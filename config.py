"""
K-Startup 데이터 관리 프로그램 설정 파일
환경 변수 및 애플리케이션 설정을 관리합니다.
"""

import os
from dotenv import load_dotenv
from typing import Optional

# .env 파일 로드
load_dotenv()

class Config:
    """애플리케이션 설정 클래스"""
    
    # API 키 설정 (환경변수 우선, 없으면 직접 설정값 사용)
    PINECONE_API_KEY: Optional[str] = os.getenv("PINECONE_API_KEY") or "pcsk_33NTQh_RpshxHr1AXWeTxKMTpc52PxEVdBomgEQBDEpADVjzdZCFx9SXoiTyDbrEee21PZ"
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    # 벡터 데이터베이스 설정
    PINECONE_ENVIRONMENT: str = os.getenv("PINECONE_ENVIRONMENT", "us-east-1")
    PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "dsc1")
    EMBEDDING_DIMENSION: int = int(os.getenv("EMBEDDING_DIMENSION", "512"))
    
    # API 설정
    K_STARTUP_BASE_URL: str = os.getenv("K_STARTUP_BASE_URL", "https://www.k-startup.go.kr")
    API_TIMEOUT: int = int(os.getenv("API_TIMEOUT", "30"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    RATE_LIMIT_DELAY: float = float(os.getenv("RATE_LIMIT_DELAY", "1.0"))
    
    # 로깅 설정
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "kstartup_app.log")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # 데이터 파일 경로
    ANNOUNCEMENTS_FILE: str = os.getenv("ANNOUNCEMENTS_FILE", "announcements.json")
    ORGANIZATIONS_FILE: str = os.getenv("ORGANIZATIONS_FILE", "organizations.json")
    CONTEST_INFO_FILE: str = os.getenv("CONTEST_INFO_FILE", "kstartup_contest_info.json")
    INDEX_FILE: str = os.getenv("INDEX_FILE", "index.json")
    RAW_DATA_FILE: str = os.getenv("RAW_DATA_FILE", "raw_data.json")
    
    # 애플리케이션 설정
    APP_TITLE: str = os.getenv("APP_TITLE", "K-Startup 지원사업 관리")
    MAX_DISPLAY_ITEMS: int = int(os.getenv("MAX_DISPLAY_ITEMS", "50"))
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "3600"))
    
    # Streamlit 설정
    STREAMLIT_PAGE_TITLE: str = os.getenv("STREAMLIT_PAGE_TITLE", "K-Startup 지원사업 관리")
    STREAMLIT_LAYOUT: str = os.getenv("STREAMLIT_LAYOUT", "wide")
    
    # RAG 챗봇 설정
    MAX_CHAT_HISTORY: int = int(os.getenv("MAX_CHAT_HISTORY", "10"))
    CONTEXT_WINDOW_SIZE: int = int(os.getenv("CONTEXT_WINDOW_SIZE", "5"))
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.7"))
    
    @classmethod
    def validate_config(cls) -> bool:
        """설정 유효성 검증"""
        errors = []
        
        # 필수 API 키 확인 (RAG 기능 사용 시)
        if not cls.PINECONE_API_KEY:
            errors.append("PINECONE_API_KEY가 설정되지 않았습니다.")
        
        if not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY가 설정되지 않았습니다.")
            
        # 파일 경로 확인
        required_files = [
            cls.ANNOUNCEMENTS_FILE,
            cls.ORGANIZATIONS_FILE,
            cls.CONTEST_INFO_FILE,
            cls.INDEX_FILE
        ]
        
        for file_path in required_files:
            if not os.path.exists(file_path):
                print(f"경고: {file_path} 파일이 존재하지 않습니다. 초기 실행 시 생성됩니다.")
        
        if errors:
            for error in errors:
                print(f"설정 오류: {error}")
            return False
        
        return True
    
    @classmethod
    def get_api_headers(cls) -> dict:
        """API 요청용 헤더 반환"""
        return {
            "User-Agent": f"{cls.APP_TITLE}/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

# 설정 인스턴스 생성
config = Config()

# 설정 검증 (선택사항)
if __name__ == "__main__":
    if config.validate_config():
        print("✅ 모든 설정이 올바르게 구성되었습니다.")
    else:
        print("❌ 설정에 문제가 있습니다. .env 파일을 확인해주세요.") 