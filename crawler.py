# requirements: requests, tqdm, pytz

import requests
import json
import os
from datetime import datetime, timedelta # CUTOFF_DATE 등을 위해 유지
from tqdm import tqdm
import time
import ssl
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context
import urllib3 # 추가

# SSL 검증 비활성화 시 발생하는 InsecureRequestWarning을 무시 (verify=False 사용 시 권장)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# === 기본 설정 ===
# 서비스설계서 기반으로 "지원사업 공고 정보" API의 Call Back URL 사용
BASE_URL = "https://apis.data.go.kr/B552735/kisedKstartupService01/getAnnouncementInformation01"
SERVICE_KEY = "XF6TR4JT8oOCoXwVPiqzRFQ5lWsUmoqTp88Kln0ndIS6dJJtrDMQb8ZI2aE4tZKumyT+2wGF1bWesMrsguh9kg==" # 제공된 디코딩된 인증키
JSON_FILE = "kstartup_contest_info.json"

# === SSL 컨텍스트 커스터마이징 ===
class CustomHttpAdapter(HTTPAdapter):
    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        context = create_urllib3_context()
        # 일반적인 호환성 높은 cipher list 설정 시도
        context.set_ciphers(
            'ECDH+AESGCM:DH+AESGCM:ECDH+AES256:DH+AES256:ECDH+AES128:DH+AES:ECDH+HIGH:'
            'DH+HIGH:ECDH+3DES:DH+3DES:RSA+AESGCM:RSA+AES:RSA+HIGH:RSA+3DES:!aNULL:'
            '!eNULL:!MD5:!DSS' # !DSS 추가
        )
        # SSL 검증 비활성화 및 호스트네임 체크 비활성화 명시
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        pool_kwargs['ssl_context'] = context
        # self.poolmanager = PoolManager(**pool_kwargs) # urllib3 < 2.0
        # For urllib3 >= 2.0, a different approach might be needed if PoolManager init changes.
        # However, passing ssl_context via pool_kwargs to super should generally work.
        super().init_poolmanager(connections, maxsize, block, **pool_kwargs)

# 기존 JSON 파일을 로드하는 함수
def load_existing_json():
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                print(f"[경고] {JSON_FILE} 파일이 비어있거나 손상되어 초기화합니다.")
                return {}
    return {}

# JSON 데이터를 파일에 저장하는 함수
def save_json(data):
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"'{JSON_FILE}' 파일에 성공적으로 저장되었습니다.")

# API 응답 아이템을 내부 데이터 형식으로 변환하는 함수 (서비스설계서 기반)
def api_item_to_custom_format(item):
    if not item or not isinstance(item, dict):
        return None

    pbanc_sn_val = item.get("pbanc_sn") # 공고일련번호
    if not pbanc_sn_val:
        return None

    application_period_start = item.get("pbanc_rcpt_bgng_dt", "") # 공고 접수 시작 일시
    application_period_end = item.get("pbanc_rcpt_end_dt", "")    # 공고 접수 종료 일시
    application_period = f"{application_period_start} ~ {application_period_end}" if application_period_start and application_period_end else ""

    # 첨부파일 정보 파싱 (API 명세에 첨부파일 관련 필드가 명시되어 있지 않음. 필요시 추가 가정 또는 확인 필요)
    # 예시: item.get("atchFileList", []) -> 서비스설계서에는 첨부파일 필드가 없음
    attachments = [] 

    info = {
        "pbancSn": str(pbanc_sn_val),
        "title": item.get("biz_pbanc_nm", ""),  # 지원 사업 공고 명
        "지원분야": item.get("supt_biz_clsfc", ""), # 지원 분야
        "대상연령": item.get("biz_trgt_age", ""), # 대상 연령
        "기관명": item.get("pbanc_ntrp_nm", ""), # 창업 지원 기관명 (API 명세에는 "주관 기관"(sprv_inst)도 있음)
        "기관구분": item.get("sprv_inst", ""), # 주관 기관 (기관구분으로 사용)
        "연락처": item.get("prch_cnpl_no", ""), # 담당자 연락처
        "지역": item.get("supt_regin", ""), # 지역명
        "접수기간": application_period,
        "창업업력": item.get("biz_enyy", ""), # 창업 기간
        "대상": item.get("aply_trgt", ""), # 신청 대상
        "담당부서": item.get("biz_prch_dprt_nm", ""), # 사업 담당자 부서명
        "공고번호": item.get("pbanc_sn", ""), # API 응답의 공고일련번호를 공고번호로 사용 (원본 데이터와 형식 통일)
        "공고설명": item.get("pbanc_ctnt", ""), # 공고 내용
        # "공고일자": API 응답 명세에 "공고일자"에 해당하는 직접적인 필드가 없음.
        # 가장 유사한 것은 "공고 접수 시작 일시"(pbanc_rcpt_bgng_dt)의 날짜 부분일 수 있음.
        # 여기서는 접수 시작일시의 날짜 부분만 사용하도록 가정.
        "공고일자": application_period_start.split(" ")[0] if application_period_start else "",
        "공고기관": item.get("pbanc_ntrp_nm", ""), # 창업 지원 기관명 (기관명과 동일하게 사용)

        # 서비스 설계서에 명시된 "신청 방법" 관련 필드들 통합
        "신청방법": [
            f"방문접수: {item.get('aply_mthd_vst_rcpt_istc', '')}".strip(),
            f"우편접수: {item.get('aply_mthd_pssr_rcpt_istc', '')}".strip(),
            f"팩스접수: {item.get('aply_mthd_fax_rcpt_istc', '')}".strip(),
            f"이메일접수: {item.get('aply_mthd_eml_rcpt_istc', '')}".strip(),
            f"온라인접수: {item.get('aply_mthd_onli_rcpt_istc', '')}".strip(),
            f"기타: {item.get('aply_mthd_etc_istc', '')}".strip(),
        ],
        "제출서류": item.get("aply_excl_trgt_ctnt", ""), # 신청제외대상내용을 제출서류로 임시 사용 (확인필요)
                                                       # 또는 pbanc_ctnt (공고내용)에서 파싱해야 할 수도 있음
        "선정절차": "", # API 명세에 명확한 필드 없음. pbanc_ctnt에서 추출 필요 가능성.
        "지원내용": item.get("pbanc_ctnt", ""), # 공고 내용을 지원내용으로 사용 (또는 더 구체적인 필드 필요)
        "문의처": item.get("prch_cnpl_no", ""), # 담당자 연락처를 문의처로 사용
        
        "첨부파일": attachments # 위에서 정의한 attachments 리스트
    }
    # 비어 있는 설명 문자열 필터링
    info["신청방법"] = [s for s in info["신청방법"] if ": " != s[-2:] and s.split(": ")[1]]
    return info

# 모든 공고 정보를 API를 통해 가져오는 함수
def fetch_all_announcements_from_api():
    existing_data = load_existing_json()
    all_fetched_items = {}

    # 세션 생성 및 어댑터 마운트
    session = requests.Session()
    session.mount('https://', CustomHttpAdapter())

    page_no = 1
    num_of_rows = 100 # 서비스 설계서 기본값(10)보다 크게 설정, 최대치는 확인 필요
    total_items_fetched = 0
    
    print("공공데이터포털에서 K-Startup 지원사업 공고 정보를 가져옵니다...")

    while True:
        params = {
            "serviceKey": SERVICE_KEY,
            "page": str(page_no), # 파라미터명 변경: pageNo -> page
            "perPage": str(num_of_rows), # 파라미터명 변경: numOfRows -> perPage
            "returnType": "JSON", # 파라미터명 변경: dataType -> returnType (명시)
            # 서비스설계서에 따르면, "지원사업 공고 정보" API는 아래와 같은 추가 검색 파라미터 사용 가능
            # "intg_pbanc_yn": "N", # 통합 공고 여부 (예시)
            # "biz_pbanc_nm": "창업", # 지원 사업 공고 명 (예시)
            # "Rcrt_prgs_yn": "Y" # 모집진행여부 (예시)
        }
        
        try:
            response = session.get(BASE_URL, params=params, timeout=30, verify=False) # SSL 검증 비활성화 (테스트용)
            response.raise_for_status()
            content = response.json()
            
            # 실제 API 응답 구조에 맞게 수정
            # current_items = content.get("data", []) # "data" 필드가 아이템 리스트로 추정
            # total_count_val = content.get("totalCount", content.get("matchCount", 0)) # totalCount 필드 확인
            # current_count_val = content.get("currentCount", len(current_items)) 

            # 상세 API 응답 구조를 보고 아래 경로를 정확히 수정해야 합니다.
            # 예시 응답: {'currentCount': 100, 'data': [...], 'page': 1, 'perPage': 100, 'totalCount': 500}

            current_items = content.get("data", [])
            if not isinstance(current_items, list):
                current_items = [current_items] if current_items else [] # 단일 아이템일 경우 리스트로

            # 응답에서 totalCount, page, perPage 정보를 가져오려고 시도
            # API마다 필드명이 다를 수 있으므로, 여러 가능성을 고려하거나 실제 응답을 보고 확정해야 함
            total_count = int(content.get("totalCount", 0))
            current_page_from_response = int(content.get("page", page_no)) # API가 현재 페이지 번호를 알려주면 사용
            per_page_from_response = int(content.get("perPage", num_of_rows)) # API가 페이지당 항목 수를 알려주면 사용
            api_current_count = int(content.get("currentCount", len(current_items))) # API가 현재 페이지 아이템 수를 알려주면 사용

            if not current_items and page_no > 1:
                print("더 이상 가져올 데이터가 없습니다.")
                break
            elif not current_items and page_no == 1:
                 print("API에서 반환된 데이터가 없습니다. API 키, 엔드포인트, 파라미터를 확인하세요.")
                 print(f"응답 내용(일부): {str(content)[:1000]}") # 로그 길이 증가
                 return

            new_items_count_in_page = 0
            for item_data in current_items:
                formatted_item = api_item_to_custom_format(item_data)
                if formatted_item and formatted_item["pbancSn"]:
                    all_fetched_items[formatted_item["pbancSn"]] = formatted_item
                    new_items_count_in_page +=1
            
            total_items_fetched += new_items_count_in_page
            print(f"페이지 {page_no} (API 응답 페이지: {current_page_from_response}): {new_items_count_in_page}개 공고 처리 (API currentCount: {api_current_count}, 누적: {total_items_fetched}개)")

            # === 최대 10000개 제한 추가 ===
            if total_items_fetched >= 10000:
                print(f"데이터 수집 최대 제한인 10000개에 도달했거나 초과했습니다. (현재: {total_items_fetched}개)")
                break
            # === 제한 추가 끝 ===

            # 페이징 종료 조건 수정
            if total_count > 0: # totalCount 정보가 있다면 그것을 우선 사용
                if total_items_fetched >= total_count: # 지금까지 가져온 총 아이템 수가 totalCount 이상이면 종료
                    print(f"모든 페이지의 데이터를 가져왔습니다 (totalCount: {total_count} 도달).")
                    break
                elif not current_items : # 현재 페이지에 아이템이 없는데 totalCount에 도달 못했으면 뭔가 이상함 (일단 종료)
                    print(f"현재 페이지에 아이템이 없으나 totalCount({total_count})에 도달하지 못했습니다. 페이징을 중단합니다.")
                    break
            else: # totalCount 정보가 없다면 (0 또는 누락)
                if not current_items and page_no > 1: # 첫 페이지가 아니고, 현재 페이지에 아이템이 없으면 종료
                    print("totalCount 정보 없이, 현재 페이지에 아이템이 없어 페이징을 종료합니다.")
                    break
                elif not current_items and page_no == 1:
                     print("첫 페이지부터 아이템이 없습니다. (totalCount 정보 없음)")
                     break # 이미 위에서 처리했지만, 방어적으로 추가
            
            # 다음 페이지로 이동하기 전, API가 알려준 perPage와 currentCount를 비교하여 마지막 페이지인지 추론
            if api_current_count < per_page_from_response and page_no > 0 : # 현재 페이지 아이템 수가 요청한 perPage보다 적으면 마지막 페이지일 가능성
                print(f"현재 페이지 아이템 수({api_current_count})가 요청한 perPage({per_page_from_response})보다 적어 마지막 페이지로 간주하고 종료합니다.")
                break

            page_no += 1
            time.sleep(0.3) # API 서버 부하 감소를 위한 딜레이 (0.5초 -> 0.3초)

        except requests.exceptions.Timeout:
            print(f"API 요청 시간 초과 (페이지: {page_no}).")
            break 
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP 오류 발생 (페이지: {page_no}): {http_err}")
            print(f"응답 내용(일부): {response.text[:500]}")
            break
        except requests.exceptions.RequestException as req_err:
            print(f"API 요청 중 오류 발생 (페이지: {page_no}): {req_err}")
            break
        except json.JSONDecodeError:
            print(f"API 응답이 유효한 JSON이 아닙니다 (페이지: {page_no}). 응답 내용(일부): {response.text[:500]}")
            break
        except Exception as e:
            print(f"알 수 없는 오류 발생 (페이지: {page_no}): {e}")
            break

    if not all_fetched_items and not existing_data:
        print("최종적으로 수집된 공고 데이터가 없습니다.")
        return

    print(f"총 {len(all_fetched_items)}개의 공고 정보를 API로부터 수집/처리했습니다.")
    
    updated_data_count = 0
    newly_added_count = 0
    for sn, item_info in all_fetched_items.items():
        if sn in existing_data:
            existing_data[sn] = item_info # 단순 덮어쓰기
            updated_data_count +=1
        else:
            existing_data[sn] = item_info
            newly_added_count +=1
            
    print(f"{newly_added_count}개의 새로운 공고가 추가되었고, {updated_data_count}개의 기존 공고가 업데이트(또는 유지)되었습니다.")
    save_json(existing_data)

def collect_data():
    """데이터를 수집하는 메인 함수"""
    fetch_all_announcements_from_api()

if __name__ == "__main__":
    fetch_all_announcements_from_api()