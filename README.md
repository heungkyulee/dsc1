# K-Startup 지원사업 관리 시스템

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=flat&logo=streamlit&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=flat&logo=openai&logoColor=white)
![Pinecone](https://img.shields.io/badge/Pinecone-000000?style=flat&logo=pinecone&logoColor=white)

## 📋 프로젝트 개요

K-Startup 지원사업 관리 시스템은 한국창업진흥원(K-Startup)의 지원사업 정보를 효율적으로 관리하고 검색할 수 있는 **Streamlit 기반 웹 애플리케이션**입니다. **RAG(Retrieval-Augmented Generation)** 기술을 활용한 AI 챗봇을 통해 자연어로 지원사업 정보를 검색하고 상담받을 수 있습니다.

### ✨ 주요 특징

- 🏠 **실시간 대시보드**: 지원사업 현황을 한눈에 파악할 수 있는 인터랙티브 대시보드
- ➕ **신규 지원사업 생성**: 새로운 지원사업 정보를 쉽게 등록하고 관리
- 🔍 **고급 검색 및 필터링**: 다양한 조건으로 지원사업을 빠르게 검색
- 🤖 **AI 챗봇 상담**: RAG 기반 자연어 질의응답으로 맞춤형 지원사업 추천
- 📊 **데이터 시각화**: Plotly를 활용한 직관적인 차트와 그래프
- 🔄 **실시간 데이터 동기화**: K-Startup API와 연동하여 최신 정보 자동 업데이트

## 🚀 빠른 시작

### 1. 설치 및 설정

```bash
# 저장소 클론
git clone https://github.com/heungkyulee/dsc1
cd dsc1

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env` 파일을 생성하고 다음 정보를 입력하세요:

```env
# OpenAI API 키 (RAG 챗봇 사용시 필수)
OPENAI_API_KEY=your_openai_api_key_here

# Pinecone 설정 (벡터 데이터베이스)
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_INDEX_NAME=dsc1
PINECONE_ENVIRONMENT=us-east-1

# 선택사항: 로그 레벨 설정
LOG_LEVEL=INFO
```

### 3. 애플리케이션 실행

```bash
# Streamlit 앱 실행
streamlit run _🏠대시보드.py
```

브라우저에서 `http://localhost:8501`로 접속하면 애플리케이션을 사용할 수 있습니다.

## 🏗️ 프로젝트 구조

```
dsc1/
├── 📁 pages/                      # Streamlit 멀티페이지
│   ├── 1_➕_신규_지원사업_생성.py
│   ├── 2_🔍_지원사업_검색.py
│   └── 3_🤖_AI_챗봇.py
├── 📁 ui/                         # UI 컴포넌트
│   ├── styles.py
│   └── sidebar_info.py
├── 📁 utils/                      # 유틸리티 함수
│   ├── data_utils.py
│   └── ui_utils.py
├── 📁 dsc1/                       # 하위 모듈
├── 🏠 _🏠대시보드.py              # 메인 대시보드 페이지
├── ⚙️ config.py                   # 설정 관리
├── 📊 data_handler.py             # 데이터 CRUD 처리
├── 🕷️ crawler.py                  # K-Startup API 크롤링
├── 🤖 rag_system.py               # RAG 챗봇 시스템
├── 📈 analysis.py                 # 데이터 분석
├── 📝 logger.py                   # 로깅 시스템
├── 📄 announcements.json          # 공고 데이터
├── 🏢 organizations.json          # 기관 데이터
├── 🏆 kstartup_contest_info.json  # 지원사업 상세 정보
└── 📋 requirements.txt            # 의존성 패키지
```

## 🎯 주요 기능

### 1. 🏠 대시보드 (Print 기능)

- **실시간 통계**: 전체 지원사업 수, 활성 공고, 만료 공고, 마감 임박 공고
- **시각화 차트**: 기관별/분야별 공고 분포 파이차트
- **최신 공고**: 최근 등록된 지원사업 목록
- **빠른 작업**: 데이터 새로고침, 백업 생성 등

### 2. ➕ 신규 지원사업 생성 (Create 기능)

- **포괄적 입력 폼**: 제목, 기관, 설명, 마감일, 분야, 예산, 자격요건 등
- **실시간 검증**: 입력 데이터 유효성 검사
- **자동 ID 생성**: 고유 식별자 자동 할당
- **즉시 반영**: 생성 후 대시보드에 바로 반영

### 3. 🔍 지원사업 검색 및 필터링 (Retrieve, Update, Delete 기능)

- **다중 검색 조건**: 키워드, 기관, 분야, 상태별 검색
- **고급 필터링**: 마감일 범위, 예산 규모, 지역별 필터
- **카드 형태 표시**: 직관적인 공고 정보 카드
- **인라인 편집**: 카드에서 바로 수정/삭제 가능
- **일괄 작업**: 여러 공고 동시 관리

### 4. 🤖 AI 챗봇 상담 (RAG 기능)

- **자연어 질의**: "IT 분야 창업지원사업 추천해줘"
- **맞춤형 답변**: 사용자 조건에 맞는 지원사업 추천
- **실시간 검색**: 최신 지원사업 정보 기반 응답
- **대화 기록**: 세션 동안 대화 내용 유지
- **신뢰도 표시**: AI 응답의 정확도 수준 제공

## 🛠️ 기술 스택

### Frontend

- **Streamlit**: 웹 애플리케이션 프레임워크
- **Plotly**: 인터랙티브 데이터 시각화
- **Custom CSS**: 사용자 친화적 UI/UX

### Backend

- **Python 3.9+**: 핵심 프로그래밍 언어
- **Pandas**: 데이터 처리 및 분석
- **Requests**: HTTP API 통신
- **BeautifulSoup**: 웹 스크래핑

### AI/ML

- **OpenAI GPT**: 자연어 처리 및 생성
- **Sentence Transformers**: 텍스트 임베딩
- **Pinecone**: 벡터 데이터베이스
- **RAG**: 검색 증강 생성 기술

### Data Storage

- **JSON**: 구조화된 데이터 저장
- **File-based Database**: 로컬 데이터 관리
- **Vector Database**: 의미 검색용 임베딩 저장

## 📊 데이터 구조

### 1. 지원사업 데이터 (`announcements.json`)

```json
{
  "announcement_id": {
    "title": "지원사업 제목",
    "organization": "주관기관",
    "description": "상세 설명",
    "deadline": "2024-12-31",
    "category": "지원분야",
    "budget": "지원금액",
    "eligibility": "신청자격",
    "status": "active",
    "created_at": "2024-01-01 00:00:00",
    "source_url": "https://k-startup.go.kr/..."
  }
}
```

### 2. 기관 정보 (`organizations.json`)

```json
{
  "org_id": {
    "name": "기관명",
    "type": "기관구분",
    "contact": "연락처",
    "website": "홈페이지"
  }
}
```

### 3. 검색 인덱스 (`index.json`)

```json
{
  "title_keywords": {
    "창업": ["ann_001", "ann_002"],
    "기술": ["ann_003", "ann_004"]
  },
  "organization_name": {
    "중소벤처기업부": ["ann_001", "ann_003"]
  }
}
```

## 🔧 고급 설정

### RAG 시스템 설정

```python
# config.py에서 설정 가능한 RAG 매개변수
EMBEDDING_DIMENSION = 512
SIMILARITY_THRESHOLD = 0.7
MAX_CHAT_HISTORY = 10
CONTEXT_WINDOW_SIZE = 5
```

### 로깅 설정

```python
# 로그 레벨 설정
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
LOG_FILE = "kstartup_app.log"
```

### API 설정

```python
# K-Startup API 설정
API_TIMEOUT = 30
MAX_RETRIES = 3
RATE_LIMIT_DELAY = 1.0
```

## 🤝 사용법 예시

### 1. 대시보드 사용

1. 메인 페이지에서 전체 현황 확인
2. 차트를 통해 기관별/분야별 분포 분석
3. "데이터 새로고침" 버튼으로 최신 정보 업데이트

### 2. 지원사업 검색

1. 🔍 검색 페이지로 이동
2. 검색어 입력 (예: "창업", "IT", "바이오")
3. 필터 조건 설정 (기관, 마감일, 예산 등)
4. 결과 카드에서 상세 정보 확인

### 3. AI 챗봇 활용

1. 🤖 AI 챗봇 페이지로 이동
2. 자연어로 질문 입력:
   - "초기창업자를 위한 지원사업을 찾아줘"
   - "IT 분야에서 1억원 이상 지원하는 사업이 있나요?"
   - "이번 달 마감인 공고들을 알려주세요"
3. AI의 맞춤형 답변 및 추천 확인

## 🚨 문제 해결

### 일반적인 문제들

**Q: RAG 챗봇이 작동하지 않아요**
A: OpenAI API 키와 Pinecone API 키가 올바르게 설정되었는지 확인하세요.

**Q: 데이터가 로드되지 않아요**
A: JSON 파일들이 손상되었을 수 있습니다. 백업 파일을 복원하거나 데이터를 다시 수집하세요.

**Q: 검색 결과가 나오지 않아요**
A: 인덱스 파일이 최신인지 확인하고, 대시보드에서 "데이터 새로고침"을 실행하세요.

**Q: 애플리케이션이 느려요**
A: 캐시를 초기화하거나 브라우저를 새로고침하세요. 데이터 양이 많을 경우 필터링을 사용하세요.

## 📈 향후 계획

- [ ] **다국어 지원**: 영어, 중국어 인터페이스 추가
- [ ] **모바일 최적화**: 반응형 디자인 개선
- [ ] **알림 시스템**: 마감 임박 공고 이메일 알림
- [ ] **API 서비스**: RESTful API 제공
- [ ] **데이터베이스 연동**: PostgreSQL, MongoDB 지원
- [ ] **협업 기능**: 다중 사용자 권한 관리

## 🙋‍♂️ 기여하기

1. 이 저장소를 포크하세요
2. 새로운 기능 브랜치를 만드세요 (`git checkout -b feature/새기능`)
3. 변경사항을 커밋하세요 (`git commit -am 'Add 새기능'`)
4. 브랜치에 푸시하세요 (`git push origin feature/새기능`)
5. Pull Request를 생성하세요

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 제공됩니다. 자세한 내용은 `LICENSE` 파일을 참조하세요.

## 📞 지원 및 문의

- **이슈 트래커**: GitHub Issues
- **문서**: 프로젝트 Wiki
- **이메일**: [프로젝트 담당자 이메일]

---

**Made with ❤️ by K-Startup Management Team**
