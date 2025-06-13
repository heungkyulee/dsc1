import json
import os
import re
from datetime import datetime
import uuid
import shutil
import logging

# --- 파일 경로 ---
RAW_DATA_FILE = "kstartup_contest_info.json"
ORGS_FILE = "organizations.json"
ANNS_FILE = "announcements.json"
INDEX_FILE = "index.json"

# --- 데이터 로드/저장 헬퍼 함수 ---

def load_json(filepath, default=None):
    """JSON 파일을 로드합니다. 파일이 없으면 기본값을 반환합니다."""
    if default is None:
        default = {}
    if not os.path.exists(filepath):
        return default
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"[경고] {filepath} 파일이 비어있거나 잘못된 형식입니다. 기본값을 사용합니다.")
        return default
    except Exception as e:
        print(f"[에러] {filepath} 로드 중 오류 발생: {e}")
        return default

def save_json(data, filepath):
    """데이터를 JSON 파일로 저장합니다."""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[에러] {filepath} 저장 중 오류 발생: {e}")

# --- 데이터 처리 및 인덱싱 ---

def extract_deadline_from_period(application_period):
    """접수기간에서 마감일을 추출합니다. (YYYYMMDD ~ YYYYMMDD 형식)"""
    if not application_period:
        return None
    
    try:
        # "20250602 ~ 20250620" 형식에서 마감일(끝 날짜) 추출
        if '~' in application_period:
            parts = application_period.split('~')
            if len(parts) >= 2:
                end_date_str = parts[1].strip()
                # YYYYMMDD 형식을 YYYY-MM-DD로 변환
                if len(end_date_str) == 8 and end_date_str.isdigit():
                    year = end_date_str[:4]
                    month = end_date_str[4:6]
                    day = end_date_str[6:8]
                    return f"{year}-{month}-{day}"
        
        # 단일 날짜인 경우 (YYYYMMDD)
        elif len(application_period.strip()) == 8 and application_period.strip().isdigit():
            date_str = application_period.strip()
            year = date_str[:4]
            month = date_str[4:6]
            day = date_str[6:8]
            return f"{year}-{month}-{day}"
            
    except Exception as e:
        print(f"[경고] 접수기간 파싱 오류 ({application_period}): {e}")
    
    return None

def format_date_string(date_str):
    """YYYYMMDD 형식의 날짜를 YYYY-MM-DD로 변환합니다."""
    if not date_str:
        return None
    
    try:
        if len(date_str) == 8 and date_str.isdigit():
            year = date_str[:4]
            month = date_str[4:6]
            day = date_str[6:8]
            return f"{year}-{month}-{day}"
    except Exception as e:
        print(f"[경고] 날짜 형식 변환 오류 ({date_str}): {e}")
    
    return date_str  # 변환 실패 시 원본 반환

def generate_org_id(org_name):
    """기관명으로부터 간단한 고유 ID를 생성합니다."""
    # 간단하게 앞 3글자 + 길이 사용 (중복 가능성 있음, 실제로는 더 정교한 방법 필요)
    prefix = re.sub(r'\W+', '', org_name)[:3].upper()
    return f"ORG_{prefix}{len(org_name)}"

def tokenize(text):
    """간단한 텍스트 토큰화 (띄어쓰기 기준, 특수문자 제거) - 인덱싱용"""
    if not text:
        return []
    words = re.findall(r'\b\w+\b', text.lower())
    return list(set(word for word in words if len(word) > 1))

def process_raw_data():
    """
    kstartup_contest_info.json을 읽어 organizations.json, announcements.json, index.json 생성/업데이트
    """
    raw_data = load_json(RAW_DATA_FILE)
    if not raw_data:
        print(f"[정보] {RAW_DATA_FILE} 파일이 비어있거나 찾을 수 없습니다. 처리를 건너뜁니다.")
        return False

    organizations = load_json(ORGS_FILE)
    announcements = load_json(ANNS_FILE)
    index = load_json(INDEX_FILE, default={
        "title_keywords": {}, # 제목 키워드 인덱스는 여전히 생성 (필요시 다른 용도로 활용 가능)
        "organization_name": {},
        "region": {},
        "support_field": {},
        "pbancSn_to_orgId": {}
    })

    new_org_count = 0
    new_ann_count = 0
    updated_ann_count = 0

    org_name_to_id = {org_data["name"]: org_id for org_id, org_data in organizations.items()}

    for pbancSn_str, ann_data in raw_data.items():
        pbancSn = int(pbancSn_str)
        org_name = ann_data.get("공고기관") or ann_data.get("기관명")

        if not org_name:
            print(f"[경고] 공고 {pbancSn}의 기관명을 찾을 수 없습니다. 건너뜁니다.")
            continue

        # 1. 기관 정보 처리
        org_id = org_name_to_id.get(org_name)
        if not org_id:
            org_id = generate_org_id(org_name)
            while org_id in organizations:
                org_id += "X"
            organizations[org_id] = {
                "name": org_name,
                "type": ann_data.get("기관구분", "")
            }
            org_name_to_id[org_name] = org_id
            new_org_count += 1

        # 2. 공고 정보 처리
        # 접수기간에서 마감일 추출
        application_period = ann_data.get("접수기간", "")
        deadline = extract_deadline_from_period(application_period)
        
        # 공고일자 처리
        announcement_date = ann_data.get("공고일자", "")
        formatted_announcement_date = format_date_string(announcement_date)
        
        announcement_entry = {
            "title": ann_data.get("title", ""),
            "support_field": ann_data.get("지원분야", ""),
            "target_age": ann_data.get("대상연령", ""),
            "org_name_ref": org_name,
            "org_id": org_id,
            "contact": ann_data.get("연락처", ""),
            "region": ann_data.get("지역", ""),
            "application_period": application_period,
            "deadline": deadline,  # 추출된 마감일
            "startup_experience": ann_data.get("창업업력", ""),
            "target_audience": ann_data.get("대상", ""),
            "department": ann_data.get("담당부서", ""),
            "announcement_number": ann_data.get("공고번호", ""),
            "description": ann_data.get("공고설명", ""),
            "announcement_date": formatted_announcement_date,
            "application_method": ann_data.get("신청방법", []),
            "submission_documents": ann_data.get("제출서류", []),
            "selection_procedure": ann_data.get("선정절차", []),
            "support_content": ann_data.get("지원내용", []),
            "inquiry": ann_data.get("문의처", []),
            "attachments": ann_data.get("첨부파일", [])
        }

        is_new = pbancSn_str not in announcements
        needs_update = not is_new and announcements[pbancSn_str] != announcement_entry

        if is_new or needs_update:
            announcements[pbancSn_str] = announcement_entry
            if is_new:
                new_ann_count += 1
            else:
                updated_ann_count += 1

            # 3. 인덱스 업데이트 (부분 업데이트 로직은 여전히 단순화됨)
            index["pbancSn_to_orgId"][pbancSn_str] = org_id

            # 제목 키워드 인덱싱 (여전히 생성)
            title_tokens = tokenize(announcement_entry["title"])
            for token in title_tokens:
                if token not in index["title_keywords"]:
                    index["title_keywords"][token] = []
                if pbancSn_str not in index["title_keywords"][token]:
                     index["title_keywords"][token].append(pbancSn_str)

            # 기관명 인덱싱
            if org_name:
                if org_name not in index["organization_name"]:
                    index["organization_name"][org_name] = []
                if pbancSn_str not in index["organization_name"][org_name]:
                    index["organization_name"][org_name].append(pbancSn_str)

            # 지역 인덱싱
            region = announcement_entry["region"]
            if region:
                if region not in index["region"]:
                    index["region"][region] = []
                if pbancSn_str not in index["region"][region]:
                     index["region"][region].append(pbancSn_str)

            # 지원분야 인덱싱
            support_field = announcement_entry["support_field"]
            if support_field:
                fields = [f.strip() for f in support_field.split(',') if f.strip()]
                for field in fields:
                    if field not in index["support_field"]:
                        index["support_field"][field] = []
                    if pbancSn_str not in index["support_field"][field]:
                        index["support_field"][field].append(pbancSn_str)

    save_json(organizations, ORGS_FILE)
    save_json(announcements, ANNS_FILE)
    save_json(index, INDEX_FILE)

    print(f"[정보] 데이터 처리 완료: 신규 기관 {new_org_count}개, 신규 공고 {new_ann_count}개, 업데이트된 공고 {updated_ann_count}개")
    return True

# --- CRUD 함수 ---

def get_all_organizations():
    """모든 기관 정보를 반환합니다."""
    return load_json(ORGS_FILE)

def get_all_announcements():
    """모든 공고 정보를 반환합니다."""
    return load_json(ANNS_FILE)

def get_announcement_by_id(pbancSn_str):
    """ID로 특정 공고 정보를 반환합니다."""
    announcements = load_json(ANNS_FILE)
    return announcements.get(pbancSn_str)

def find_announcements(keyword=None, org_name=None, region=None, support_field=None):
    """조건에 맞는 공고 ID 목록을 반환합니다. 키워드는 부분 문자열 검색, 나머지는 인덱스 활용."""
    index = load_json(INDEX_FILE)
    announcements = load_json(ANNS_FILE)
    if not announcements: # 공고 데이터가 없으면 검색 불가
        return []

    result_sets = []
    all_ann_ids = set(announcements.keys()) # 교집합 연산을 위해 전체 ID 집합 생성

    # 1. 키워드 검색 (부분 문자열 검색)
    if keyword:
        keyword_ids = set()
        search_keyword_lower = keyword.lower()
        for pbancSn_str, ann_data in announcements.items():
            title = ann_data.get("title", "")
            if search_keyword_lower in title.lower():
                keyword_ids.add(pbancSn_str)
        result_sets.append(keyword_ids)

    # 2. 기관명 검색 (인덱스 활용)
    if org_name:
        if index and org_name in index.get("organization_name", {}):
             result_sets.append(set(index["organization_name"][org_name]))
        else: # 인덱스가 없거나 기관명이 인덱스에 없는 경우
             result_sets.append(set()) # 빈 집합 추가

    # 3. 지역 필터 (인덱스 활용)
    if region:
        if index and region in index.get("region", {}):
            result_sets.append(set(index["region"][region]))
        else:
            result_sets.append(set())

    # 4. 지원분야 필터 (인덱스 활용)
    if support_field:
        if index and support_field in index.get("support_field", {}):
             result_sets.append(set(index["support_field"][support_field]))
        else:
             result_sets.append(set())

    # 모든 조건을 만족하는 ID 찾기 (교집합)
    if not result_sets: # 적용된 필터가 없으면 모든 공고 ID 반환
        return list(all_ann_ids)
    else:
        # 시작 집합을 전체 ID로 설정하고, 각 필터 결과와 교집합 수행
        final_ids = all_ann_ids
        for s in result_sets:
            final_ids.intersection_update(s)
        return list(final_ids)


def update_announcement(pbancSn_str, updated_data):
    """특정 공고 정보를 업데이트합니다. (개선된 Pinecone 메타데이터 포함)"""
    try:
        # 1. JSON 파일 업데이트
        announcements = load_json(ANNS_FILE)
        if pbancSn_str not in announcements:
            print(f"[에러] 공고 ID {pbancSn_str}를 찾을 수 없습니다.")
            return False

        # 기존 데이터와 새 데이터 병합
        announcements[pbancSn_str].update(updated_data)
        
        # 2. JSON 파일 저장
        save_json(announcements, ANNS_FILE)
        print(f"[정보] 공고 {pbancSn_str} JSON 파일 업데이트 완료")

        # 3. 개선된 Pinecone 업데이트
        try:
            from rag_system import _build_announcement_text, _build_announcement_metadata, get_rag_chatbot
            
            # RAG 시스템 초기화 확인
            chatbot = get_rag_chatbot()
            if not chatbot.embedding_manager.model or not chatbot.pinecone_manager.index:
                print(f"[경고] RAG 시스템이 초기화되지 않아 Pinecone 업데이트를 건너뜁니다.")
                return True  # JSON 업데이트는 성공했으므로 True 반환
            
            # 업데이트된 데이터로 개선된 임베딩 및 메타데이터 생성
            updated_contest_data = announcements[pbancSn_str]
            
            # 개선된 텍스트 내용 구성 (모든 메타데이터 포함)
            text_content = _build_announcement_text(updated_contest_data)
            
            if text_content.strip():
                # 임베딩 생성
                embedding = chatbot.embedding_manager.create_embedding(text_content)
                
                # 개선된 메타데이터 구성 (확장된 정보 포함)
                metadata = _build_announcement_metadata(updated_contest_data)
                
                # 벡터 데이터 구성
                vector_id = f"announcement_{pbancSn_str}"
                vector_data = [{
                    "id": vector_id,
                    "values": embedding,
                    "metadata": metadata
                }]
                
                # Pinecone에 업서트
                success = chatbot.pinecone_manager.upsert_vectors(vector_data)
                if success:
                    print(f"[정보] 공고 {pbancSn_str} Pinecone 업데이트 완료 (개선된 메타데이터)")
                else:
                    print(f"[경고] 공고 {pbancSn_str} Pinecone 업데이트 실패")
                    return False
            else:
                print(f"[경고] 임베딩할 텍스트 내용이 없어 Pinecone 업데이트를 건너뜁니다.")
                
        except Exception as e:
            print(f"[경고] Pinecone 업데이트 중 오류: {e}")
            return False

        return True
    except Exception as e:
        print(f"[에러] 공고 업데이트 중 오류 발생: {e}")
        return False

def delete_announcement(pbancSn_str):
    """특정 공고 정보를 삭제합니다. (인덱스 업데이트는 단순화)"""
    announcements = load_json(ANNS_FILE)
    if pbancSn_str not in announcements:
        print(f"[에러] 공고 ID {pbancSn_str}를 찾을 수 없습니다.")
        return False
    del announcements[pbancSn_str]
    save_json(announcements, ANNS_FILE)

    # TODO: 인덱스에서 해당 pbancSn 제거하는 로직 필요
    # 여기서는 index.json은 직접 수정하지 않음
    # process_raw_data() # 비효율적일 수 있음. 부분 업데이트 로직 필요.
    print(f"[정보] 공고 {pbancSn_str} 삭제 완료. (인덱스 업데이트 필요시 process_raw_data() 재실행 권장)")
    return True


# --- 초기화 ---
# 프로그램 시작 시 데이터 파일들이 없으면 생성 시도
def initialize_data():
    """데이터 파일이 없으면 초기화 (raw 데이터 처리) 시도"""
    if not os.path.exists(ORGS_FILE) or not os.path.exists(ANNS_FILE) or not os.path.exists(INDEX_FILE):
        print("[정보] 데이터 파일(organizations, announcements, index)이 없습니다. raw 데이터 처리를 시도합니다...")
        if os.path.exists(RAW_DATA_FILE):
            process_raw_data()
        else:
            print(f"[경고] {RAW_DATA_FILE} 파일이 없어 초기 데이터 구조를 생성할 수 없습니다.")
            # 빈 파일이라도 생성
            save_json({}, ORGS_FILE)
            save_json({}, ANNS_FILE)
            save_json({}, INDEX_FILE)

# 데이터 파일 경로
DATA_FILE = 'kstartup_contest_info.json'

# 메모리에 로드된 전체 공고 데이터
all_contests_data = []

def load_all_data():
    """
    JSON 파일들에서 모든 공고 데이터를 로드하여 all_contests_data에 저장합니다.
    announcements.json이 더 많은 데이터를 가지고 있으면 우선적으로 사용합니다.
    """
    global all_contests_data
    
    print("\n[LOAD] ==================== 데이터 로드 시작 ====================")
    
    # 백업 파일들 확인
    backup_files = [f for f in os.listdir('.') if f.startswith(f"{DATA_FILE}.backup.")]
    if backup_files:
        print(f"[LOAD] 백업 파일 {len(backup_files)}개 발견")
    
    # 1. kstartup_contest_info.json 로드 시도
    contest_data = []
    contest_file_error = None
    
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
                if content.strip():
                    loaded_json = json.loads(content)
                    if isinstance(loaded_json, dict):
                        contest_data = list(loaded_json.values())
                    elif isinstance(loaded_json, list):
                        contest_data = loaded_json
                    print(f"[LOAD] kstartup_contest_info.json에서 {len(contest_data)}개 항목 로드")
                else:
                    print(f"[LOAD] {DATA_FILE}이 비어있음")
        except Exception as e:
            contest_file_error = e
            print(f"[LOAD] {DATA_FILE} 로드 실패: {e}")
            
            # 백업에서 복구 시도
            if backup_files:
                print(f"[RECOVERY] 백업에서 복구 시도...")
                latest_backup = sorted(backup_files)[-1]
                try:
                    with open(latest_backup, 'r', encoding='utf-8') as f:
                        backup_content = json.load(f)
                        if isinstance(backup_content, dict):
                            contest_data = list(backup_content.values())
                        elif isinstance(backup_content, list):
                            contest_data = backup_content
                        print(f"[RECOVERY] 백업에서 {len(contest_data)}개 항목 복구 성공: {latest_backup}")
                except Exception as backup_error:
                    print(f"[RECOVERY] 백업 복구 실패: {backup_error}")
    
    # 2. announcements.json 로드 시도 (더 많은 데이터가 있을 가능성)
    announcements_data = []
    announcements_file_error = None
    
    if os.path.exists(ANNS_FILE):
        try:
            announcements_dict = load_json(ANNS_FILE, default={})
            if announcements_dict:
                announcements_data = list(announcements_dict.values())
                print(f"[LOAD] announcements.json에서 {len(announcements_data)}개 항목 로드")
        except Exception as e:
            announcements_file_error = e
            print(f"[LOAD] {ANNS_FILE} 로드 실패: {e}")
    
    # 3. 더 많은 데이터를 가진 소스 선택
    if len(announcements_data) > len(contest_data):
        print(f"[LOAD] announcements.json이 더 많은 데이터를 가지고 있음 ({len(announcements_data)} vs {len(contest_data)})")
        all_contests_data = announcements_data
        
        # kstartup_contest_info.json을 announcements.json과 동기화
        if len(contest_data) < len(announcements_data):
            try:
                print(f"[SYNC] kstartup_contest_info.json을 announcements.json과 동기화 중...")
                sync_data = {}
                
                for i, item in enumerate(all_contests_data):
                    if item and isinstance(item, dict):
                        pblancId = item.get('pblancId', f"AUTO_ID_{i}")
                        if not pblancId or pblancId == 'N/A':
                            pblancId = str(uuid.uuid4())
                            item['pblancId'] = pblancId
                        sync_data[str(pblancId)] = item
                
                # 백업 생성 후 동기화
                if os.path.exists(DATA_FILE):
                    backup_file = f"{DATA_FILE}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    shutil.copy2(DATA_FILE, backup_file)
                    print(f"[SYNC] 동기화 전 백업 생성: {backup_file}")
                
                with open(DATA_FILE, 'w', encoding='utf-8') as f:
                    json.dump(sync_data, f, ensure_ascii=False, indent=2)
                
                print(f"[SYNC] 동기화 완료: {len(sync_data)}개 항목")
                
            except Exception as e:
                print(f"[SYNC] 동기화 실패: {e}")
    
    elif len(contest_data) > 0:
        print(f"[LOAD] kstartup_contest_info.json 사용 ({len(contest_data)}개 항목)")
        all_contests_data = contest_data
    
    else:
        print(f"[LOAD] 모든 데이터 파일이 비어있음")
        all_contests_data = []
        
        # 긴급 복구: 백업 파일에서 로드 시도
        if backup_files and (contest_file_error or announcements_file_error):
            print(f"[EMERGENCY] 긴급 복구 시도...")
            for backup_file in sorted(backup_files, reverse=True):  # 최신 백업부터
                try:
                    with open(backup_file, 'r', encoding='utf-8') as f:
                        backup_data = json.load(f)
                        if isinstance(backup_data, dict) and backup_data:
                            all_contests_data = list(backup_data.values())
                            print(f"[EMERGENCY] 긴급 복구 성공: {backup_file}에서 {len(all_contests_data)}개 항목")
                            break
                except Exception as emergency_error:
                    print(f"[EMERGENCY] {backup_file} 복구 실패: {emergency_error}")
    
    print(f"[LOAD] 최종 로드된 데이터: {len(all_contests_data)}개 항목")
    
    # 4. 데이터 검증 및 정리
    valid_data = []
    fixed_count = 0
    
    for i, item in enumerate(all_contests_data):
        if isinstance(item, dict) and item.get('title'):  # 최소한 제목이 있는 데이터만
            # pblancId가 없거나 유효하지 않으면 생성
            if 'pblancId' not in item or not item['pblancId'] or item['pblancId'] == 'N/A':
                item['pblancId'] = str(uuid.uuid4())
                fixed_count += 1
            valid_data.append(item)
    
    all_contests_data = valid_data
    
    print(f"[LOAD] 검증 후 유효한 데이터: {len(all_contests_data)}개 항목")
    if fixed_count > 0:
        print(f"[LOAD] pblancId 자동 수정: {fixed_count}개 항목")
    
    # 5. 데이터 무결성 최종 검증
    if len(all_contests_data) == 0:
        print(f"[WARNING] 로드된 데이터가 없습니다!")
    elif len(all_contests_data) < 10:
        print(f"[WARNING] 로드된 데이터가 예상보다 적습니다 ({len(all_contests_data)}개)")
    else:
        print(f"[SUCCESS] 데이터 로드 성공")
    
    print(f"[LOAD] ==================== 데이터 로드 완료 ====================\n")
    
    return len(all_contests_data)

def save_all_data():
    """
    all_contests_data의 내용을 kstartup_contest_info.json 파일에 안전하게 저장합니다.
    백업 생성 및 원자적 쓰기를 통해 데이터 손실을 방지합니다.
    """
    global all_contests_data
    
    print(f"\n[SAVE] ==================== 데이터 저장 시작 ====================")
    print(f"[SAVE] 저장할 데이터 수: {len(all_contests_data)}")
    
    # 1. 데이터 검증
    if not all_contests_data:
        print(f"[ERROR] 저장할 데이터가 없습니다. 저장을 중단합니다.")
        return False
    
    # 2. 기존 파일 백업 생성
    backup_created = False
    if os.path.exists(DATA_FILE):
        try:
            backup_file = f"{DATA_FILE}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(DATA_FILE, backup_file)
            print(f"[SAVE] 백업 파일 생성: {backup_file}")
            backup_created = True
        except Exception as e:
            print(f"[WARNING] 백업 생성 실패: {e}")
    
    # 3. 데이터 변환 (pblancId가 있는 항목만)
    valid_data = {}
    invalid_count = 0
    
    for item in all_contests_data:
        if isinstance(item, dict) and 'pblancId' in item and item['pblancId']:
            pblancId = str(item['pblancId'])
            valid_data[pblancId] = item
        else:
            invalid_count += 1
    
    print(f"[SAVE] 유효한 데이터: {len(valid_data)}개")
    if invalid_count > 0:
        print(f"[WARNING] pblancId가 없는 데이터 {invalid_count}개 제외됨")
    
    # 4. 최소 데이터 수 검증 (기존 데이터가 10,000개 이상이었으므로)
    if len(valid_data) < 100:  # 임계치 설정
        print(f"[ERROR] 저장할 데이터가 너무 적습니다 ({len(valid_data)}개). 데이터 손실 방지를 위해 저장을 중단합니다.")
        return False
    
    # 5. 임시 파일에 먼저 저장 (원자적 쓰기)
    temp_file = f"{DATA_FILE}.tmp"
    try:
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(valid_data, f, ensure_ascii=False, indent=2)
        
        # 6. 저장 성공 시 원본 파일로 이동
        if os.path.exists(temp_file):
            if os.path.exists(DATA_FILE):
                os.remove(DATA_FILE)
            os.rename(temp_file, DATA_FILE)
            
            print(f"[SAVE] 데이터 저장 완료: {len(valid_data)}개 항목")
            print(f"[SAVE] ==================== 데이터 저장 완료 ====================\n")
            return True
        else:
            print(f"[ERROR] 임시 파일 생성 실패")
            return False
            
    except Exception as e:
        print(f"[ERROR] 데이터 저장 중 오류 발생: {e}")
        
        # 임시 파일 정리
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass
        
        # 백업에서 복구 시도
        if backup_created:
            try:
                backup_files = [f for f in os.listdir('.') if f.startswith(f"{DATA_FILE}.backup.")]
                if backup_files:
                    latest_backup = sorted(backup_files)[-1]
                    shutil.copy2(latest_backup, DATA_FILE)
                    print(f"[RECOVERY] 백업에서 복구 완료: {latest_backup}")
            except Exception as recovery_error:
                print(f"[ERROR] 백업 복구 실패: {recovery_error}")
        
        return False

def get_all_contests():
    """
    메모리에 로드된 모든 공고 데이터를 반환합니다. (리스트 형태)
    """
    global all_contests_data
    # 데이터가 메모리에 없으면 로드 시도 (load_all_data가 리스트를 가져옴)
    if not all_contests_data and os.path.exists(DATA_FILE):
        load_all_data()
    return all_contests_data

def find_contest_by_id(contest_id):
    """
    주어진 ID (pblancId)를 가진 공고를 찾아서 반환합니다.
    ID는 문자열로 처리합니다.
    """
    global all_contests_data
    if not all_contests_data:
        load_all_data()
    
    str_contest_id = str(contest_id)
    for contest in all_contests_data: # all_contests_data는 이제 항상 리스트
        if 'pblancId' in contest and str(contest['pblancId']) == str_contest_id:
            return contest
    return None

def add_contest(contest_data):
    """
    새로운 공고 데이터를 추가합니다.
    트랜잭션 방식으로 안전하게 저장하며, 실패 시 롤백됩니다.
    """
    global all_contests_data
    
    print(f"\n[ADD_CONTEST] ==================== 공고 추가 시작 ====================")
    
    # 1. 초기 데이터 로드
    if not all_contests_data:
        print(f"[ADD_CONTEST] 데이터 로드 중...")
        loaded_count = load_all_data()
        print(f"[ADD_CONTEST] 기존 데이터: {loaded_count}개")

    original_data_count = len(all_contests_data)
    
    # 2. pblancId 자동 생성
    if 'pblancId' not in contest_data or not contest_data['pblancId']:
        contest_data['pblancId'] = str(uuid.uuid4())
        print(f"[ADD_CONTEST] 자동 생성된 ID: {contest_data['pblancId']}")

    # 3. 중복 검사
    existing_contest = find_contest_by_id(contest_data.get('pblancId'))
    if existing_contest:
        print(f"[ERROR] ID {contest_data.get('pblancId')}가 이미 존재합니다.")
        return False
    
    # 4. 데이터 표준화
    try:
        standardized_data = _standardize_contest_data(contest_data)
        print(f"[ADD_CONTEST] 데이터 표준화 완료")
    except Exception as e:
        print(f"[ERROR] 데이터 표준화 실패: {e}")
        return False
    
    # 5. 메모리에 임시 추가 (롤백 가능한 상태)
    all_contests_data.append(standardized_data)
    print(f"[ADD_CONTEST] 메모리에 임시 추가 ({original_data_count} → {len(all_contests_data)})")
    
    try:
        # 6. JSON 파일들에 저장
        print(f"[ADD_CONTEST] JSON 파일 저장 시작...")
        save_success = _save_to_json_files(standardized_data)
        
        if not save_success:
            # 저장 실패 시 메모리에서 롤백
            print(f"[ROLLBACK] JSON 저장 실패로 메모리에서 제거")
            all_contests_data.pop()
            print(f"[ROLLBACK] 메모리 롤백 완료 ({len(all_contests_data)}개)")
            return False
        
        print(f"[ADD_CONTEST] JSON 파일 저장 완료")
        
        # 7. Pinecone 업데이트
        print(f"[ADD_CONTEST] Pinecone 업데이트 시작...")
        pinecone_success = _update_pinecone_single(standardized_data)
        
        if not pinecone_success:
            print(f"[WARNING] Pinecone 업데이트 실패 (JSON 데이터는 저장됨)")
        else:
            print(f"[ADD_CONTEST] Pinecone 업데이트 완료")
        
        # 8. 성공 완료
        print(f"[SUCCESS] 공고 추가 완료!")
        print(f"[SUCCESS] - ID: {standardized_data['pblancId']}")
        print(f"[SUCCESS] - 제목: {standardized_data.get('title', 'N/A')}")
        print(f"[SUCCESS] - 전체 데이터 수: {len(all_contests_data)}")
        print(f"[ADD_CONTEST] ==================== 공고 추가 완료 ====================\n")
        
        return True
        
    except Exception as e:
        # 예외 발생 시 메모리에서 롤백
        print(f"[ERROR] 예외 발생: {e}")
        print(f"[ROLLBACK] 메모리에서 롤백 시도...")
        
        try:
            if len(all_contests_data) > original_data_count:
                all_contests_data.pop()
                print(f"[ROLLBACK] 메모리 롤백 완료 ({len(all_contests_data)}개)")
            else:
                print(f"[ROLLBACK] 롤백할 데이터가 없음")
        except Exception as rollback_error:
            print(f"[ERROR] 롤백 중 오류: {rollback_error}")
        
        print(f"[ADD_CONTEST] ==================== 공고 추가 실패 ====================\n")
        return False

def _standardize_contest_data(contest_data):
    """
    새로 생성된 데이터를 기존 형식에 맞춰 표준화합니다. (데이터 소스 정보 포함)
    """
    current_time = datetime.now().isoformat()
    
    standardized = {
        'pblancId': contest_data.get('pblancId'),
        'title': contest_data.get('title', ''),
        'org_name_ref': contest_data.get('organization', ''),
        'support_field': contest_data.get('category', ''),
        'region': contest_data.get('region', '전국'),
        'target_audience': contest_data.get('target_audience', '제한 없음'),
        'description': contest_data.get('description', ''),
        'deadline': contest_data.get('deadline', ''),
        'application_period': f"{datetime.now().strftime('%Y%m%d')} ~ {contest_data.get('deadline', '').replace('-', '')}",
        'contact': contest_data.get('contact', ''),
        'department': contest_data.get('organization', ''),
        'announcement_date': datetime.now().strftime('%Y-%m-%d'),
        'status': contest_data.get('status', 'active'),
        'created_at': contest_data.get('created_at', current_time),
        'updated_at': contest_data.get('updated_at', current_time),
        'announcement_number': f"USER-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8]}",
        'target_age': '',
        'startup_experience': '',
        'application_method': ['온라인 신청'],
        'submission_documents': [],
        'selection_procedure': [],
        'support_content': contest_data.get('budget', ''),
        'inquiry': [contest_data.get('contact', '')] if contest_data.get('contact') else [],
        'attachments': [],
        # 🔥 데이터 소스 정보 추가 (RAG 시스템에서 구분용)
        'data_source': 'user_created',
        'source_type': '사용자 생성',
        'is_user_generated': True
    }
    
    return standardized

def _save_to_json_files(contest_data):
    """
    표준화된 데이터를 관련 JSON 파일들에 트랜잭션 방식으로 안전하게 저장합니다.
    """
    print(f"\n[SAVE_FILES] ==================== JSON 파일 저장 시작 ====================")
    
    success_operations = []
    
    try:
        # 1. kstartup_contest_info.json에 저장 (전체 데이터)
        print(f"[SAVE_FILES] 1. kstartup_contest_info.json 저장 중...")
        save_result = save_all_data()
        if save_result:
            success_operations.append("kstartup_contest_info")
            print(f"[SAVE_FILES] ✓ kstartup_contest_info.json 저장 완료")
        else:
            print(f"[SAVE_FILES] ✗ kstartup_contest_info.json 저장 실패")
            return False
        
        # 2. announcements.json에 추가/업데이트
        print(f"[SAVE_FILES] 2. announcements.json 업데이트 중...")
        announcements = load_json(ANNS_FILE, default={})
        original_count = len(announcements)
        
        announcements[str(contest_data['pblancId'])] = contest_data
        save_json(announcements, ANNS_FILE)
        success_operations.append("announcements")
        
        new_count = len(announcements)
        print(f"[SAVE_FILES] ✓ announcements.json 업데이트 완료 ({original_count} → {new_count})")
        
        # 3. organizations.json 업데이트
        print(f"[SAVE_FILES] 3. organizations.json 업데이트 중...")
        organizations = load_json(ORGS_FILE, default={})
        org_name = contest_data.get('org_name_ref', '')
        
        if org_name:
            org_id = f"ORG_{org_name[:3].upper()}{len(org_name)}"
            if org_id not in organizations:
                organizations[org_id] = {
                    "name": org_name,
                    "type": "사용자 생성",
                    "created_at": datetime.now().isoformat()
                }
                save_json(organizations, ORGS_FILE)
                print(f"[SAVE_FILES] ✓ 새 기관 추가: {org_name}")
            else:
                print(f"[SAVE_FILES] ○ 기존 기관 사용: {org_name}")
        
        success_operations.append("organizations")
        
        # 4. index.json 업데이트
        print(f"[SAVE_FILES] 4. index.json 업데이트 중...")
        index = load_json(INDEX_FILE, default={
            "title_keywords": {},
            "organization_name": {},
            "region": {},
            "support_field": {},
            "pbancSn_to_orgId": {}
        })
        
        # 기존 인덱스에서 해당 ID 제거 (업데이트 시)
        pblancId_str = str(contest_data['pblancId'])
        for keyword_list in index["title_keywords"].values():
            if pblancId_str in keyword_list:
                keyword_list.remove(pblancId_str)
        
        # 새로운 키워드 인덱싱
        title_tokens = tokenize(contest_data.get('title', ''))
        for token in title_tokens:
            if token not in index["title_keywords"]:
                index["title_keywords"][token] = []
            if pblancId_str not in index["title_keywords"][token]:
                index["title_keywords"][token].append(pblancId_str)
        
        # 기관명 인덱싱
        if org_name:
            if org_name not in index["organization_name"]:
                index["organization_name"][org_name] = []
            if pblancId_str not in index["organization_name"][org_name]:
                index["organization_name"][org_name].append(pblancId_str)
        
        # 지역 인덱싱
        region = contest_data.get('region', '')
        if region:
            if region not in index["region"]:
                index["region"][region] = []
            if pblancId_str not in index["region"][region]:
                index["region"][region].append(pblancId_str)
        
        # 지원분야 인덱싱
        support_field = contest_data.get('support_field', '')
        if support_field:
            if support_field not in index["support_field"]:
                index["support_field"][support_field] = []
            if pblancId_str not in index["support_field"][support_field]:
                index["support_field"][support_field].append(pblancId_str)
        
        save_json(index, INDEX_FILE)
        success_operations.append("index")
        print(f"[SAVE_FILES] ✓ index.json 업데이트 완료")
        
        print(f"[SAVE_FILES] ==================== JSON 파일 저장 완료 ====================\n")
        return True
        
    except Exception as e:
        print(f"[SAVE_FILES] ✗ JSON 파일 저장 중 오류: {e}")
        print(f"[SAVE_FILES] 성공한 작업: {', '.join(success_operations)}")
        print(f"[SAVE_FILES] ==================== JSON 파일 저장 실패 ====================\n")
        return False

def _update_pinecone_single(contest_data):
    """
    단일 공고 데이터를 Pinecone에 업데이트합니다. (개선된 메타데이터 사용)
    """
    try:
        # RAG 시스템이 사용 가능한지 확인
        try:
            from rag_system import get_rag_chatbot, _build_announcement_text, _build_announcement_metadata
            chatbot = get_rag_chatbot()
            
            if not chatbot.embedding_manager.model or not chatbot.pinecone_manager.index:
                print("Warning: RAG 시스템이 초기화되지 않아 Pinecone 업데이트를 건너뜁니다.")
                return False
                
        except ImportError:
            print("Warning: RAG 시스템을 가져올 수 없어 Pinecone 업데이트를 건너뜁니다.")
            return False
        
        # 개선된 텍스트 내용 구성 (모든 메타데이터 포함)
        text_content = _build_announcement_text(contest_data)
        
        if not text_content.strip():
            print("Warning: 임베딩할 텍스트 내용이 없습니다.")
            return False
        
        # 임베딩 생성
        embedding = chatbot.embedding_manager.create_embedding(text_content)
        
        # 개선된 메타데이터 구성 (확장된 정보 포함)
        metadata = _build_announcement_metadata(contest_data)
        
        # 벡터 데이터 구성
        vector_id = f"announcement_{contest_data.get('pblancId', contest_data.get('id', 'unknown'))}"
        vector_data = [{
            "id": vector_id,
            "values": embedding,
            "metadata": metadata
        }]
        
        # Pinecone에 업서트
        success = chatbot.pinecone_manager.upsert_vectors(vector_data)
        
        if success:
            print(f"Pinecone 업데이트 성공: {vector_id}")
        else:
            print(f"Pinecone 업데이트 실패: {vector_id}")
            
        return success
        
    except Exception as e:
        print(f"Pinecone 업데이트 중 오류: {e}")
        return False

def update_contest(contest_id, updated_data):
    """
    기존 공고 데이터를 수정합니다. (완전 재구현)
    contest_id를 여러 방법으로 찾아 데이터를 업데이트합니다.
    """
    global all_contests_data
    
    # 강제로 최신 데이터 로드
    load_all_data()
    
    if not all_contests_data:
        print(f"[ERROR] 전체 데이터가 비어있습니다.")
        return False
    
    str_contest_id = str(contest_id)
    print(f"\n[UPDATE] ==================== 수정 시작 ====================")
    print(f"[UPDATE] 입력 ID: '{str_contest_id}'")
    print(f"[UPDATE] 전체 데이터 수: {len(all_contests_data)}")
    print(f"[UPDATE] 업데이트 필드: {list(updated_data.keys())}")
    
    # 첫 번째 데이터 샘플 확인
    if all_contests_data:
        sample = all_contests_data[0]
        print(f"[UPDATE] 샘플 데이터 키: {list(sample.keys())[:15]}")
        print(f"[UPDATE] 샘플 pblancId: '{sample.get('pblancId', 'N/A')}'")
        print(f"[UPDATE] 샘플 title: '{sample.get('title', 'N/A')}'")
    
    # 모든 가능한 방법으로 데이터 찾기
    found_index = None
    found_data = None
    search_method = None
    
    # === 방법 1: pblancId 필드로 정확히 매칭 ===
    print(f"\n[SEARCH] 방법 1: pblancId 정확 매칭")
    for idx, item in enumerate(all_contests_data):
        item_id = item.get('pblancId')
        if item_id is not None and str(item_id) == str_contest_id:
            found_index = idx
            found_data = item
            search_method = f"pblancId 정확 매칭 (Index: {idx})"
            print(f"[SEARCH] ✓ 방법 1 성공: Index {idx}, pblancId '{item_id}'")
            break
    
    # === 방법 2: 숫자 인덱스로 직접 접근 ===
    if found_index is None:
        print(f"[SEARCH] 방법 2: 숫자 인덱스 접근")
        try:
            idx_num = int(str_contest_id)
            if 0 <= idx_num < len(all_contests_data):
                found_index = idx_num
                found_data = all_contests_data[idx_num]
                search_method = f"인덱스 직접 접근 (Index: {idx_num})"
                print(f"[SEARCH] ✓ 방법 2 성공: Index {idx_num}")
                print(f"[SEARCH] 해당 데이터 pblancId: '{found_data.get('pblancId', 'N/A')}'")
            else:
                print(f"[SEARCH] ✗ 방법 2 실패: 인덱스 {idx_num}이 범위를 벗어남")
        except (ValueError, TypeError):
            print(f"[SEARCH] ✗ 방법 2 실패: '{str_contest_id}'를 숫자로 변환 불가")
    
    # === 방법 3: 부분 문자열 매칭 (pblancId, title 등) ===
    if found_index is None:
        print(f"[SEARCH] 방법 3: 부분 문자열 매칭")
        search_fields = ['pblancId', 'title', 'id']
        for field in search_fields:
            for idx, item in enumerate(all_contests_data):
                field_value = item.get(field, '')
                if field_value and str_contest_id in str(field_value):
                    found_index = idx
                    found_data = item
                    search_method = f"{field} 필드 부분 매칭 (Index: {idx})"
                    print(f"[SEARCH] ✓ 방법 3 성공: {field} 필드에서 '{field_value}' 매칭")
                    break
            if found_index is not None:
                break
    
    # === 방법 4: UUID 형태 ID 매칭 ===
    if found_index is None:
        print(f"[SEARCH] 방법 4: UUID 형태 매칭")
        for idx, item in enumerate(all_contests_data):
            item_id = item.get('pblancId', '')
            if item_id and len(str(item_id)) > 10 and str_contest_id in str(item_id):
                found_index = idx
                found_data = item
                search_method = f"UUID 부분 매칭 (Index: {idx})"
                print(f"[SEARCH] ✓ 방법 4 성공: UUID '{item_id}' 부분 매칭")
                break
    
    # === 결과 확인 및 업데이트 ===
    if found_index is not None and found_data is not None:
        print(f"\n[SUCCESS] 데이터 찾기 성공!")
        print(f"[SUCCESS] 검색 방법: {search_method}")
        print(f"[SUCCESS] 인덱스: {found_index}")
        print(f"[SUCCESS] 원본 pblancId: '{found_data.get('pblancId', 'N/A')}'")
        print(f"[SUCCESS] 원본 title: '{found_data.get('title', 'N/A')}'")
        
        # 원본 ID 보존
        original_pblancId = found_data.get('pblancId', str_contest_id)
        
        # 업데이트 시간 추가
        updated_data['updated_at'] = datetime.now().isoformat()
        
        # 데이터 병합 (기존 데이터 보존하면서 새 데이터 추가)
        merged_data = found_data.copy()
        for key, value in updated_data.items():
            if key != 'pblancId':  # ID는 변경하지 않음
                merged_data[key] = value
        merged_data['pblancId'] = original_pblancId  # ID 보존
        
        print(f"[UPDATE] 병합된 데이터 필드 수: {len(merged_data)}")
        print(f"[UPDATE] 변경된 필드: {[k for k in updated_data.keys() if k != 'updated_at']}")
        
        # 메모리 업데이트
        all_contests_data[found_index] = merged_data
        print(f"[UPDATE] 메모리 업데이트 완료")
        
        # JSON 파일 저장
        try:
            save_success = _save_to_json_files(merged_data)
            if save_success:
                print(f"[UPDATE] JSON 파일 저장 완료")
            else:
                print(f"[ERROR] JSON 파일 저장 실패")
                return False
        except Exception as e:
            print(f"[ERROR] JSON 파일 저장 중 오류: {e}")
            return False
        
        # Pinecone 업데이트
        try:
            pinecone_success = _update_pinecone_single(merged_data)
            if pinecone_success:
                print(f"[UPDATE] Pinecone 업데이트 완료")
            else:
                print(f"[WARNING] Pinecone 업데이트 실패 (JSON은 저장됨)")
        except Exception as e:
            print(f"[WARNING] Pinecone 업데이트 중 오류: {e}")
        
        print(f"[SUCCESS] ==================== 수정 완료 ====================\n")
        return True
    
    else:
        print(f"\n[FAILURE] ==================== 수정 실패 ====================")
        print(f"[FAILURE] ID '{str_contest_id}'로 데이터를 찾을 수 없습니다.")
        
        # 디버깅을 위해 실제 저장된 ID들 출력
        print(f"[DEBUG] 실제 저장된 ID들 (처음 10개):")
        for i, item in enumerate(all_contests_data[:10]):
            pblancId = item.get('pblancId', 'N/A')
            title = item.get('title', 'N/A')[:30]
            print(f"[DEBUG]   [{i}] pblancId: '{pblancId}', title: '{title}'")
        
        print(f"[FAILURE] ==========================================\n")
        return False

def delete_contest(contest_id):
    """
    주어진 ID (pblancId)를 가진 공고를 안전하게 삭제합니다.
    백업 생성 후 삭제하며, 실패 시 복구 가능합니다.
    """
    global all_contests_data
    
    print(f"\n[DELETE_CONTEST] ==================== 공고 삭제 시작 ====================")
    
    if not all_contests_data:
        print(f"[DELETE_CONTEST] 데이터 로드 중...")
        load_all_data()

    str_contest_id = str(contest_id)
    original_length = len(all_contests_data)
    print(f"[DELETE_CONTEST] 삭제 대상 ID: {str_contest_id}")
    print(f"[DELETE_CONTEST] 현재 데이터 수: {original_length}")
    
    # 1. 삭제할 데이터 찾기 및 백업
    deleted_data = None
    deleted_index = None
    
    for idx, contest in enumerate(all_contests_data):
        if 'pblancId' in contest and str(contest['pblancId']) == str_contest_id:
            deleted_data = contest.copy()  # 백업용 복사본
            deleted_index = idx
            print(f"[DELETE_CONTEST] 삭제 대상 발견: {contest.get('title', 'N/A')}")
            break
    
    if deleted_data is None:
        print(f"[ERROR] ID {str_contest_id}를 가진 공고를 찾을 수 없습니다.")
        print(f"[DELETE_CONTEST] ==================== 공고 삭제 실패 ====================\n")
        return False
    
    try:
        # 2. 메모리에서 제거
        all_contests_data.pop(deleted_index)
        print(f"[DELETE_CONTEST] 메모리에서 제거 완료 ({original_length} → {len(all_contests_data)})")
        
        # 3. JSON 파일들 업데이트
        print(f"[DELETE_CONTEST] JSON 파일 업데이트 시작...")
        
        # 3-1. kstartup_contest_info.json 업데이트
        save_result = save_all_data()
        if not save_result:
            raise Exception("kstartup_contest_info.json 저장 실패")
        
        # 3-2. announcements.json에서 삭제
        try:
            announcements = load_json(ANNS_FILE, default={})
            if str_contest_id in announcements:
                del announcements[str_contest_id]
                save_json(announcements, ANNS_FILE)
                print(f"[DELETE_CONTEST] announcements.json에서 제거 완료")
            else:
                print(f"[WARNING] announcements.json에 ID {str_contest_id}가 없음")
        except Exception as e:
            print(f"[WARNING] announcements.json 업데이트 실패: {e}")
        
        # 3-3. index.json에서 관련 인덱스 정리
        try:
            index = load_json(INDEX_FILE, default={
                "title_keywords": {},
                "organization_name": {},
                "region": {},
                "support_field": {},
                "pbancSn_to_orgId": {}
            })
            
            # 모든 인덱스에서 해당 ID 제거
            index_updated = False
            
            # 키워드 인덱스 정리
            for keyword, id_list in list(index["title_keywords"].items()):
                if str_contest_id in id_list:
                    id_list.remove(str_contest_id)
                    index_updated = True
                    if not id_list:  # 빈 리스트이면 키워드 자체 제거
                        del index["title_keywords"][keyword]
            
            # 기관명 인덱스 정리
            for org_name, id_list in list(index["organization_name"].items()):
                if str_contest_id in id_list:
                    id_list.remove(str_contest_id)
                    index_updated = True
                    if not id_list:
                        del index["organization_name"][org_name]
            
            # 지역 인덱스 정리
            for region, id_list in list(index["region"].items()):
                if str_contest_id in id_list:
                    id_list.remove(str_contest_id)
                    index_updated = True
                    if not id_list:
                        del index["region"][region]
            
            # 지원분야 인덱스 정리
            for field, id_list in list(index["support_field"].items()):
                if str_contest_id in id_list:
                    id_list.remove(str_contest_id)
                    index_updated = True
                    if not id_list:
                        del index["support_field"][field]
            
            # pbancSn_to_orgId 인덱스 정리
            if str_contest_id in index["pbancSn_to_orgId"]:
                del index["pbancSn_to_orgId"][str_contest_id]
                index_updated = True
            
            if index_updated:
                save_json(index, INDEX_FILE)
                print(f"[DELETE_CONTEST] index.json 정리 완료")
            else:
                print(f"[DELETE_CONTEST] index.json에 변경사항 없음")
                
        except Exception as e:
            print(f"[WARNING] index.json 업데이트 실패: {e}")
        
        # 4. Pinecone에서 삭제
        print(f"[DELETE_CONTEST] Pinecone에서 삭제 시도...")
        pinecone_success = _delete_from_pinecone(str_contest_id)
        if not pinecone_success:
            print(f"[WARNING] Pinecone 삭제 실패 (JSON 데이터는 삭제됨)")
        else:
            print(f"[DELETE_CONTEST] Pinecone 삭제 완료")
        
        # 5. 성공 완료
        print(f"[SUCCESS] 공고 삭제 완료!")
        print(f"[SUCCESS] - 삭제된 ID: {str_contest_id}")
        print(f"[SUCCESS] - 삭제된 제목: {deleted_data.get('title', 'N/A')}")
        print(f"[SUCCESS] - 남은 데이터 수: {len(all_contests_data)}")
        print(f"[DELETE_CONTEST] ==================== 공고 삭제 완료 ====================\n")
        
        return True
        
    except Exception as e:
        # 오류 발생 시 메모리 복구
        print(f"[ERROR] 삭제 중 오류 발생: {e}")
        print(f"[RECOVERY] 메모리 복구 시도...")
        
        try:
            if deleted_data and deleted_index is not None:
                all_contests_data.insert(deleted_index, deleted_data)
                print(f"[RECOVERY] 메모리 복구 완료 ({len(all_contests_data)}개)")
            else:
                print(f"[ERROR] 복구할 데이터가 없음")
        except Exception as recovery_error:
            print(f"[ERROR] 메모리 복구 실패: {recovery_error}")
        
        print(f"[DELETE_CONTEST] ==================== 공고 삭제 실패 ====================\n")
        return False

def _delete_from_pinecone(contest_id):
    """
    Pinecone에서 공고 데이터를 삭제합니다.
    """
    try:
        # RAG 시스템이 사용 가능한지 확인
        try:
            from rag_system import get_rag_chatbot
            chatbot = get_rag_chatbot()
            
            if not chatbot.pinecone_manager.index:
                print("Warning: Pinecone 인덱스가 초기화되지 않아 삭제를 건너뜁니다.")
                return False
                
        except ImportError:
            print("Warning: RAG 시스템을 가져올 수 없어 Pinecone 삭제를 건너뜁니다.")
            return False
        
        # 벡터 ID 구성
        vector_id = f"announcement_{contest_id}"
        
        # Pinecone에서 삭제
        success = chatbot.pinecone_manager.delete_vectors([vector_id])
        
        if success:
            print(f"Pinecone 삭제 성공: {vector_id}")
        else:
            print(f"Pinecone 삭제 실패: {vector_id}")
            
        return success
        
    except Exception as e:
        print(f"Pinecone 삭제 중 오류: {e}")
        return False

def search_contests(keyword, search_fields=None):
    """
    지정된 필드 또는 전체 필드에서 키워드를 포함하는 공고를 검색합니다.
    search_fields가 None이면 모든 문자열 타입의 값을 검색 대상으로 합니다.
    """
    global all_contests_data
    if not all_contests_data:
        load_all_data()
    
    results = []
    lower_keyword = keyword.lower()

    # 검색 대상 필드가 지정되지 않았거나 빈 리스트면, 모든 키를 대상으로 함
    effective_search_fields = search_fields
    if not search_fields:
        # 데이터가 있다면 첫 번째 아이템의 키들을 사용 (모든 아이템이 동일한 키를 가진다고 가정)
        if all_contests_data:
            effective_search_fields = list(all_contests_data[0].keys())
        else: # 데이터가 없으면 검색 불가
            return []
            
    for contest in all_contests_data:
        for field in effective_search_fields:
            if field in contest and isinstance(contest[field], str):
                if lower_keyword in contest[field].lower():
                    results.append(contest)
                    break # 현재 공고는 이미 추가되었으므로 다음 공고로 넘어감
    return results

# 프로그램 시작 시 데이터 로드 (app.py에서 data_handler 임포트 시 실행됨)
load_all_data()

if __name__ == '__main__':
    # 테스트 코드 (선택 사항)
    print("data_handler.py 테스트 시작")

    # 초기 데이터 로드 확인 (load_all_data가 자동으로 호출되었을 것임)
    print(f"초기 로드된 공고 수: {len(get_all_contests())}")
    if get_all_contests():
        print(f"첫번째 공고 샘플: {list(get_all_contests())[0] if get_all_contests() else '없음'}")


    # kstartup_contest_info.json 파일이 비어있거나, 테스트 ID가 이미 존재하면 실패할 수 있음.
    # 테스트 전 파일을 정리하거나 고유한 테스트 ID 사용 권장.

    # 샘플 데이터 추가
    sample_contest_1 = {
        "pblancId": f"TESTID_{uuid.uuid4()}", 
        "pblancNm": "테스트 공고 1 (핸들러)",
        "plBizNm": "테스트 사업 1", "pblancUrl": "http://example.com/test001",
        "rcptEngNm": "테스트기관A", "reqstBeginDt": "20240101", "reqstEndDt": "20240131"
    }
    sample_contest_2 = {
        "pblancId": f"TESTID_{uuid.uuid4()}",
        "pblancNm": "두번째 테스트 공고 (핸들러)",
        "plBizNm": "테스트 사업 2", "pblancUrl": "http://example.com/test002",
        "rcptEngNm": "테스트기관B", "reqstBeginDt": "20240201", "reqstEndDt": "20240228"
    }
    
    print("\n--- 공고 추가 테스트 ---")
    added1 = add_contest(sample_contest_1)
    print(f"{sample_contest_1['pblancId']} 추가 결과: {'성공' if added1 else '실패'}")
    added2 = add_contest(sample_contest_2)
    print(f"{sample_contest_2['pblancId']} 추가 결과: {'성공' if added2 else '실패'}")
    
    print(f"추가 후 공고 수: {len(get_all_contests())}")

    print("\n--- 공고 조회 테스트 ---")
    if added1:
        found_contest = find_contest_by_id(sample_contest_1["pblancId"])
        print(f"{sample_contest_1['pblancId']} 찾음: {found_contest.get('pblancNm') if found_contest else '못찾음'}")

    print("\n--- 공고 수정 테스트 ---")
    if added1:
        update_data = {"pblancNm": "수정된 테스트 공고 1 (핸들러)", "rcptEngNm": "테스트기관AA"}
        updated = update_contest(sample_contest_1["pblancId"], update_data)
        print(f"{sample_contest_1['pblancId']} 수정 결과: {'성공' if updated else '실패'}")
        if updated:
            updated_c = find_contest_by_id(sample_contest_1["pblancId"])
            print(f"수정된 내용: {updated_c.get('pblancNm')}, {updated_c.get('rcptEngNm')}")

    print("\n--- 공고 검색 테스트 (사업명) ---")
    search_results_biz = search_contests("테스트 사업", search_fields=['plBizNm', 'pblancNm'])
    print(f"'테스트 사업' 검색 결과 (사업명, 공고명): {len(search_results_biz)}건")
    for r in search_results_biz:
        print(f"  - {r.get('pblancId')}: {r.get('pblancNm')}")
        
    print("\n--- 공고 삭제 테스트 ---")
    if added2:
        deleted = delete_contest(sample_contest_2["pblancId"])
        print(f"{sample_contest_2['pblancId']} 삭제 결과: {'성공' if deleted else '실패'}")
        
    print(f"삭제 후 공고 수: {len(get_all_contests())}")
    
    print("\n테스트 완료. kstartup_contest_info.json 파일을 확인하세요.")
    print("저장된 파일은 ID를 키로 하는 딕셔너리 형태여야 합니다.")
    print("get_all_contests()는 리스트를 반환해야 합니다.")

    # 확인용: 현재 메모리(all_contests_data)와 파일 내용 비교
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            file_content_type = type(json.load(f))
            print(f"{DATA_FILE}의 최상위 타입: {file_content_type}")
    print(f"get_all_contests() 반환 타입: {type(get_all_contests())}")
    if get_all_contests():
         print(f"get_all_contests() 첫번째 아이템 타입: {type(get_all_contests()[0])}") 