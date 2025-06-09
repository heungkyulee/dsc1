import json
import os
import re
from datetime import datetime
import uuid

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
        print(f"[정보] {RAW_DATA_FILE} 파일이 비어있거나 찾을 수 없습니다. 처리를 건너<0xEB><0x9B><0x81>니다.")
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
            print(f"[경고] 공고 {pbancSn}의 기관명을 찾을 수 없습니다. 건너<0xEB><0x9B><0x81>니다.")
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
        announcement_entry = {
            "title": ann_data.get("title", ""),
            "support_field": ann_data.get("지원분야", ""),
            "target_age": ann_data.get("대상연령", ""),
            "org_name_ref": org_name,
            "org_id": org_id,
            "contact": ann_data.get("연락처", ""),
            "region": ann_data.get("지역", ""),
            "application_period": ann_data.get("접수기간", ""),
            "startup_experience": ann_data.get("창업업력", ""),
            "target_audience": ann_data.get("대상", ""),
            "department": ann_data.get("담당부서", ""),
            "announcement_number": ann_data.get("공고번호", ""),
            "description": ann_data.get("공고설명", ""),
            "announcement_date": ann_data.get("공고일자", ""),
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
    """특정 공고 정보를 업데이트합니다. (인덱스 업데이트는 단순화)"""
    announcements = load_json(ANNS_FILE)
    if pbancSn_str not in announcements:
        print(f"[에러] 공고 ID {pbancSn_str}를 찾을 수 없습니다.")
        return False

    # TODO: 실제 업데이트 시에는 기존 인덱스 제거 및 새 인덱스 추가 필요
    # 여기서는 announcements.json만 업데이트
    announcements[pbancSn_str].update(updated_data)
    save_json(announcements, ANNS_FILE)

    # 인덱스 업데이트 (간단하게 다시 전체 처리)
    # process_raw_data() # 비효율적일 수 있음. 부분 업데이트 로직 필요.
    print(f"[정보] 공고 {pbancSn_str} 업데이트 완료. (인덱스 업데이트 필요시 process_raw_data() 재실행 권장)")
    return True

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
    kstartup_contest_info.json 파일에서 모든 공고 데이터를 로드하여 all_contests_data에 저장합니다.
    파일이 없거나 비어있으면 빈 리스트로 초기화합니다.
    JSON 최상위 구조가 딕셔너리인 경우 값의 리스트로 변환합니다.
    """
    global all_contests_data
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
                if not content.strip(): # 파일 내용이 비어있는 경우
                    all_contests_data = []
                else:
                    loaded_json = json.loads(content)
                    if isinstance(loaded_json, dict):
                        all_contests_data = list(loaded_json.values()) # 딕셔너리면 값들의 리스트로 변환
                    elif isinstance(loaded_json, list):
                        all_contests_data = loaded_json # 이미 리스트면 그대로 사용
                    else:
                        # 예상치 못한 형식이거나, 혹은 단일 객체가 파일 전체일 경우
                        print(f"[경고] {DATA_FILE} 내용이 예상치 못한 형식입니다. ({type(loaded_json)})")
                        all_contests_data = [] 
        except json.JSONDecodeError:
            all_contests_data = [] # JSON 파싱 오류 시 빈 리스트로 초기화
        except Exception as e:
            print(f"데이터 로딩 중 오류 발생: {e}")
            all_contests_data = []
    else:
        all_contests_data = []

def save_all_data():
    """
    all_contests_data의 내용을 kstartup_contest_info.json 파일에 저장합니다.
    주의: crawler.py는 딕셔너리 형태로 저장하므로, 여기서 리스트를 저장하면
    crawler.py의 load_existing_json()과의 호환성 문제가 생길 수 있습니다.
    crawler.py도 리스트 형태로 저장하거나, 여기서 저장할 때 crawler.py의 형식에 맞춰야 합니다.
    현재 crawler.py는 ID를 키로 하는 딕셔너리를 저장합니다.
    이 함수는 data_handler 내부에서 CRUD 작업 후 호출되므로, 
    all_contests_data (리스트)를 다시 딕셔너리 형태로 변환하여 저장하는 것이 일관성에 좋습니다.
    """
    global all_contests_data
    data_to_save = {item['pblancId']: item for item in all_contests_data if 'pblancId' in item}
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"데이터 저장 중 오류 발생: {e}")

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
    공고 ID (pblancId)가 이미 존재하면 추가하지 않고 False를 반환합니다.
    """
    global all_contests_data
    if not all_contests_data: # load_all_data는 리스트를 가져옴
        load_all_data()

    if 'pblancId' not in contest_data or not contest_data['pblancId']:
        # UI에서 ID 입력을 강제하거나 여기서 생성 규칙 정의 필요
        # 지금은 ID가 있다고 가정, 없으면 False 반환 또는 에러 발생
        print("Error: pblancId is required to add a new contest.")
        # contest_data['pblancId'] = str(uuid.uuid4()) # 임시 ID 생성 (정책에 따라)
        return False

    if find_contest_by_id(contest_data.get('pblancId')):
        print(f"Error: Contest with ID {contest_data.get('pblancId')} already exists.")
        return False
    
    all_contests_data.append(contest_data) # 리스트에 추가
    save_all_data() # 저장 시 딕셔너리로 변환됨
    return True

def update_contest(contest_id, updated_data):
    """
    기존 공고 데이터를 수정합니다.
    contest_id (pblancId)를 사용하여 공고를 찾고, updated_data로 내용을 업데이트합니다.
    """
    global all_contests_data
    if not all_contests_data:
        load_all_data()
    
    str_contest_id = str(contest_id)
    for index, contest in enumerate(all_contests_data): # 리스트 순회
        if 'pblancId' in contest and str(contest['pblancId']) == str_contest_id:
            original_id = contest['pblancId']
            all_contests_data[index].update(updated_data)
            all_contests_data[index]['pblancId'] = original_id # ID 변경 방지
            save_all_data()
            return True
    print(f"Error: Contest with ID {str_contest_id} not found for update.")
    return False

def delete_contest(contest_id):
    """
    주어진 ID (pblancId)를 가진 공고를 삭제합니다.
    """
    global all_contests_data
    if not all_contests_data:
        load_all_data()

    str_contest_id = str(contest_id)
    original_length = len(all_contests_data)
    # 리스트 컴프리헨션으로 삭제
    all_contests_data = [contest for contest in all_contests_data if not ('pblancId' in contest and str(contest['pblancId']) == str_contest_id)]
    
    if len(all_contests_data) < original_length:
        save_all_data()
        return True
    
    print(f"Error: Contest with ID {str_contest_id} not found for deletion.")
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
            
    for contest in all_contests_data: # 리스트 순회
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