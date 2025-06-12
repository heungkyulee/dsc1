# K-Startup 지원사업 관리 시스템 아키텍처

## 📋 개요

K-Startup 지원사업 관리 시스템은 한국창업진흥원의 지원사업 정보를 효율적으로 관리하고 사용자에게 제공하는 웹 기반 플랫폼입니다. Streamlit 기반의 웹 애플리케이션을 제공하며, RAG(Retrieval-Augmented Generation) 기술을 활용한 AI 챗봇을 통해 지능형 질의응답 서비스를 제공합니다.

### 🎯 주요 기능

- 📊 **실시간 대시보드**: 지원사업 통계 및 시각화
- ➕ **CRUD 기능**: 지원사업 생성, 조회, 수정, 삭제
- 🔍 **고급 검색**: 키워드 및 필터 기반 검색
- 🤖 **AI 챗봇**: RAG 기반 지능형 상담 서비스
- 📈 **데이터 분석**: 기관별 공고 빈도 분석

---

## 🏗️ 전체 시스템 아키텍처

```mermaid
graph TD
    subgraph "사용자 인터페이스 계층"
        A[🏠 Streamlit 대시보드]
        B[➕ 신규 지원사업 생성]
        C[🔍 검색 및 필터링]
        D[🤖 AI 챗봇]
    end

    subgraph "핵심 비즈니스 로직 계층"
        E[📊 Data Handler<br/>CRUD 관리]
        F[🕷️ Crawler<br/>API 수집]
        G[🤖 RAG System<br/>벡터 검색 & 생성]
        H[📈 Analysis<br/>데이터 분석]
    end

    subgraph "유틸리티 계층"
        I[⚙️ Config<br/>설정 관리]
        J[📋 Logger<br/>로깅 시스템]
        K[🎨 UI Utils<br/>화면 유틸리티]
        L[💾 Data Utils<br/>데이터 유틸리티]
    end

    subgraph "데이터 저장소"
        M[(📄 announcements.json<br/>공고 정보)]
        N[(🏢 organizations.json<br/>기관 정보)]
        O[(📋 kstartup_contest_info.json<br/>원본 데이터)]
    end

    subgraph "외부 서비스"
        P[🌐 K-Startup API<br/>데이터 소스]
        Q[🔗 Pinecone<br/>벡터 DB]
        R[🧠 OpenAI<br/>LLM 서비스]
    end

    A --> E
    A --> H
    B --> E
    C --> E
    D --> G

    E --> M
    E --> N
    F --> O
    F --> P
    G --> Q
    G --> R

    E --> I
    E --> J
    A --> K
    E --> L

    style A fill:#e1f5fe
    style E fill:#f3e5f5
    style G fill:#fff3e0
    style P fill:#e8f5e8
    style Q fill:#fff9c4
    style R fill:#ffebee
```

---

## 🔄 데이터 흐름도

```mermaid
flowchart TD
    A[📊 K-Startup API] --> B[🕷️ Crawler 모듈]
    B --> C[📋 kstartup_contest_info.json<br/>원본 데이터]

    C --> D[📊 Data Handler<br/>데이터 처리]
    D --> E[🏢 organizations.json<br/>기관 정보 분리]
    D --> F[📄 announcements.json<br/>공고 정보 정제]

    F --> G[🤖 RAG System<br/>벡터 임베딩]
    G --> H[🔗 Pinecone<br/>벡터 저장소]

    E --> I[📊 Streamlit Dashboard<br/>대시보드 표시]
    F --> I

    F --> J[🔍 검색 & 필터링<br/>페이지]

    F --> K[➕ 신규 생성<br/>페이지]

    H --> L[🤖 AI 챗봇<br/>질의응답]
    M[🧠 OpenAI API] --> L

    I --> N[👤 사용자]
    J --> N
    K --> N
    L --> N

    style A fill:#e8f5e8
    style B fill:#f3e5f5
    style D fill:#f3e5f5
    style G fill:#fff3e0
    style H fill:#fff9c4
    style M fill:#ffebee
    style N fill:#e3f2fd
```

---

## 🧩 컴포넌트 구조도

```mermaid
graph LR
    subgraph "Frontend Layer"
        A[🏠 메인 대시보드<br/>_🏠대시보드.py]
    end

    subgraph "Pages Layer"
        B[➕ 신규 생성<br/>1_신규_지원사업_생성.py]
        C[🔍 검색 필터링<br/>2_지원사업_검색_및_필터링.py]
        D[🤖 챗봇<br/>3_AI_챗봇.py]
    end

    subgraph "UI Components"
        E[🎨 Styles<br/>ui/styles.py]
        F[📋 Sidebar Info<br/>ui/sidebar_info.py]
    end

    subgraph "Business Logic"
        G[📊 Data Handler<br/>data_handler.py]
        H[🕷️ Crawler<br/>crawler.py]
        I[🤖 RAG System<br/>rag_system.py]
        J[📈 Analysis<br/>analysis.py]
    end

    subgraph "Utilities"
        K[⚙️ Config<br/>config.py]
        L[📋 Logger<br/>logger.py]
        M[🔧 Data Utils<br/>utils/data_utils.py]
        N[🎨 UI Utils<br/>utils/ui_utils.py]
    end

    A --> B
    A --> C
    A --> D
    A --> E
    A --> F

    B --> G
    C --> G
    D --> I

    G --> K
    G --> L
    H --> K
    I --> K
    J --> K

    A --> M
    A --> N

    style A fill:#e1f5fe
    style G fill:#f3e5f5
    style I fill:#fff3e0
    style K fill:#e8f5e8
```

---

## 🗄️ 데이터베이스 스키마

```mermaid
erDiagram
    ANNOUNCEMENT {
        string pbancSn PK "공고일련번호"
        string title "지원사업 제목"
        string support_field "지원분야"
        string target_age "대상연령"
        string org_id FK "기관 ID"
        string org_name_ref "기관명 참조"
        string contact "연락처"
        string region "지역"
        string application_period "접수기간"
        string deadline "마감일"
        string startup_experience "창업업력"
        string target_audience "대상"
        string department "담당부서"
        string announcement_number "공고번호"
        string description "공고설명"
        string announcement_date "공고일자"
        array application_method "신청방법"
        array submission_documents "제출서류"
        array selection_procedure "선정절차"
        array support_content "지원내용"
        array inquiry "문의처"
        array attachments "첨부파일"
    }

    ORGANIZATION {
        string org_id PK "기관 ID"
        string name "기관명"
        string type "기관구분"
    }

    RAW_DATA {
        string pbancSn PK "공고일련번호"
        string title "원본 제목"
        string org_name "기관명"
        string content "원본 내용"
        array api_fields "API 필드들"
    }

    VECTOR_DATA {
        string vector_id PK "벡터 ID"
        string pbancSn FK "공고일련번호"
        array embedding "임베딩 벡터"
        json metadata "메타데이터"
    }

    ANNOUNCEMENT ||--|| ORGANIZATION : "belongs_to"
    RAW_DATA ||--|| ANNOUNCEMENT : "processed_to"
    ANNOUNCEMENT ||--o| VECTOR_DATA : "embedded_as"
```

---

## 👤 사용자 플로우

```mermaid
flowchart TD
    A[👤 사용자 웹 접속] --> B[🏠 Streamlit 대시보드]

    B --> C{페이지 선택}
    C -->|대시보드| D[📊 통계 및 차트 보기]
    C -->|신규 생성| E[➕ 지원사업 생성 폼]
    C -->|검색/필터링| F[🔍 공고 검색 및 관리]
    C -->|AI 챗봇| G[🤖 질의응답 채팅]

    E --> H[💾 데이터 저장]
    F --> I{작업 선택}
    I -->|조회| J[📖 상세 정보 표시]
    I -->|수정| K[✏️ 정보 업데이트]
    I -->|삭제| L[🗑️ 데이터 삭제]

    G --> M[🧠 RAG 시스템 처리]
    M --> N[🔍 벡터 검색]
    N --> O[📝 답변 생성]

    H --> P[(💾 JSON 파일)]
    K --> P
    L --> P

    O --> Q[💬 사용자에게 응답]
    D --> R[📊 차트 표시]
    J --> S[📄 정보 표시]

    style A fill:#e3f2fd
    style B fill:#e1f5fe
    style G fill:#fff3e0
    style P fill:#f3e5f5
    style M fill:#fff9c4
```

---

## ⚡ 시퀀스 다이어그램

```mermaid
sequenceDiagram
    participant U as 👤 사용자
    participant S as 🏠 Streamlit 앱
    participant DH as 📊 Data Handler
    participant C as 🕷️ Crawler
    participant API as 🌐 K-Startup API
    participant R as 🤖 RAG System
    participant P as 🔗 Pinecone
    participant O as 🧠 OpenAI
    participant DB as 💾 JSON 파일들

    Note over U,DB: 데이터 수집 및 처리 플로우

    U->>C: 데이터 수집 요청
    C->>API: API 호출
    API-->>C: 원본 데이터 반환
    C->>DB: kstartup_contest_info.json 저장

    U->>DH: 데이터 처리 요청
    DH->>DB: 원본 데이터 로드
    DH->>DH: 데이터 정제 및 분리
    DH->>DB: announcements.json 저장
    DH->>DB: organizations.json 저장

    Note over U,DB: RAG 시스템 초기화

    R->>DB: 공고 데이터 로드
    R->>R: 텍스트 임베딩 생성
    R->>P: 벡터 데이터 저장

    Note over U,DB: 사용자 상호작용

    U->>S: 웹 앱 접속
    S->>DH: 대시보드 데이터 요청
    DH->>DB: 데이터 조회
    DB-->>DH: 데이터 반환
    DH-->>S: 처리된 데이터
    S-->>U: 대시보드 표시

    U->>S: 챗봇 질문
    S->>R: 질의 처리 요청
    R->>R: 질문 임베딩 생성
    R->>P: 유사 벡터 검색
    P-->>R: 관련 공고 반환
    R->>O: 답변 생성 요청
    O-->>R: LLM 응답
    R-->>S: 최종 답변
    S-->>U: 챗봇 응답 표시
```

---

## 📁 파일 구조

```
dsc1/
├── 📱 _🏠대시보드.py              # Streamlit 메인 앱
├── 📊 data_handler.py              # 데이터 CRUD 관리
├── 🕷️ crawler.py                   # K-Startup API 크롤러
├── 🤖 rag_system.py                # RAG 챗봇 시스템
├── 📈 analysis.py                  # 데이터 분석 모듈
├── ⚙️ config.py                    # 설정 관리
├── 📋 logger.py                    # 로깅 시스템
│
├── 📄 데이터 파일/
│   ├── announcements.json         # 공고 정보
│   ├── organizations.json         # 기관 정보
│   └── kstartup_contest_info.json # 원본 데이터
│
├── 📱 pages/                       # Streamlit 페이지
│   ├── 1_➕_신규_지원사업_생성.py
│   ├── 2_🔍_지원사업_검색_및_필터링.py
│   └── 3_🤖_AI_챗봇.py
│
├── 🎨 ui/                          # UI 컴포넌트
│   ├── styles.py                  # 스타일 관리
│   └── sidebar_info.py            # 사이드바 정보
│
├── 🔧 utils/                       # 유틸리티
│   ├── data_utils.py              # 데이터 유틸리티
│   └── ui_utils.py                # UI 유틸리티
│
└── 📋 requirements.txt             # 의존성 관리
```

---

## 🔧 기술 스택

### 🖥️ Frontend

- **Streamlit**: 웹 애플리케이션 프레임워크
- **Plotly**: 데이터 시각화
- **Rich**: 콘솔 출력 개선

### 🔗 Backend

- **Python 3.11+**: 메인 프로그래밍 언어
- **FastAPI**: REST API (필요시)
- **Pandas**: 데이터 처리
- **NumPy**: 수치 연산

### 🤖 AI/ML

- **OpenAI GPT**: 대화형 AI
- **Pinecone**: 벡터 데이터베이스
- **Sentence Transformers**: 텍스트 임베딩
- **LangChain**: LLM 체인 관리

### 💾 데이터

- **JSON**: 로컬 데이터 저장
- **Requests**: HTTP API 통신
- **Beautiful Soup**: 웹 스크래핑 (필요시)

### 🔧 개발 도구

- **Git**: 버전 관리
- **Poetry/pip**: 의존성 관리
- **Black**: 코드 포매팅
- **Pytest**: 테스트 프레임워크

---

## 🔑 핵심 설계 원칙

### 1. 📐 계층형 아키텍처

- **프레젠테이션 계층**: Streamlit 웹 UI
- **비즈니스 로직 계층**: 데이터 처리 및 분석
- **데이터 접근 계층**: JSON 파일 관리
- **외부 서비스 계층**: API 통신 및 벡터 DB

### 2. 🔒 단일 책임 원칙

- 각 모듈은 명확한 단일 책임을 가짐
- 데이터 처리, UI 렌더링, API 통신 분리
- 재사용 가능한 컴포넌트 설계

### 3. 🔄 데이터 흐름 관리

- 단방향 데이터 흐름
- 중앙집중식 상태 관리
- 캐싱을 통한 성능 최적화

### 4. 🛡️ 오류 처리 및 로깅

- 체계적인 예외 처리
- 구조화된 로깅 시스템
- 사용자 친화적 오류 메시지

### 5. 🔌 확장성 고려

- 모듈형 설계로 기능 추가 용이
- 플러그인 아키텍처 준비
- 마이크로서비스 전환 가능성

---

## 🚀 배포 및 운영

### 📦 배포 방식

- **로컬 개발**: `streamlit run _🏠대시보드.py`
- **Docker 컨테이너**: 컨테이너화 준비
- **클라우드 배포**: Streamlit Cloud, AWS, GCP

### 📊 모니터링

- 애플리케이션 로그 모니터링
- API 호출 성능 추적
- 사용자 행동 분석

### 🔐 보안

- API 키 환경변수 관리
- 데이터 입력 검증 및 sanitization
- HTTPS 통신 강제

---

## 🛠️ 개발 및 유지보수 가이드

### 📝 코드 품질

- PEP 8 스타일 가이드 준수
- 타입 힌팅 적극 활용
- 단위 테스트 및 통합 테스트

### 📖 문서화

- 모든 함수/클래스 Docstring 작성
- API 문서 자동 생성
- 사용자 매뉴얼 유지

### 🔄 CI/CD

- GitHub Actions 워크플로우
- 자동 테스트 실행
- 코드 품질 검사

이 아키텍처 문서는 시스템의 전체적인 구조와 설계 철학을 제공하며, 개발팀의 효율적인 협업과 시스템 유지보수를 지원합니다.
