"""
로깅 설정 모듈
애플리케이션 전반에서 일관된 로깅을 제공합니다.
"""

import logging
import sys
from datetime import datetime
from functools import wraps
from typing import Dict, Any, Optional
from config import config

def setup_logging() -> logging.Logger:
    """애플리케이션 로깅 설정"""
    
    # 로거 생성
    logger = logging.getLogger("kstartup_app")
    logger.setLevel(getattr(logging, config.LOG_LEVEL.upper()))
    
    # 핸들러가 이미 추가되어 있으면 스킵 (중복 방지)
    if logger.handlers:
        return logger
    
    # 포맷터 설정
    formatter = logging.Formatter(config.LOG_FORMAT)
    
    # 파일 핸들러 설정
    file_handler = logging.FileHandler(config.LOG_FILE, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    
    # 콘솔 핸들러 설정
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # 핸들러 추가
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """특정 모듈용 로거 반환"""
    return logging.getLogger(f"kstartup_app.{name}")

def log_user_action(action: str, user_id: str = "anonymous", details: Optional[Dict[str, Any]] = None):
    """사용자 액션 로깅"""
    logger = get_logger("user_actions")
    
    log_data = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "user_id": user_id,
        "details": details or {}
    }
    
    logger.info(f"User Action: {log_data}")

def log_api_call(endpoint: str, status_code: int, response_time: float, error: Optional[str] = None):
    """API 호출 로깅"""
    logger = get_logger("api_calls")
    
    log_data = {
        "endpoint": endpoint,
        "status_code": status_code,
        "response_time": f"{response_time:.2f}s",
        "error": error
    }
    
    if error:
        logger.error(f"API Call Failed: {log_data}")
    else:
        logger.info(f"API Call Success: {log_data}")

def log_data_operation(operation: str, table: str, record_id: str = None, success: bool = True, error: Optional[str] = None):
    """데이터 조작 작업 로깅"""
    logger = get_logger("data_operations")
    
    log_data = {
        "operation": operation,
        "table": table,
        "record_id": record_id,
        "success": success,
        "timestamp": datetime.now().isoformat(),
        "error": error
    }
    
    if success:
        logger.info(f"Data Operation Success: {log_data}")
    else:
        logger.error(f"Data Operation Failed: {log_data}")

def monitor_performance(func):
    """함수 실행 시간 모니터링 데코레이터"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger("performance")
        start_time = datetime.now()
        
        try:
            result = func(*args, **kwargs)
            execution_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"{func.__name__} executed successfully in {execution_time:.2f}s")
            return result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"{func.__name__} failed in {execution_time:.2f}s: {str(e)}")
            raise
    
    return wrapper

def log_chatbot_interaction(user_query: str, response: str, confidence: float = 0.0, sources: Optional[list] = None):
    """챗봇 상호작용 로깅"""
    logger = get_logger("chatbot")
    
    log_data = {
        "timestamp": datetime.now().isoformat(),
        "user_query": user_query[:100] + "..." if len(user_query) > 100 else user_query,
        "response_length": len(response),
        "confidence": confidence,
        "sources_count": len(sources) if sources else 0
    }
    
    logger.info(f"Chatbot Interaction: {log_data}")

class HealthChecker:
    """애플리케이션 건강성 체크"""
    
    @staticmethod
    def check_json_files() -> bool:
        """JSON 파일 접근성 체크"""
        import os
        required_files = [
            config.ANNOUNCEMENTS_FILE,
            config.ORGANIZATIONS_FILE,
            config.CONTEST_INFO_FILE,
            config.INDEX_FILE
        ]
        
        return all(
            os.path.exists(file_path) and os.access(file_path, os.R_OK) 
            for file_path in required_files
        )
    
    @staticmethod
    def check_memory_usage() -> Dict[str, Any]:
        """메모리 사용량 체크"""
        import psutil
        
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            "rss": memory_info.rss / 1024 / 1024,  # MB
            "vms": memory_info.vms / 1024 / 1024,  # MB
            "percent": process.memory_percent()
        }
    
    @staticmethod
    def health_check() -> Dict[str, Any]:
        """전체 건강성 체크"""
        logger = get_logger("health_check")
        
        checks = {
            "json_files": HealthChecker.check_json_files(),
            "memory": HealthChecker.check_memory_usage(),
            "timestamp": datetime.now().isoformat()
        }
        
        # API 키 체크 (존재 여부만)
        checks["api_keys"] = {
            "pinecone": bool(config.PINECONE_API_KEY),
            "openai": bool(config.OPENAI_API_KEY)
        }
        
        all_healthy = (
            checks["json_files"] and 
            checks["memory"]["percent"] < 90  # 메모리 사용률 90% 미만
        )
        
        status = "healthy" if all_healthy else "unhealthy"
        
        result = {
            "status": status,
            "checks": checks
        }
        
        if all_healthy:
            logger.info(f"Health Check Passed: {result}")
        else:
            logger.warning(f"Health Check Failed: {result}")
        
        return result

# 로깅 초기화
logger = setup_logging()

# 모듈 로드 시 기본 로깅
logger.info("Logger initialized successfully")

if __name__ == "__main__":
    # 테스트
    test_logger = get_logger("test")
    test_logger.info("로깅 모듈 테스트")
    
    # 건강성 체크 테스트
    health_result = HealthChecker.health_check()
    print(f"Health Check Result: {health_result}")
    
    # 성능 모니터링 테스트
    @monitor_performance
    def test_function():
        import time
        time.sleep(1)
        return "테스트 완료"
    
    result = test_function()
    print(f"Performance Test: {result}") 