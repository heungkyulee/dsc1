# K-Startup 사업 공고 데이터 관리 프로그램

## 1. 팀프로젝트 제목 및 개요

-   **프로젝트 제목:** K-Startup 사업 공고 데이터 관리 및 분석 콘솔 프로그램
-   **개요:**
    본 프로젝트는 `crawler.py`를 통해 수집된 창업지원포털(K-Startup)의 사업 공고 데이터를 효율적으로 관리하고 분석하는 콘솔 기반 프로그램을 개발하는 것을 목표로 합니다. 크롤링된 데이터를 체계적으로 저장 및 관리하고, 사용자가 원하는 정보를 쉽게 검색, 수정, 삭제할 수 있는 CRUD 기능을 제공합니다. 또한, 기관별 공고 게시 빈도 분석 등 부가 기능을 통해 데이터 활용성을 높입니다. 모든 사용자 인터페이스는 **Rich 라이브러리**를 활용하여 가독성 높은 콘솔 환경(CUI)으로 제공됩니다.

## 2. 관리 대상 데이터

### (1) 데이터 구조도 및 설명

본 프로그램은 크롤링된 원본 데이터를 세 개의 JSON 파일로 구조화하여 관리합니다.

-   **기관 정보 (`organizations.json`):**
    -   기관 고유 ID (자체 생성)를 키로 사용합니다.
    -   주요 정보: 기관명 (`name`), 기관 구분 (`type`).
    -   예시: `{"ORG_중소벤처기업부11": {"name": "중소벤처기업부", "type": "정부부처"}, ...}`
-   **공고 정보 (`announcements.json`):**
    -   공고 고유번호 `pbancSn` (문자열)을 키로 사용합니다.
    -   주요 정보: 공고 제목 (`title`), 접수 기간 (`application_period`), 지원 내용 (`support_content`), 담당 기관 ID (`org_id`), 공고일자 (`announcement_date`) 등 크롤링된 상세 정보.
    -   예시: `{"123456": {"title": "2024년 창업도약패키지", "org_id": "ORG_중소벤처기업부11", ...}, ...}`
-   **인덱스 (`index.json`):**
    -   빠른 검색을 위해 주요 필드를 기반으로 구축된 검색용 인덱스입니다.
    -   주요 키: `title_keywords` (제목 키워드), `organization_name` (기관명), `region` (지역), `support_field` (지원분야), `pbancSn_to_orgId` (공고 ID -> 기관 ID 매핑).
    -   각 키는 해당 값을 포함하는 공고 ID(`pbancSn`)들의 리스트를 값으로 가집니다.
    -   예시: `{"organization_name": {"중소벤처기업부": ["123456", "789012"], ...}, "region": {"서울": ["123456", ...]}, ...}`

### (2) 데이터 관리 체계 설명

본 프로그램은 파일에 저장된 JSON 데이터를 Python의 효율적인 내장 자료구조를 활용하여 메모리 상에서 관리합니다. 각 데이터의 특성과 주된 사용 방식(삽입 빈도 vs 검색 빈도)을 고려하여 다음과 같은 관리 체계를 채택했습니다.

-   **핵심 자료구조:** **딕셔너리 (Dictionary)** 와 **리스트 (List)**

-   **데이터별 관리 방식 및 근거:**
    -   **원본 데이터 (`kstartup_contest_info.json` 참조):**
        -   **특성:** `crawler.py`를 통해 주기적으로 새로운 공고 정보가 추가되어 파일 내용이 **삽입/갱신**되는 경우가 빈번한 데이터 소스입니다.
        -   **관리:** 프로그램은 메뉴 1번(원본 데이터 처리) 실행 시 이 파일을 읽어들여, 내부적으로 구조화된 데이터(아래의 기관/공고/인덱스 딕셔너리)를 생성/업데이트합니다. 원본 파일 자체는 읽기 전용 소스로 사용됩니다.
    -   **기관 정보 (`organizations.json`) 및 공고 정보 (`announcements.json`):**
        -   **특성:** 프로그램 실행 중에는 특정 기관이나 공고의 상세 정보를 조회하거나(Retrieve), 수정(Update), 삭제(Delete)하는 등 ID 기반의 **검색 및 접근** 작업이 빈번하게 발생합니다.
        -   **관리:** 이 데이터들은 각각 기관 ID 또는 공고 ID(`pbancSn`)를 키로 사용하는 Python **딕셔너리**로 메모리에 로드되어 관리됩니다. 딕셔너리는 평균 O(1)의 시간 복잡도로 특정 키에 해당하는 값(기관 또는 공고 정보)에 매우 빠르게 접근할 수 있어, ID 기반의 빈번한 **검색, 수정, 삭제** 요구사항에 효과적으로 대응합니다.
    -   **인덱스 (`index.json`):**
        -   **특성:** 제목 키워드, 기관명, 지역 등 다양한 조건으로 공고를 **검색/필터링**하는 기능을 빠르게 수행하기 위해 사용됩니다.
        -   **관리:** 검색 기준이 되는 값(예: '중소벤처기업부', '서울', '창업')을 키로 하고, 해당 값을 가지는 공고 ID들의 **리스트**를 값으로 갖는 중첩된 **딕셔너리** 형태로 로드됩니다. 사용자가 특정 조건으로 검색하면, 이 인덱스 딕셔너리를 통해 해당 조건의 키로 공고 ID 리스트를 즉시 얻을 수 있습니다 (O(1) 평균). 이는 전체 공고 데이터를 순회하며 조건을 비교하는 방식보다 훨씬 효율적입니다. 여기서 **리스트**는 특정 조건을 만족하는 ID들을 모아두는 역할을 수행합니다.

-   **데이터 관리 흐름 요약:**
    1.  **처리(Create):** 삽입/갱신이 빈번한 원본 데이터를 읽어(메뉴 1), 검색/접근에 최적화된 기관/공고/인덱스 **딕셔너리** 구조로 변환하여 메모리에 로드하고 파일로 저장합니다.
    2.  **조회(Retrieve):** 검색 조건에 따라 **인덱스 딕셔너리**를 사용하여 관련 공고 ID **리스트**를 신속하게 찾고, 이 ID를 이용해 **공고 딕셔너리**에서 상세 정보를 효율적으로 가져옵니다.
    3.  **수정/삭제(Update/Delete):** 대상 ID를 키로 사용하여 **기관/공고 딕셔너리**에 빠르게 접근하여 데이터를 변경/제거하고 파일에 반영합니다. (단, 현재 인덱스 동기화는 수동 업데이트 필요)

## 3. 주요 기능

### (1) 기본 기능 : CRUD + P

-   **Create (생성/처리):** `crawler.py`가 수집한 원본 JSON 데이터를 읽어, 구조화된 기관/공고/인덱스 JSON 파일들을 생성 및 업데이트합니다. (데이터 관리 체계 기반)
-   **Retrieve (조회):**
    -   전체 기관 목록 보기 (기관 딕셔너리 활용).
    -   전체 공고 목록 보기 (공고 딕셔너리 활용).
    -   조건 검색/필터링: 키워드(제목), 기관명, 지역, 지원분야 등 다양한 조건을 조합하여 공고 검색 (인덱스 딕셔너리 활용).
    -   공고 상세 정보 보기: 특정 공고 ID를 입력받아 상세 정보 출력 (공고 딕셔너리 활용).
-   **Update (수정):** 특정 공고 ID를 지정하여 공고 정보(현재는 제목만)를 수정하고 `announcements.json` 파일에 반영합니다.
-   **Delete (삭제):** 특정 공고 ID를 지정하여 공고 정보를 `announcements.json`에서 삭제합니다.
-   **Print (출력):** 모든 조회 결과(목록, 상세 정보, 분석 결과)를 **Rich 라이브러리**의 `Table`, `Panel` 등을 활용하여 콘솔에 가독성 높게 출력합니다.

### (2) 추가 기능

-   **기관별 공고 게시 빈도 시계열 분석:**
    -   `pandas` 라이브러리를 활용하여 `announcements.json`의 공고일자 데이터를 분석합니다.
    -   기관별로 월별 또는 지정된 주기별 공고 게시 횟수를 집계합니다.
    -   분석 결과를 Rich `Table` 형식으로 콘솔에 시각화하여 기관들의 활동 추세를 파악할 수 있도록 지원합니다.

## 4. 팀구성 및 역할분담

### (1) 팀 구성

-   팀명: (팀명 입력)
-   팀원:
    -   (이름 1)
    -   (이름 2)
    -   (이름 3)
    -   ...

### (2) 역할 분담

-   **(이름 1):** (담당 역할 상세 기술, 예: 프로젝트 총괄, README 작성, 데이터 구조 설계, CRUD 기능 구현)
-   **(이름 2):** (담당 역할 상세 기술, 예: `crawler.py` 기능 개선 및 유지보수, 데이터 인덱싱 로직 구현, 검색 기능 구현)
-   **(이름 3):** (담당 역할 상세 기술, 예: `analysis.py` 모듈 구현 (시계열 분석), Rich 기반 UI/UX 설계 및 구현, 테스트 및 디버깅)

### (3) 개발 일정 (14주차까지 예시)

| 주차 | 주요 개발 내용                     | 담당자 (예시)   | 비고                                   |
| :--- | :--------------------------------- | :-------------- | :------------------------------------- |
| 9주차  | 요구사항 분석 및 기획 구체화        | 팀 전체         | README 초안 작성                       |
| 10주차 | 데이터 구조 설계 및 `crawler.py` 검토 | 이름 1, 이름 2  | JSON 구조 확정, 크롤러 안정화          |
| 11주차 | `data_handler.py` (Create, Index) 구현 | 이름 2         | 데이터 처리 및 인덱싱 로직 구현        |
| 12주차 | `data_handler.py` (Retrieve) 및 `main.py` (기본 UI, 조회 연동) 구현 | 이름 1, 이름 3 | 검색 기능 및 Rich 기본 출력 구현       |
| 13주차 | CRUD (Update, Delete) 기능 구현 및 `analysis.py` (시계열 분석) 구현 | 이름 1, 이름 3 | 남은 CRUD 구현, 분석 로직 개발       |
| 14주차 | 최종 테스트, UI 개선, 문서화 및 발표 준비 | 팀 전체         | 버그 수정, README 최종화, 발표자료 제작 |