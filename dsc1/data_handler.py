import json
import os
import uuid

# 데이터 파일 경로
DATA_FILE = 'kstartup_contest_info.json'

# 메모리에 로드된 전체 공고 데이터
all_contests_data = []

def load_all_data():
    """
    kstartup_contest_info.json 파일에서 모든 공고 데이터를 로드하여 all_contests_data에 저장합니다.
    파일이 없거나 비어있으면 빈 리스트로 초기화합니다.
    """
    global all_contests_data
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
                if not content.strip(): # 파일 내용이 비어있는 경우
                    all_contests_data = []
                else:
                    all_contests_data = json.loads(content)
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
    """
    global all_contests_data
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_contests_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"데이터 저장 중 오류 발생: {e}")

def get_all_contests():
    """
    메모리에 로드된 모든 공고 데이터를 반환합니다.
    """
    global all_contests_data
    if not all_contests_data and os.path.exists(DATA_FILE): # 메모리에 없지만 파일은 존재할 경우 로드 시도
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
    
    # contest_id가 문자열이 아니면 문자열로 변환
    str_contest_id = str(contest_id)

    for contest in all_contests_data:
        # contest 딕셔너리 내의 ID 필드 (예: 'pblancId')도 문자열로 비교
        # 또는 해당 필드가 숫자일 가능성도 고려해야 함. 우선 문자열로 가정.
        if 'pblancId' in contest and str(contest['pblancId']) == str_contest_id:
            return contest
        # dsrpNo 필드도 ID로 사용될 수 있으므로 추가 확인 (선택 사항)
        # elif 'dsrpNo' in contest and str(contest['dsrpNo']) == str_contest_id:
        #     return contest
    return None

def add_contest(contest_data):
    """
    새로운 공고 데이터를 추가합니다.
    공고 ID (pblancId)가 이미 존재하면 추가하지 않고 False를 반환합니다.
    ID가 없으면 uuid로 자동 생성합니다. (하지만 API 데이터는 pblancId가 있을 것으로 예상)
    """
    global all_contests_data
    if not all_contests_data:
        load_all_data()

    if 'pblancId' not in contest_data or not contest_data['pblancId']:
        # pblancId가 없는 경우, 임시로 UUID를 사용하거나 dsrpNo를 사용할 수 있음.
        # 여기서는 UUID를 사용하지만, 실제 K-Startup 데이터에는 pblancId가 있으므로 이 경우는 드물 것.
        # 혹은 dsrpNo를 고유 ID로 활용하는 것을 고려.
        # 지금은 사용자 입력 데이터에 ID가 없을 경우를 대비해 UUID 생성.
        # 실제 Streamlit UI에서는 필수 입력으로 만들거나, 자동 생성 규칙을 명확히 해야 함.
        temp_id = str(uuid.uuid4())
        # pblancId를 사용하기로 했으므로, 새로운 공고에는 pblancId가 있어야 함.
        # UI 단에서 pblancId 입력을 필수로 하거나, 여기서 생성 규칙을 정해야 함.
        # 여기서는 일단 'pblancId'가 없으면 추가하지 않거나, 혹은 다른 고유 ID를 찾는 로직이 필요.
        # 지금은 pblancId가 제공된다고 가정하고, 없으면 에러 또는 특정 처리를 해야 함.
        # find_contest_by_id는 pblancId를 기준으로 찾으므로, pblancId가 있어야 함.
        if not contest_data.get('pblancId'): # pblancId가 없거나 비어있으면
             # 새로운 ID를 부여하거나, 다른 필드(예: dsrpNo)를 pblancId로 사용하도록 유도
             # 또는 예외 발생. 여기서는 임의의 ID를 부여하지 않고, pblancId가 있어야 한다고 가정.
             # 실제로는 UI에서 입력받거나, 자동 생성 규칙을 따라야 함.
             # 임시로 dsrpNo를 pblancId로 사용하거나, 사용자에게 입력을 요구해야 함.
             # 여기서는 'pblancId'가 없는 경우 생성 로직 추가.
             contest_data['pblancId'] = str(uuid.uuid4()) # 또는 다른 고유값 생성 방식

    # pblancId 기준으로 중복 확인
    if find_contest_by_id(contest_data.get('pblancId')):
        print(f"Error: Contest with ID {contest_data.get('pblancId')} already exists.")
        return False
    
    all_contests_data.append(contest_data)
    save_all_data()
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
    for index, contest in enumerate(all_contests_data):
        if 'pblancId' in contest and str(contest['pblancId']) == str_contest_id:
            # ID 자체는 변경하지 않는다고 가정. updated_data에 ID가 있어도 무시.
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

    if not search_fields: # 검색할 특정 필드가 지정되지 않은 경우
        search_fields = [] # 모든 필드를 대상으로 하도록 설정 (아래 로직에서 자동 감지)


    for contest in all_contests_data:
        # 특정 검색 필드가 지정된 경우
        if search_fields:
            for field in search_fields:
                if field in contest and isinstance(contest[field], str):
                    if lower_keyword in contest[field].lower():
                        results.append(contest)
                        break # 현재 공고는 이미 추가되었으므로 다음 공고로 넘어감
        else: # 특정 검색 필드가 지정되지 않은 경우, 모든 문자열 값에서 검색
            for key, value in contest.items():
                if isinstance(value, str):
                    if lower_keyword in value.lower():
                        results.append(contest)
                        break # 현재 공고는 이미 추가되었으므로 다음 공고로 넘어감
    return results

# 프로그램 시작 시 데이터 로드
load_all_data()

# --- 기존 함수들은 제거되거나 위의 함수들로 대체됩니다. ---
# def get_organizations(): ...
# def get_announcements(): ...
# def get_index(): ...
# def get_organization_by_id(org_id): ...
# def get_announcement_by_id(ann_id): ...
# def add_organization(name): ...
# def add_announcement(title, content, org_id, deadline): ...
# def update_organization(org_id, new_name): ...
# def update_announcement(ann_id, new_title, new_content, new_deadline): ...
# def delete_organization(org_id): ...
# def delete_announcement(ann_id): ...
# def generate_id(): ... # 필요시 add_contest 등에서 uuid.uuid4() 사용
# def search_data(keyword): # search_contests로 대체
# def load_data(): # load_all_data로 대체 및 프로그램 시작 시 호출
# def save_data(): # save_all_data로 대체 및 각 CRUD 함수 내에서 호출

if __name__ == '__main__':
    # 테스트 코드 (선택 사항)
    print("data_handler.py 테스트 시작")

    # 초기 데이터 로드 확인
    print(f"초기 로드된 공고 수: {len(get_all_contests())}")

    # 샘플 데이터 추가
    sample_contest_1 = {
        "pblancId": "TESTID001", # API에서 가져오는 실제 ID 형식 사용 권장
        "pblancNm": "테스트 공고 1",
        "plBizNm": "테스트 사업 1",
        "pblancUrl": "http://example.com/test001",
        "rcptEngNm": "테스트기관A",
        "reqstBeginDt": "20240101",
        "reqstEndDt": "20240131",
        "sprtCtgryNm": "기술개발", # 예시 필드
        "trgetNm": "중소기업"      # 예시 필드
    }
    sample_contest_2 = {
        "pblancId": "TESTID002",
        "pblancNm": "두번째 테스트 공고",
        "plBizNm": "테스트 사업 2",
        "pblancUrl": "http://example.com/test002",
        "rcptEngNm": "테스트기관B",
        "reqstBeginDt": "20240201",
        "reqstEndDt": "20240228",
        "sprtCtgryNm": "사업화",
        "trgetNm": "예비창업자"
    }
    
    # 기존 데이터가 있다면 삭제 후 테스트 (테스트의 일관성을 위해)
    # 주의: 실제 kstartup_contest_info.json 파일이 있다면 백업 후 실행하세요.
    # 또는 테스트용 파일을 따로 사용하세요.
    # 여기서는 간단히 현재 메모리 상의 데이터로만 테스트합니다.
    # 만약 파일에 이미 TESTID001, TESTID002가 있다면 add_contest는 False를 반환합니다.
    # 테스트를 위해 파일을 비우고 시작하거나, 테스트 ID를 변경하세요.
    # all_contests_data = [] # 메모리 초기화 (파일에는 영향 없음, 실제 테스트 시 주의)
    # save_all_data()       # 파일도 초기화하려면 호출


    print("\\n--- 공고 추가 테스트 ---")
    if add_contest(sample_contest_1):
        print("TESTID001 추가 성공")
    else:
        print("TESTID001 추가 실패 (이미 존재하거나 오류 발생)")

    if add_contest(sample_contest_2):
        print("TESTID002 추가 성공")
    else:
        print("TESTID002 추가 실패 (이미 존재하거나 오류 발생)")
    
    print(f"추가 후 공고 수: {len(get_all_contests())}")

    print("\\n--- 공고 조회 테스트 ---")
    found_contest = find_contest_by_id("TESTID001")
    if found_contest:
        print(f"TESTID001 찾음: {found_contest.get('pblancNm')}")
    else:
        print("TESTID001 찾지 못함")

    non_existent_contest = find_contest_by_id("NONEXISTENTID")
    if non_existent_contest:
        print(f"NONEXISTENTID 찾음 (오류): {non_existent_contest.get('pblancNm')}")
    else:
        print("NONEXISTENTID 찾지 못함 (정상)")


    print("\\n--- 공고 수정 테스트 ---")
    update_data = {"pblancNm": "수정된 테스트 공고 1", "rcptEngNm": "테스트기관AA"}
    if update_contest("TESTID001", update_data):
        print("TESTID001 수정 성공")
        updated_c = find_contest_by_id("TESTID001")
        print(f"수정된 내용: {updated_c.get('pblancNm')}, {updated_c.get('rcptEngNm')}")
    else:
        print("TESTID001 수정 실패")

    if update_contest("NONEXISTENTID", update_data):
        print("NONEXISTENTID 수정 성공 (오류)")
    else:
        print("NONEXISTENTID 수정 실패 (정상)")

    print("\\n--- 공고 검색 테스트 (사업명) ---")
    # 검색 필드를 명시적으로 지정: ['plBizNm', 'pblancNm']
    search_results_biz = search_contests("테스트 사업", search_fields=['plBizNm', 'pblancNm'])
    print(f"'테스트 사업' 검색 결과 (사업명, 공고명): {len(search_results_biz)}건")
    for r in search_results_biz:
        print(f"  - {r.get('pblancId')}: {r.get('pblancNm')} (사업명: {r.get('plBizNm')})")
        
    print("\\n--- 공고 검색 테스트 (기관명, 특정 필드) ---")
    search_results_org = search_contests("테스트기관AA", search_fields=['rcptEngNm'])
    print(f"'테스트기관AA' 검색 결과 (기관명): {len(search_results_org)}건")
    for r in search_results_org:
        print(f"  - {r.get('pblancId')}: {r.get('pblancNm')} (기관명: {r.get('rcptEngNm')})")

    print("\\n--- 공고 검색 테스트 (전체 필드, 키워드 '사업화') ---")
    search_results_all = search_contests("사업화") # search_fields=None이면 전체 문자열 필드에서 검색
    print(f"'사업화' 검색 결과 (전체): {len(search_results_all)}건")
    for r in search_results_all:
        print(f"  - {r.get('pblancId')}: {r.get('pblancNm')}")
        for k,v in r.items():
            if isinstance(v,str) and "사업화" in v.lower():
                print(f"    매칭 필드: {k} = {v}")


    print("\\n--- 공고 삭제 테스트 ---")
    if delete_contest("TESTID002"):
        print("TESTID002 삭제 성공")
    else:
        print("TESTID002 삭제 실패")
    
    if delete_contest("NONEXISTENTID"):
        print("NONEXISTENTID 삭제 성공 (오류)")
    else:
        print("NONEXISTENTID 삭제 실패 (정상)")
        
    print(f"삭제 후 공고 수: {len(get_all_contests())}")
    
    # TESTID001도 삭제하여 테스트 환경을 초기 상태로 (선택적)
    # if delete_contest("TESTID001"):
    #     print("TESTID001 삭제 성공 (테스트 정리)")
    # print(f"최종 공고 수: {len(get_all_contests())}")

    print("\\n--- 최종 데이터 상태 ---")
    # print(json.dumps(get_all_contests(), indent=2, ensure_ascii=False))

    print("\\n테스트 완료. kstartup_contest_info.json 파일을 확인하세요.") 