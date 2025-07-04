# 데이터사이언스와컴퓨팅1 팀 프로젝트 제안서

**프로젝트 제목:** K-Startup 사업 공고 데이터 관리 및 분석 콘솔 프로그램

**팀명:** SKKartup
**팀 구성:**

- 이흥규 (팀장)
- 노건준 (팀원)

**제출일:** {current_date}

---

## 1. 제안 배경 및 목표

### (1) 배경

정부 및 공공기관에서 지원하는 스타트업 관련 사업 공고는 다양한 플랫폼에 분산되어 제공되며, 정보의 양이 방대하여 사용자가 원하는 정보를 효율적으로 찾고 관리하기 어렵습니다. 특히, K-Startup 사이트는 많은 공고 정보를 포함하고 있지만, 웹사이트 내에서의 검색 및 관리 기능에는 한계가 있습니다.

### (2) 목표

본 프로젝트는 Python을 이용하여 K-Startup 사이트의 사업 공고 데이터를 자동으로 수집(`crawler.py` 활용)하고, 이를 효과적으로 관리 및 분석할 수 있는 **콘솔 기반 데이터 관리 프로그램** 개발을 목표로 합니다. 사용자는 이 프로그램을 통해 다음을 수행할 수 있습니다:

- 체계적으로 구조화된 공고 데이터를 관리 (Create)
- 다양한 조건으로 원하는 공고 정보를 신속하게 검색 및 조회 (Retrieve)
- 필요에 따라 공고 정보 수정 및 삭제 (Update, Delete)
- 조회된 정보를 가독성 높은 형태로 확인 (Print)
- 기관별 공고 게시 빈도 분석 등 부가적인 정보 획득

## 2. 관리 대상 데이터

### (1) 데이터 구조도 및 설명

본 프로그램은 `crawler.py`를 통해 수집된 원본 데이터를 다음 세 개의 JSON 파일로 구조화하여 관리합니다. 이는 데이터의 성격과 접근 패턴을 고려한 설계입니다.

- **기관 정보 (`organizations.json`):** 기관 고유 ID를 키로 하여 기관명, 기관 구분 등 기관 고유 정보를 저장합니다. (예: `{{"ORG_...": {{"name": "...", "type": "..."}}, ...}}`)
- **공고 정보 (`announcements.json`):** 공고 고유번호 `pbancSn`을 키로 하여 공고 제목, 접수 기간, 담당 기관 ID 등 공고별 상세 정보를 저장합니다. (예: `{{"123456": {{"title": "...", "org_id": "ORG_...", ...}}, ...}}`)
- **인덱스 (`index.json`):** 빠른 검색을 위해 기관명, 지역, 지원분야 등 주요 필드 값을 키로 하고, 해당 값을 포함하는 공고 ID(`pbancSn`)들의 리스트를 값으로 갖는 역 인덱스 구조입니다. (예: `{{"organization_name": {{"기관명": ["123456", ...], ...}}, ...}}`)

### (2) 데이터 관리 체계 설명

프로그램 내부에서는 파일에 저장된 JSON 데이터를 Python의 효율적인 내장 자료구조인 **딕셔너리(Dictionary)** 와 **리스트(List)** 를 사용하여 메모리 상에서 관리합니다.

- **기관/공고 데이터 관리 (딕셔너리 활용):** `organizations.json`과 `announcements.json`은 각각 ID(기관 ID, 공고 ID)를 키로 하는 **딕셔너리**로 로드됩니다. 이는 특정 정보에 대한 **검색(Retrieve), 수정(Update), 삭제(Delete)** 작업 시 평균 O(1) 시간 복잡도로 매우 빠르게 데이터에 접근할 수 있게 하여 프로그램의 반응성을 높입니다. 검색이 빈번한 데이터 특성에 최적화된 방식입니다.
- **인덱스 데이터 관리 (딕셔너리 + 리스트 활용):** `index.json`은 검색 조건을 키로 하고 공고 ID 리스트를 값으로 갖는 중첩된 **딕셔너리** 구조로 로드됩니다. 사용자가 특정 조건(예: 기관명 '중소벤처기업부')으로 검색하면, 해당 키를 통해 관련 공고 ID **리스트** `["123456", "789012"]`를 즉시 얻을 수 있습니다. 이는 전체 데이터를 순회하지 않고도 **검색(Retrieve)** 성능을 크게 향상시킵니다. 리스트는 조건을 만족하는 ID 집합을 관리하는 데 사용됩니다.
- **원본 데이터 처리 (Create):** `kstartup_contest_info.json`은 **삽입/갱신**이 빈번한 원본 소스로, 프로그램은 이를 읽어 위에서 설명한 검색 및 접근에 효율적인 딕셔너리 기반 구조로 변환하여 관리합니다.

## 3. 주요 기능 구현 계획

### (1) 기본 기능 : CRUD + P

- **Create:** 원본 크롤링 데이터를 로드하여 구조화된 기관/공고/인덱스 딕셔너리로 변환하고 JSON 파일로 저장합니다.
- **Retrieve:** 다양한 조건(키워드 부분 검색, 기관명, 지역, 지원분야 등)을 조합하여 인덱스를 활용, 효율적으로 공고를 검색하고 전체/상세 정보를 조회합니다.
- **Update:** 지정된 공고 ID의 정보(현재: 제목)를 수정하고 JSON 파일에 반영합니다.
- **Delete:** 지정된 공고 ID의 정보를 확인 후 JSON 파일에서 삭제합니다.
- **Print:** 모든 조회/분석 결과를 Rich 라이브러리를 사용하여 가독성 높은 테이블, 패널 등으로 콘솔에 출력합니다.

### (2) 추가 기능

- **기관별 공고 게시 빈도 분석:** `pandas`를 이용하여 기관별 월별 공고 수를 집계하고, 결과를 시계열 테이블 형태로 시각화하여 기관 활동 동향 파악을 지원합니다.

## 4. 팀 구성 및 개발 계획

### (1) 팀 구성

- **팀장:** 이흥규
- **팀원:** 노건준

### (2) 역할 분담

- **이흥규 (팀장):**
  - 프로젝트 총괄 및 일정 관리
  - 데이터 구조 설계 및 `data_handler.py` (CRUD 핵심 로직) 구현
  - `README.md` (제안서 및 최종 보고서) 작성 주도
  - 전체 코드 통합 및 최종 테스트
- **노건준 (팀원):**
  - `crawler.py` 기능 검토 및 유지보수
  - 데이터 인덱싱 로직 구현 (`data_handler.py` 보조)
  - `analysis.py` (시계열 분석) 모듈 구현
  - Rich 기반 CUI 설계 및 `main.py` 구현
  - 기능별 테스트 및 디버깅

### (3) 개발 일정 (예상: 9주차 ~ 14주차)

| 주차    | 주요 개발 내용                                                     | 담당자         | 비고                                 |
| :------ | :----------------------------------------------------------------- | :------------- | :----------------------------------- |
| ~ 9주차 | 주제 선정 및 팀 구성 완료, 요구사항 분석                           | 팀 전체        | 완료 (본 제안서 작성)                |
| 10주차  | 데이터 구조 상세 설계, `crawler.py` 분석/개선점 파악               | 이흥규, 노건준 | JSON 구조 확정                       |
| 11주차  | `data_handler.py`: 데이터 로드/저장, Create(처리), Indexing 구현   | 노건준         | 데이터 변환 및 인덱스 생성 구현 완료 |
| 12주차  | `data_handler.py`: Retrieve 구현, `main.py`: 기본 CUI 및 조회 연동 | 이흥규, 노건준 | 검색 기능 및 Rich 기본 출력 구현     |
| 13주차  | `data_handler.py`: Update/Delete 구현, `analysis.py` 구현          | 이흥규, 노건준 | CRUD 완성 및 시계열 분석 로직 개발   |
| 14주차  | 최종 기능 통합, 테스트 및 디버깅, UI 개선, 문서화                  | 팀 전체        | 버그 수정, README 최종화, 발표 준비  |

## 5. 기대 효과

- K-Startup 공고 정보에 대한 **체계적이고 효율적인 관리** 시스템 구축
- **빠르고 정확한 정보 검색**을 통한 사용자 편의성 증대
- 기관별 활동 동향 분석 등 **데이터 기반의 인사이트 도출** 가능
- Python을 활용한 **데이터 처리, 분석, 콘솔 UI 개발 역량 강화**
