import json
import os
import re
from datetime import datetime

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

if __name__ == '__main__':
    # data_handler.py 직접 실행 시 테스트/초기화 용도
    print("데이터 핸들러 모듈 테스트/초기화...")
    # 1. 크롤링된 데이터가 있다고 가정하고 처리 실행
    # process_raw_data()

    # 2. 데이터 로드 테스트
    # orgs = get_all_organizations()
    # anns = get_all_announcements()
    # print(f"로드된 기관 수: {len(orgs)}")
    # print(f"로드된 공고 수: {len(anns)}")

    # 3. 검색 테스트
    # results = find_announcements(keyword="창업")
    # print(f"'창업' 키워드 검색 결과 (ID 목록): {results}")
    # results = find_announcements(org_name="중소벤처기업부")
    # print(f"'중소벤처기업부' 기관 검색 결과 (ID 목록): {results}")
    # results = find_announcements(keyword="기술", region="서울")
    # print(f"'기술' 키워드 + '서울' 지역 검색 결과 (ID 목록): {results}")
    pass 