# requirements: selenium, beautifulsoup4, lxml, tqdm, pytz

import json
import os
import time
import ssl
import socket
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from tqdm import tqdm

# === 기본 설정 ===
BASE_URL = "https://www.k-startup.go.kr/web/contents/bizpbanc-ongoing.do"
DETAIL_URL_TEMPLATE = BASE_URL + "?schM=view&pbancSn={}"
JSON_FILE = "kstartup_contest_info.json"
CUTOFF_DATE = datetime.now() - timedelta(days=1)

# === 포트 문제 우회: Selenium 포트 직접 지정 ===
def find_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    addr, port = s.getsockname()
    s.close()
    return port

# === 크롬 드라이버 설정 ===
options = Options()
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')
options.add_argument('--headless=new')

try:
    service = Service(port=find_free_port())
    driver = webdriver.Chrome(service=service, options=options)
    driver.get(BASE_URL)
    time.sleep(2)
except OSError as e:
    print("[드라이버 에러] Chrome 드라이버 실행 실패. 환경 또는 호환성을 확인하세요.")
    raise e

# === 유틸 함수 ===
def get_soup():
    return BeautifulSoup(driver.page_source, "lxml")

def parse_date(text):
    try:
        return datetime.strptime(text.strip(), "%Y-%m-%d")
    except:
        return None

def extract_pbanc_items(soup):
    items = []
    for li in soup.select("#bizPbancList li.notice"):
        title_el = li.select_one(".tit")
        date_text = next((x for x in li.select(".list") if "등록일자" in x.text), None)
        if title_el and date_text:
            try:
                pbancSn = int(title_el.find_parent("a")["href"].split("(")[1].split(")")[0])
                reg_date = parse_date(date_text.text.replace("등록일자", "").strip())
                if reg_date and reg_date <= CUTOFF_DATE:
                    items.append((pbancSn, reg_date))
            except:
                continue
    return items

def go_to_next_page():
    try:
        next_btn = driver.find_element(By.CSS_SELECTOR, ".paginate .next.page_btn")
        driver.execute_script("arguments[0].click();", next_btn)
        time.sleep(1.5)
        return True
    except:
        return False

def load_existing_json():
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(data):
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def extract_detail(pbancSn):
    detail_url = DETAIL_URL_TEMPLATE.format(pbancSn)
    driver.get(detail_url)
    time.sleep(1.5)
    soup = get_soup()

    def get_text_by_label(label):
        el = soup.find("p", string=label)
        return el.find_next("p").text.strip() if el else ""

    # 공고일자 / 공고기관 안전 분기
    date_block = soup.select_one(".box .date")
    if date_block:
        date_parts = [p.strip() for p in date_block.text.strip().split("\n")]
        공고일자 = date_parts[0] if len(date_parts) > 0 else ""
        공고기관 = date_parts[1] if len(date_parts) > 1 else ""
    else:
        공고일자 = ""
        공고기관 = ""

    info = {
        "pbancSn": pbancSn,
        "title": soup.select_one("#scrTitle h3").text.strip() if soup.select_one("#scrTitle h3") else "",
        "지원분야": get_text_by_label("지원분야"),
        "대상연령": get_text_by_label("대상연령"),
        "기관명": get_text_by_label("기관명"),
        "기관구분": get_text_by_label("기관구분"),
        "연락처": get_text_by_label("연락처"),
        "지역": get_text_by_label("지역"),
        "접수기간": get_text_by_label("접수기간"),
        "창업업력": get_text_by_label("창업업력"),
        "대상": get_text_by_label("대상"),
        "담당부서": get_text_by_label("담당부서"),
        "공고번호": soup.select_one(".box .num_txt").text.strip() if soup.select_one(".box .num_txt") else "",
        "공고설명": soup.select_one(".box .txt").text.strip() if soup.select_one(".box .txt") else "",
        "공고일자": 공고일자,
        "공고기관": 공고기관,
    }

    def get_section(title):
        section = soup.find("p", class_="title", string=title)
        if not section:
            return ""
        ul = section.find_next("ul")
        return [li.get_text(" ", strip=True) for li in ul.select(".dot_list")]

    info["신청방법"] = get_section("신청방법 및 대상")
    info["제출서류"] = get_section("제출서류")
    info["선정절차"] = get_section("선정절차 및 평가방법")
    info["지원내용"] = get_section("지원내용")
    info["문의처"] = get_section("문의처")

    files = []
    for li in soup.select(".board_file li.clear"):
        try:
            name = li.select_one("a").text.strip()
            href = li.select(".btn_down a")[-1]["href"]
            files.append({"name": name, "url": f"https://www.k-startup.go.kr{href}"})
        except:
            continue
    info["첨부파일"] = files

    return info

# === 1단계: pbancSn 수집 ===
all_sn = []
while True:
    soup = get_soup()
    items = extract_pbanc_items(soup)
    if not items:
        break
    all_sn.extend(items)
    latest_date = items[-1][1]
    if latest_date > CUTOFF_DATE:
        if not go_to_next_page():
            break
    else:
        break

sn_list = list(set([sn for sn, _ in all_sn]))

# === 2단계: JSON 병합 및 상세 수집 ===
data = load_existing_json()
new_sn = [sn for sn in sn_list if str(sn) not in data]

for sn in tqdm(new_sn, desc="크롤링 중"):
    try:
        data[str(sn)] = extract_detail(sn)
    except Exception as e:
        print(f"[에러] {sn}: {e}")

save_json(data)
driver.quit()