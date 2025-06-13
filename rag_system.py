"""
RAG (Retrieval-Augmented Generation) 시스템
Pinecone 벡터 데이터베이스와 OpenAI를 활용한 지능형 질의응답 시스템
"""

import json
import hashlib
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta
import asyncio

from config import config
from logger import get_logger, log_chatbot_interaction, monitor_performance

try:
    import pinecone
    from pinecone import Pinecone, ServerlessSpec
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    print("경고: pinecone-client가 설치되지 않았습니다. RAG 기능이 제한됩니다.")

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("경고: sentence-transformers가 설치되지 않았습니다. 임베딩 기능이 제한됩니다.")

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("경고: openai가 설치되지 않았습니다. 텍스트 생성 기능이 제한됩니다.")

logger = get_logger(__name__)

class EmbeddingManager:
    """텍스트 임베딩 생성 및 관리"""
    
    def __init__(self):
        self.model = None
        self.model_name = "distiluse-base-multilingual-cased"
        self.embedding_dimension = None
        self._initialize_model()
    
    def _initialize_model(self):
        """임베딩 모델 초기화"""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            logger.warning("sentence-transformers를 사용할 수 없습니다.")
            return
        
        try:
            self.model = SentenceTransformer(self.model_name)
            
            # 실제 임베딩 차원 확인
            test_embedding = self.model.encode(["test"])
            self.embedding_dimension = len(test_embedding[0])
            
            logger.info(f"임베딩 모델 '{self.model_name}' 로드 완료")
            logger.info(f"임베딩 차원: {self.embedding_dimension}")
            
        except Exception as e:
            logger.error(f"임베딩 모델 로드 실패: {e}")
    
    def get_embedding_dimension(self) -> int:
        """임베딩 차원 반환"""
        return self.embedding_dimension or 512  # 기본값 512
    
    @monitor_performance
    def create_embedding(self, text: str) -> List[float]:
        """텍스트를 벡터로 변환"""
        if not self.model:
            raise ValueError("임베딩 모델이 초기화되지 않았습니다.")
        
        try:
            # 텍스트 전처리
            cleaned_text = self._preprocess_text(text)
            # 임베딩 생성
            embedding = self.model.encode(cleaned_text).tolist()
            return embedding
        except Exception as e:
            logger.error(f"임베딩 생성 실패: {e}")
            raise
    
    def create_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """여러 텍스트를 한 번에 임베딩으로 변환"""
        if not self.model:
            raise ValueError("임베딩 모델이 초기화되지 않았습니다.")
        
        try:
            cleaned_texts = [self._preprocess_text(text) for text in texts]
            embeddings = self.model.encode(cleaned_texts).tolist()
            return embeddings
        except Exception as e:
            logger.error(f"배치 임베딩 생성 실패: {e}")
            raise
    
    def _preprocess_text(self, text: str) -> str:
        """임베딩을 위한 텍스트 전처리"""
        if not text:
            return ""
        
        # 기본적인 정제
        text = text.strip()
        # 긴 텍스트 자르기 (모델 제한 고려)
        max_length = 512
        if len(text) > max_length:
            text = text[:max_length]
        
        return text

class PineconeManager:
    """Pinecone 벡터 데이터베이스 관리"""
    
    def __init__(self, embedding_dimension: Optional[int] = None):
        self.client = None
        self.index = None
        self.embedding_dimension = embedding_dimension
        self._initialize_pinecone()
    
    def _initialize_pinecone(self):
        """Pinecone 초기화"""
        if not PINECONE_AVAILABLE:
            logger.warning("Pinecone을 사용할 수 없습니다.")
            return
        
        if not config.PINECONE_API_KEY:
            logger.warning("PINECONE_API_KEY가 설정되지 않았습니다.")
            return
        
        try:
            logger.info(f"Pinecone 초기화 시작...")
            logger.info(f"API 키: {config.PINECONE_API_KEY[:20]}...")
            logger.info(f"인덱스명: {config.PINECONE_INDEX_NAME}")
            logger.info(f"임베딩 차원: {self.embedding_dimension}")
            
            # Pinecone 클라이언트 초기화
            self.client = Pinecone(api_key=config.PINECONE_API_KEY)
            logger.info("Pinecone 클라이언트 초기화 완료")
            
            # 인덱스 존재 확인 및 생성
            self._ensure_index_exists()
            
            # 인덱스 연결
            self.index = self.client.Index(config.PINECONE_INDEX_NAME)
            logger.info(f"Pinecone 인덱스 '{config.PINECONE_INDEX_NAME}' 연결 완료")
            
            # 연결 테스트
            stats = self.index.describe_index_stats()
            logger.info(f"인덱스 통계: {stats}")
            
        except Exception as e:
            logger.error(f"Pinecone 초기화 실패: {e}")
            logger.error(f"오류 상세: {type(e).__name__}: {str(e)}")
            raise
    
    def _ensure_index_exists(self):
        """인덱스가 존재하지 않으면 생성"""
        try:
            # 기존 인덱스 목록 확인
            existing_indexes = [index_info["name"] for index_info in self.client.list_indexes()]
            
            if config.PINECONE_INDEX_NAME not in existing_indexes:
                logger.info(f"인덱스 '{config.PINECONE_INDEX_NAME}' 생성 중...")
                
                # 실제 임베딩 차원 사용
                dimension = self.embedding_dimension or config.EMBEDDING_DIMENSION
                
                self.client.create_index(
                    name=config.PINECONE_INDEX_NAME,
                    dimension=dimension,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region="us-east-1"
                    )
                )
                logger.info(f"인덱스 '{config.PINECONE_INDEX_NAME}' 생성 완료 (차원: {dimension})")
            else:
                # 기존 인덱스의 차원 확인
                index_stats = self.client.describe_index(config.PINECONE_INDEX_NAME)
                existing_dimension = index_stats.dimension
                expected_dimension = self.embedding_dimension or config.EMBEDDING_DIMENSION
                
                if existing_dimension != expected_dimension:
                    logger.warning(f"기존 인덱스 차원({existing_dimension})과 임베딩 모델 차원({expected_dimension})이 불일치합니다.")
                    logger.warning("기존 인덱스를 삭제하고 새로 생성합니다...")
                    
                    # 기존 인덱스 삭제
                    self.client.delete_index(config.PINECONE_INDEX_NAME)
                    
                    # 새 인덱스 생성
                    self.client.create_index(
                        name=config.PINECONE_INDEX_NAME,
                        dimension=expected_dimension,
                        metric="cosine",
                        spec=ServerlessSpec(
                            cloud="aws",
                            region="us-east-1"
                        )
                    )
                    logger.info(f"새 인덱스 '{config.PINECONE_INDEX_NAME}' 생성 완료 (차원: {expected_dimension})")
                else:
                    logger.info(f"인덱스 '{config.PINECONE_INDEX_NAME}' 이미 존재 (차원: {existing_dimension})")
                
        except Exception as e:
            logger.error(f"인덱스 확인/생성 실패: {e}")
            raise
    
    @monitor_performance
    def upsert_vectors(self, vectors: List[Dict[str, Any]]) -> bool:
        """벡터 데이터 업서트"""
        if not self.index:
            logger.error("Pinecone 인덱스가 초기화되지 않았습니다.")
            return False
        
        try:
            # 배치 크기로 분할하여 업서트
            batch_size = 100
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                self.index.upsert(vectors=batch)
            
            logger.info(f"{len(vectors)}개 벡터 업서트 완료")
            return True
            
        except Exception as e:
            logger.error(f"벡터 업서트 실패: {e}")
            return False
    
    @monitor_performance
    def search_similar(self, query_vector: List[float], top_k: int = 30, filter_dict: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """유사한 벡터 검색 (신청 가능한 지원사업 우선)"""
        if not self.index:
            logger.error("Pinecone 인덱스가 초기화되지 않았습니다.")
            return []
        
        try:
            # 신청 가능한 지원사업을 우선적으로 찾기 위해 더 많은 결과 가져오기
            extended_top_k = min(top_k * 5, 100)  # 최대 100개까지 확장
            
            query_response = self.index.query(
                vector=query_vector,
                top_k=extended_top_k,
                include_metadata=True,
                filter=filter_dict
            )
            
            results = []
            current_year = datetime.now().year
            
            for match in query_response.matches:
                metadata = match.metadata
                
                # 신청 기간 분석
                application_period = metadata.get('application_period', '')
                deadline_status = self._analyze_deadline_status(application_period)
                is_current_year = self._is_current_year_announcement(application_period, current_year)
                
                result = {
                    "id": match.id,
                    "score": match.score,
                    "metadata": metadata,
                    "is_current_year": is_current_year,
                    "deadline_status": deadline_status,
                    "is_applicable": not deadline_status["is_expired"]  # 신청 가능 여부
                }
                
                results.append(result)
            
            # 신청 가능한 지원사업을 우선적으로 정렬
            # 1순위: 신청 가능 여부 (마감되지 않음)
            # 2순위: 현재 연도 여부
            # 3순위: 마감 임박도 (마감이 가까울수록 우선)
            # 4순위: 유사도 점수
            def sort_key(x):
                deadline_status = x["deadline_status"]
                urgency_score = 0
                
                if deadline_status["status"] == "today":
                    urgency_score = 1000  # 오늘 마감 - 최우선
                elif deadline_status["status"] == "urgent":
                    urgency_score = 500   # 3일 이내 마감
                elif deadline_status["days_remaining"] is not None and deadline_status["days_remaining"] > 0:
                    # 마감일이 가까울수록 높은 점수 (최대 30일 기준)
                    urgency_score = max(0, 100 - deadline_status["days_remaining"])
                
                return (
                    not x["is_applicable"],      # 신청 불가능한 것은 뒤로
                    not x["is_current_year"],    # 현재 연도가 아닌 것은 뒤로
                    -urgency_score,              # 긴급도가 높은 것을 앞으로
                    -x["score"]                  # 유사도가 높은 것을 앞으로
                )
            
            results.sort(key=sort_key)
            
            # 요청된 개수만큼 반환
            final_results = results[:top_k]
            
            # 통계 정보 로깅
            applicable_count = sum(1 for r in final_results if r["is_applicable"])
            current_year_count = sum(1 for r in final_results if r["is_current_year"])
            urgent_count = sum(1 for r in final_results if r["deadline_status"]["is_urgent"])
            
            logger.info(f"유사도 검색 완료: {len(final_results)}개 결과 "
                       f"(신청가능: {applicable_count}개, 현재연도: {current_year_count}개, 긴급: {urgent_count}개)")
            
            return final_results
            
        except Exception as e:
            logger.error(f"유사도 검색 실패: {e}")
            return []
    
    def _analyze_deadline_status(self, application_period: str) -> Dict[str, Any]:
        """지원사업 마감일 분석 (YYYYMMDD 형식 포함)"""
        try:
            kst = timezone(timedelta(hours=9))
            now = datetime.now(kst)
            
            # 접수기간에서 마감일 추출 시도
            import re
            
            deadline_info = {
                "status": "unknown",
                "days_remaining": None,
                "deadline_date": None,
                "is_expired": False,
                "is_urgent": False
            }
            
            if not application_period:
                return deadline_info
            
            # YYYYMMDD ~ YYYYMMDD 형식 우선 처리
            yyyymmdd_pattern = r'(\d{8})\s*~\s*(\d{8})'
            yyyymmdd_match = re.search(yyyymmdd_pattern, application_period)
            
            if yyyymmdd_match:
                try:
                    end_date_str = yyyymmdd_match.group(2)  # 마감일
                    year = int(end_date_str[:4])
                    month = int(end_date_str[4:6])
                    day = int(end_date_str[6:8])
                    
                    deadline = datetime(year, month, day, 23, 59, 59, tzinfo=kst)
                    days_diff = (deadline - now).days
                    
                    deadline_info.update({
                        "deadline_date": deadline.strftime("%Y-%m-%d"),
                        "days_remaining": days_diff,
                        "is_expired": days_diff < 0,
                        "is_urgent": 0 <= days_diff <= 3
                    })
                    
                    if days_diff < 0:
                        deadline_info["status"] = "expired"
                    elif days_diff == 0:
                        deadline_info["status"] = "today"
                    elif days_diff <= 3:
                        deadline_info["status"] = "urgent"
                    elif days_diff <= 7:
                        deadline_info["status"] = "soon"
                    else:
                        deadline_info["status"] = "active"
                        
                    return deadline_info
                    
                except ValueError:
                    pass
            
            # YYYY.MM.DD 형식 처리
            dot_pattern = r'(\d{4})\.(\d{1,2})\.(\d{1,2})\s*~\s*(\d{4})\.(\d{1,2})\.(\d{1,2})'
            dot_match = re.search(dot_pattern, application_period)
            
            if dot_match:
                try:
                    year = int(dot_match.group(4))
                    month = int(dot_match.group(5))
                    day = int(dot_match.group(6))
                    
                    deadline = datetime(year, month, day, 23, 59, 59, tzinfo=kst)
                    days_diff = (deadline - now).days
                    
                    deadline_info.update({
                        "deadline_date": deadline.strftime("%Y-%m-%d"),
                        "days_remaining": days_diff,
                        "is_expired": days_diff < 0,
                        "is_urgent": 0 <= days_diff <= 3
                    })
                    
                    if days_diff < 0:
                        deadline_info["status"] = "expired"
                    elif days_diff == 0:
                        deadline_info["status"] = "today"
                    elif days_diff <= 3:
                        deadline_info["status"] = "urgent"
                    elif days_diff <= 7:
                        deadline_info["status"] = "soon"
                    else:
                        deadline_info["status"] = "active"
                        
                    return deadline_info
                    
                except ValueError:
                    pass
            
            # 기타 형식들도 시도할 수 있지만, 기본값 반환
            return deadline_info
            
        except Exception as e:
            logger.error(f"마감일 분석 실패: {e}")
            return {
                "status": "unknown",
                "days_remaining": None,
                "deadline_date": None,
                "is_expired": False,
                "is_urgent": False
            }
    
    def _is_current_year_announcement(self, application_period: str, current_year: int) -> bool:
        """접수기간에서 현재 연도 지원사업인지 확인"""
        if not application_period:
            return False
        
        try:
            import re
            # YYYYMMDD 형식에서 연도 추출
            year_matches = re.findall(r'(\d{4})', application_period)
            if year_matches:
                # 가장 최근 연도 확인
                years = [int(year) for year in year_matches]
                latest_year = max(years)
                return latest_year >= current_year
            return False
        except Exception:
            return False
    
    def delete_vectors(self, ids: List[str]) -> bool:
        """특정 벡터들 삭제"""
        if not self.index:
            logger.error("Pinecone 인덱스가 초기화되지 않았습니다.")
            return False
        
        try:
            self.index.delete(ids=ids)
            logger.info(f"{len(ids)}개 벡터 삭제 완료")
            return True
        except Exception as e:
            logger.error(f"벡터 삭제 실패: {e}")
            return False
    
    def get_index_stats(self) -> Dict[str, Any]:
        """인덱스 통계 정보 반환"""
        if not self.index:
            return {}
        
        try:
            stats = self.index.describe_index_stats()
            return {
                "total_vector_count": stats.total_vector_count,
                "dimension": stats.dimension,
                "index_fullness": stats.index_fullness
            }
        except Exception as e:
            logger.error(f"인덱스 통계 조회 실패: {e}")
            return {}

class RAGChatbot:
    """RAG 기반 챗봇 시스템"""
    
    def __init__(self):
        self.embedding_manager = EmbeddingManager()
        
        # 임베딩 차원을 가져와서 PineconeManager에 전달
        embedding_dimension = self.embedding_manager.get_embedding_dimension()
        self.pinecone_manager = PineconeManager(embedding_dimension=embedding_dimension)
        
        self.openai_client = None
        self.chat_history = []
        self.conversation_memory = []  # 대화 컨텍스트를 위한 메모리
        self.max_memory_turns = 5  # 최대 5턴의 대화 기억
        self._initialize_openai()
    
    def _get_current_time_info(self) -> Dict[str, str]:
        """현재 한국 시간 정보 반환"""
        # 한국 시간대 (UTC+9)
        kst = timezone(timedelta(hours=9))
        now = datetime.now(kst)
        
        return {
            "current_date": now.strftime("%Y년 %m월 %d일"),
            "current_time": now.strftime("%H시 %M분"),
            "current_datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
            "day_of_week": now.strftime("%A"),
            "korean_day": ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"][now.weekday()],
            "iso_format": now.isoformat()
        }
    
    def _analyze_deadline_status(self, application_period: str) -> Dict[str, Any]:
        """지원사업 마감일 분석 (YYYYMMDD 형식 포함)"""
        try:
            kst = timezone(timedelta(hours=9))
            now = datetime.now(kst)
            
            # 접수기간에서 마감일 추출 시도
            import re
            
            deadline_info = {
                "status": "unknown",
                "days_remaining": None,
                "deadline_date": None,
                "is_expired": False,
                "is_urgent": False
            }
            
            if not application_period:
                return deadline_info
            
            # YYYYMMDD ~ YYYYMMDD 형식 우선 처리
            yyyymmdd_pattern = r'(\d{8})\s*~\s*(\d{8})'
            yyyymmdd_match = re.search(yyyymmdd_pattern, application_period)
            
            if yyyymmdd_match:
                try:
                    end_date_str = yyyymmdd_match.group(2)  # 마감일
                    year = int(end_date_str[:4])
                    month = int(end_date_str[4:6])
                    day = int(end_date_str[6:8])
                    
                    deadline = datetime(year, month, day, 23, 59, 59, tzinfo=kst)
                    days_diff = (deadline - now).days
                    
                    deadline_info.update({
                        "deadline_date": deadline.strftime("%Y-%m-%d"),
                        "days_remaining": days_diff,
                        "is_expired": days_diff < 0,
                        "is_urgent": 0 <= days_diff <= 3
                    })
                    
                    if days_diff < 0:
                        deadline_info["status"] = "expired"
                    elif days_diff == 0:
                        deadline_info["status"] = "today"
                    elif days_diff <= 3:
                        deadline_info["status"] = "urgent"
                    elif days_diff <= 7:
                        deadline_info["status"] = "soon"
                    else:
                        deadline_info["status"] = "active"
                        
                    return deadline_info
                    
                except ValueError:
                    pass
            
            # YYYY.MM.DD 형식 처리
            dot_pattern = r'(\d{4})\.(\d{1,2})\.(\d{1,2})\s*~\s*(\d{4})\.(\d{1,2})\.(\d{1,2})'
            dot_match = re.search(dot_pattern, application_period)
            
            if dot_match:
                try:
                    year = int(dot_match.group(4))
                    month = int(dot_match.group(5))
                    day = int(dot_match.group(6))
                    
                    deadline = datetime(year, month, day, 23, 59, 59, tzinfo=kst)
                    days_diff = (deadline - now).days
                    
                    deadline_info.update({
                        "deadline_date": deadline.strftime("%Y-%m-%d"),
                        "days_remaining": days_diff,
                        "is_expired": days_diff < 0,
                        "is_urgent": 0 <= days_diff <= 3
                    })
                    
                    if days_diff < 0:
                        deadline_info["status"] = "expired"
                    elif days_diff == 0:
                        deadline_info["status"] = "today"
                    elif days_diff <= 3:
                        deadline_info["status"] = "urgent"
                    elif days_diff <= 7:
                        deadline_info["status"] = "soon"
                    else:
                        deadline_info["status"] = "active"
                        
                    return deadline_info
                    
                except ValueError:
                    pass
            
            # 기타 형식들도 시도할 수 있지만, 기본값 반환
            return deadline_info
            
        except Exception as e:
            logger.error(f"마감일 분석 실패: {e}")
            return {
                "status": "unknown",
                "days_remaining": None,
                "deadline_date": None,
                "is_expired": False,
                "is_urgent": False
            }
    
    def _initialize_openai(self):
        """OpenAI 클라이언트 초기화"""
        if not OPENAI_AVAILABLE:
            logger.warning("OpenAI를 사용할 수 없습니다.")
            return
        
        if not config.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY가 설정되지 않았습니다.")
            return
        
        try:
            self.openai_client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
            logger.info("OpenAI 클라이언트 초기화 완료")
        except Exception as e:
            logger.error(f"OpenAI 클라이언트 초기화 실패: {e}")
    
    @monitor_performance
    def get_response(self, user_query: str) -> Dict[str, Any]:
        """사용자 질문에 대한 RAG 기반 응답 생성 (메모리 기능 포함)"""
        try:
            # 1. 질문 임베딩 생성
            query_embedding = self.embedding_manager.create_embedding(user_query)
            
            # 2. 신청 가능한 지원사업 우선 검색
            search_results = self._search_with_application_priority(query_embedding, top_k=30)
            
            # 3. 컨텍스트 구성 (검색 결과 + 대화 기록)
            context = self._build_context(search_results)
            conversation_context = self._build_conversation_context()
            
            # 4. LLM을 통한 답변 생성 (메모리 포함)
            if self.openai_client:
                response_text = self._generate_response_with_memory(user_query, context, conversation_context)
            else:
                response_text = self._generate_fallback_response(user_query, search_results)
            
            # 5. 결과 구성 (신청 가능 여부 통계 포함)
            applicable_count = len([r for r in search_results if r.get("is_applicable", False)])
            urgent_count = len([r for r in search_results if r.get("deadline_status", {}).get("is_urgent", False)])
            
            result = {
                "answer": response_text,
                "sources": self._extract_sources(search_results),
                "confidence": self._calculate_confidence(search_results),
                "context_used": bool(context),
                "memory_used": len(self.conversation_memory) > 0,
                "applicable_count": applicable_count,
                "urgent_count": urgent_count,
                "total_results": len(search_results)
            }
            
            # 6. 대화 기록 및 메모리 업데이트
            self._add_to_chat_history("user", user_query)
            self._add_to_chat_history("assistant", response_text)
            self._update_conversation_memory(user_query, response_text)
            
            log_chatbot_interaction(
                user_query=user_query,
                response=response_text,
                confidence=result["confidence"],
                sources=result["sources"]
            )
            
            return result
            
        except Exception as e:
            logger.error(f"RAG 응답 생성 실패: {e}")
            return {
                "answer": "죄송합니다. 현재 질문에 대한 답변을 생성할 수 없습니다.",
                "sources": [],
                "confidence": 0.0,
                "context_used": False,
                "memory_used": False,
                "error": str(e)
            }
    
    def _build_context(self, search_results: List[Dict[str, Any]]) -> str:
        """검색 결과를 컨텍스트로 구성 (모든 메타데이터 활용 + 마감일 상태)"""
        if not search_results:
            return ""
        
        contexts = []
        for i, result in enumerate(search_results, 1):
            metadata = result.get("metadata", {})
            
            # 마감일 상태 분석
            application_period = metadata.get('application_period', '')
            deadline_info = self._analyze_deadline_status(application_period)
            
            # 마감일 상태에 따른 이모지와 메시지
            status_emoji = {
                "expired": "❌",
                "today": "🚨",
                "urgent": "⚠️",
                "soon": "⏰",
                "active": "✅",
                "unknown": "❓"
            }
            
            status_message = {
                "expired": "마감됨",
                "today": "오늘 마감!",
                "urgent": f"긴급! {deadline_info['days_remaining']}일 남음",
                "soon": f"{deadline_info['days_remaining']}일 남음",
                "active": f"{deadline_info['days_remaining']}일 남음" if deadline_info['days_remaining'] else "신청 가능",
                "unknown": "마감일 확인 필요"
            }
            
            deadline_status = f"{status_emoji.get(deadline_info['status'], '❓')} {status_message.get(deadline_info['status'], '상태 불명')}"
            
            context_piece = f"""
=== 지원사업 {i} ===
📢 제목: {metadata.get('title', '제목 없음')}
🏢 기관: {metadata.get('organization', '기관 정보 없음')} ({metadata.get('department', '부서 정보 없음')})
🎯 분야: {metadata.get('support_field', '분야 정보 없음')}
👥 대상: {metadata.get('target_audience', '대상 정보 없음')}
👶 연령대: {metadata.get('target_age', '연령 정보 없음')}
🚀 창업경험: {metadata.get('startup_experience', '경험 정보 없음')}
📍 지역: {metadata.get('region', '지역 정보 없음')}
📅 접수기간: {application_period}
⏰ 마감상태: {deadline_status}
📝 설명: {metadata.get('description', '설명 없음')[:300]}...
💰 지원내용: {metadata.get('support_content', '지원내용 정보 없음')[:300]}...
📋 신청방법: {metadata.get('application_method', '신청방법 정보 없음')}
📄 제출서류: {metadata.get('submission_documents', '제출서류 정보 없음')}
📞 연락처: {metadata.get('contact', '연락처 정보 없음')}
📊 유사도: {result.get('score', 0.0):.3f}
            """.strip()
            
            contexts.append(context_piece)
        full_context = "\n\n" + "\n\n".join(contexts)
        logger.info(f"[RAG 컨텍스트 로그] 검색 결과 컨텍스트(상위 {len(contexts)}개):\n{full_context}")
        return full_context
    
    def _build_conversation_context(self) -> str:
        """대화 기록을 컨텍스트로 구성"""
        if not self.conversation_memory:
            return ""
        
        context_parts = ["이전 대화 내용:"]
        for i, memory in enumerate(self.conversation_memory, 1):
            context_parts.append(f"대화 {i}:")
            context_parts.append(f"사용자: {memory['user_query']}")
            context_parts.append(f"답변: {memory['response'][:100]}...")
            context_parts.append("---")
        
        return "\n".join(context_parts)
    
    def _generate_response_with_memory(self, user_query: str, context: str, conversation_context: str) -> str:
        """메모리를 활용한 OpenAI 응답 생성"""
        try:
            # 현재 시간 정보 가져오기
            time_info = self._get_current_time_info()
            
            system_prompt = f"""
당신은 K-Startup 지원사업 전문 상담사입니다. 
사용자의 질문에 대해 제공된 지원사업 정보와 이전 대화 내용을 바탕으로 정확하고 도움이 되는 답변을 제공하세요.

=== 현재 시간 정보 ===
📅 현재 날짜: {time_info['current_date']} ({time_info['korean_day']})
🕐 현재 시간: {time_info['current_time']}
📊 정확한 시각: {time_info['current_datetime']}

답변 시 유의사항:
1. **신청 가능한 지원사업만 추천**: ❌ 마감됨 표시가 있는 지원사업은 절대 추천하지 마세요
2. **현재 날짜 기준 엄격 필터링**: 현재 {time_info['current_date']}를 기준으로 신청 기간이 남은 지원사업만 추천하세요
3. **마감된 지원사업 완전 제외**: 2024년 이전, 이미 마감된 지원사업은 언급조차 하지 마세요
4. **시의성 최우선**: 🚨 오늘 마감, ⚠️ 긴급 표시가 있는 지원사업을 최우선으로 안내하세요
5. **명확한 상태 표시**: 각 지원사업의 마감 상태와 남은 일수를 반드시 표시하세요
6. **연속성 있는 대화**: 이전 대화 내용을 참고하여 맥락에 맞는 답변을 제공하세요
7. **구체적인 정보 제공**: 지원사업명, 기관명, 정확한 마감일, 남은 일수를 포함하세요
8. **사용자 맞춤 추천**: 사용자의 조건(지역, 분야, 창업경험 등)에 맞는 지원사업을 우선 추천하세요
9. **실용적 정보 제공**: 신청 방법, 제출 서류, 연락처 등 즉시 활용 가능한 정보를 제공하세요
10. **정확성 최우선**: 불확실한 정보보다는 확실하고 신청 가능한 정보만 제공하세요
11. **긴급성 강조**: 마감이 임박한 지원사업은 반드시 긴급성을 강조하여 안내하세요
12. **친근하고 전문적인 톤**: 상담사로서 실질적으로 도움이 되는 조언을 제공하세요

마감일 상태 표시 가이드:
- ❌ 마감됨: 이미 접수가 종료된 지원사업
- 🚨 오늘 마감: 오늘이 마감일인 지원사업 (긴급!)
- ⚠️ 긴급: 3일 이내 마감 예정
- ⏰ 곧 마감: 7일 이내 마감 예정
- ✅ 신청 가능: 여유 있게 신청 가능한 지원사업
            """
            
            # 메시지 구성
            messages = [{"role": "system", "content": system_prompt}]
            
            # 대화 컨텍스트 추가
            if conversation_context:
                messages.append({
                    "role": "system", 
                    "content": f"참고할 이전 대화:\n{conversation_context}"
                })
            
            # 현재 질문과 검색 결과
            current_message = f"현재 질문: {user_query}"
            if context:
                current_message += f"\n\n관련 지원사업 정보:\n{context}"
            
            messages.append({"role": "user", "content": current_message})
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=600,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"OpenAI 메모리 응답 생성 실패: {e}")
            return self._generate_fallback_response(user_query, [])
    
    def _search_with_application_priority(self, query_vector: List[float], top_k: int = 30) -> List[Dict[str, Any]]:
        """신청 가능한 지원사업을 우선적으로 검색"""
        try:
            # 필터링 없이 전체 검색을 한 다음, 결과를 후처리로 정렬
            # Pinecone 필터가 제대로 작동하지 않는 경우에 대비
            
            # 더 많은 결과를 가져와서 후처리로 필터링
            all_results = self.pinecone_manager.search_similar(
                query_vector=query_vector,
                top_k=top_k * 4  # 4배 더 가져와서 필터링
            )
            
            # 신청 가능한 지원사업과 만료된 지원사업 분류
            applicable_results = []
            expired_results = []
            current_year_results = []
            
            current_year = datetime.now().year
            
            for result in all_results:
                # 현재 연도 지원사업인지 확인
                is_current_year = result.get("is_current_year", False)
                is_applicable = result.get("is_applicable", False)
                
                if is_current_year:
                    current_year_results.append(result)
                
                if is_applicable:
                    applicable_results.append(result)
                else:
                    expired_results.append(result)
            
            # 우선순위 정렬: 신청 가능 + 현재 연도 > 신청 가능 > 현재 연도 > 기타
            def priority_sort_key(result):
                is_applicable = result.get("is_applicable", False)
                is_current_year = result.get("is_current_year", False)
                deadline_status = result.get("deadline_status", {})
                score = result.get("score", 0.0)
                
                # 우선순위 점수 계산
                priority_score = 0
                
                if is_applicable and is_current_year:
                    priority_score = 1000  # 최우선
                elif is_applicable:
                    priority_score = 500   # 신청 가능
                elif is_current_year:
                    priority_score = 100   # 현재 연도
                else:
                    priority_score = 10    # 기타
                
                # 긴급도 추가 점수
                if deadline_status.get("status") == "today":
                    priority_score += 200
                elif deadline_status.get("status") == "urgent":
                    priority_score += 100
                elif deadline_status.get("status") == "soon":
                    priority_score += 50
                
                return (-priority_score, -score)  # 높은 우선순위, 높은 점수 순
            
            # 전체 결과를 우선순위로 정렬
            all_results.sort(key=priority_sort_key)
            
            # 상위 결과 선택
            final_results = all_results[:top_k]
            
            # 통계 정보 계산
            applicable_count = sum(1 for r in final_results if r.get("is_applicable", False))
            current_year_count = sum(1 for r in final_results if r.get("is_current_year", False))
            urgent_count = sum(1 for r in final_results 
                             if r.get("deadline_status", {}).get("status") in ["today", "urgent"])
            
            logger.info(f"최종 검색 결과: 총 {len(final_results)}개 "
                       f"(신청가능: {applicable_count}개, 현재연도: {current_year_count}개, 긴급: {urgent_count}개)")
            
            return final_results
            
        except Exception as e:
            logger.error(f"우선순위 검색 실패, 기본 검색으로 대체: {e}")
            # 실패 시 기본 검색으로 대체
            return self.pinecone_manager.search_similar(
                query_vector=query_vector,
                top_k=top_k
            )
    
    def _update_conversation_memory(self, user_query: str, response: str):
        """대화 메모리 업데이트"""
        # 새로운 대화 추가
        memory_entry = {
            "user_query": user_query,
            "response": response,
            "timestamp": datetime.now().isoformat(),
            "turn": len(self.conversation_memory) + 1
        }
        
        self.conversation_memory.append(memory_entry)
        
        # 최대 턴 수 제한 (최근 5개 대화만 유지)
        if len(self.conversation_memory) > self.max_memory_turns:
            self.conversation_memory = self.conversation_memory[-self.max_memory_turns:]
            # 턴 번호 재조정
            for i, memory in enumerate(self.conversation_memory):
                memory["turn"] = i + 1
        
        logger.info(f"대화 메모리 업데이트: {len(self.conversation_memory)}개 대화 기억 중")
    
    def get_conversation_summary(self) -> str:
        """대화 요약 반환"""
        if not self.conversation_memory:
            return "아직 대화 기록이 없습니다."
        
        summary_parts = [f"총 {len(self.conversation_memory)}개의 대화를 기억하고 있습니다:\n"]
        
        for memory in self.conversation_memory:
            summary_parts.append(f"대화 {memory['turn']}: {memory['user_query'][:50]}...")
        
        return "\n".join(summary_parts)
    
    def clear_conversation_memory(self):
        """대화 메모리 초기화"""
        self.conversation_memory.clear()
        logger.info("대화 메모리가 초기화되었습니다.")
    
    def get_memory_status(self) -> Dict[str, Any]:
        """메모리 상태 반환"""
        return {
            "total_conversations": len(self.conversation_memory),
            "max_memory_turns": self.max_memory_turns,
            "memory_usage": f"{len(self.conversation_memory)}/{self.max_memory_turns}",
            "oldest_conversation": self.conversation_memory[0]["timestamp"] if self.conversation_memory else None,
            "latest_conversation": self.conversation_memory[-1]["timestamp"] if self.conversation_memory else None
        }
    
    def _generate_fallback_response(self, user_query: str, search_results: List[Dict[str, Any]]) -> str:
        """대체 응답 생성 (OpenAI 없이, 현재 시간 정보 포함)"""
        # 현재 시간 정보 가져오기
        time_info = self._get_current_time_info()
        
        if not search_results:
            return f"""
현재 시간: {time_info['current_date']} {time_info['current_time']}

죄송합니다. '{user_query}'와 관련된 지원사업 정보를 찾을 수 없습니다. 
다른 키워드로 다시 시도해보시거나, 더 구체적인 조건을 말씀해 주세요.

예시: "AI 스타트업", "서울 지역", "3년 미만 기업" 등
            """.strip()
        
        # 가장 유사도가 높은 결과를 기반으로 간단한 응답 생성
        best_match = search_results[0]
        metadata = best_match.get("metadata", {})
        
        # 마감일 상태 분석
        application_period = metadata.get('application_period', '')
        deadline_info = self._analyze_deadline_status(application_period)
        
        # 마감일 상태 메시지
        status_messages = {
            "expired": "❌ 이미 마감된 지원사업입니다",
            "today": "🚨 오늘 마감! 긴급히 신청하세요",
            "urgent": f"⚠️ 긴급! {deadline_info['days_remaining']}일 남았습니다",
            "soon": f"⏰ {deadline_info['days_remaining']}일 남았습니다",
            "active": f"✅ 신청 가능 ({deadline_info['days_remaining']}일 남음)" if deadline_info['days_remaining'] else "✅ 신청 가능",
            "unknown": "❓ 마감일을 확인해 주세요"
        }
        
        deadline_status = status_messages.get(deadline_info['status'], '상태 불명')
        
        response = f"""
현재 시간: {time_info['current_date']} {time_info['current_time']}

'{user_query}'와 관련하여 다음 지원사업을 찾았습니다:

📌 **{metadata.get('title', '제목 정보 없음')}**
🏢 주관기관: {metadata.get('organization', '기관 정보 없음')}
📅 접수기간: {application_period}
⏰ 마감상태: {deadline_status}
🎯 분야: {metadata.get('support_field', '분야 정보 없음')}
👥 대상: {metadata.get('target_audience', '대상 정보 없음')}

📝 설명: {metadata.get('description', '상세 설명이 없습니다.')[:200]}...

더 자세한 정보는 해당 기관에 직접 문의하시기 바랍니다.
📞 연락처: {metadata.get('contact', '연락처 정보 없음')}
        """.strip()
        
        return response
    
    def _extract_sources(self, search_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """검색 결과에서 소스 정보 추출"""
        sources = []
        for result in search_results:
            metadata = result.get("metadata", {})
            sources.append({
                "title": metadata.get("title", "제목 없음"),
                "organization": metadata.get("organization", "기관 정보 없음"),
                "score": result.get("score", 0.0),
                "id": result.get("id", "")
            })
        return sources
    
    def _calculate_confidence(self, search_results: List[Dict[str, Any]]) -> float:
        """응답 신뢰도 계산 (Pinecone 코사인 유사도 기준)"""
        if not search_results:
            return 0.0
        
        # 가장 높은 유사도 점수를 기준으로 신뢰도 계산
        max_score = max(result.get("score", 0.0) for result in search_results)
        
        # Pinecone 코사인 유사도에 맞게 임계값 조정
        # 0.6 이상: 매우 높은 신뢰도 (85-100%)
        # 0.4-0.6: 높은 신뢰도 (60-85%)
        # 0.2-0.4: 보통 신뢰도 (30-60%)
        # 0.2 미만: 낮은 신뢰도 (0-30%)
        
        if max_score >= 0.6:
            # 0.6 이상은 85-100% 신뢰도
            return min(0.85 + (max_score - 0.6) * 0.375, 1.0)  # 0.6->85%, 1.0->100%
        elif max_score >= 0.4:
            # 0.4-0.6은 60-85% 신뢰도
            return 0.6 + (max_score - 0.4) * 1.25  # 0.4->60%, 0.6->85%
        elif max_score >= 0.2:
            # 0.2-0.4는 30-60% 신뢰도
            return 0.3 + (max_score - 0.2) * 1.5  # 0.2->30%, 0.4->60%
        else:
            # 0.2 미만은 0-30% 신뢰도
            return max_score * 1.5  # 0->0%, 0.2->30%
    
    def _add_to_chat_history(self, role: str, content: str):
        """대화 기록 추가"""
        self.chat_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        # 기록 길이 제한
        if len(self.chat_history) > config.MAX_CHAT_HISTORY * 2:  # user + assistant
            self.chat_history = self.chat_history[-config.MAX_CHAT_HISTORY * 2:]
    
    def get_chat_history(self) -> List[Dict[str, Any]]:
        """대화 기록 반환"""
        return self.chat_history.copy()
    
    def clear_chat_history(self):
        """대화 기록 초기화"""
        self.chat_history.clear()
        logger.info("대화 기록이 초기화되었습니다.")
    
    def get_system_status(self) -> Dict[str, Any]:
        """시스템 상태 반환"""
        return {
            "embedding_model_loaded": self.embedding_manager.model is not None,
            "pinecone_connected": self.pinecone_manager.index is not None,
            "openai_available": self.openai_client is not None,
            "chat_history_length": len(self.chat_history),
            "pinecone_stats": self.pinecone_manager.get_index_stats()
        }

# 전역 RAG 시스템 인스턴스
_rag_chatbot = None

def get_rag_chatbot() -> RAGChatbot:
    """RAG 챗봇 싱글톤 인스턴스 반환"""
    global _rag_chatbot
    if _rag_chatbot is None:
        _rag_chatbot = RAGChatbot()
    return _rag_chatbot

def ingest_announcements_to_pinecone(announcements_data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    지원사업 데이터를 Pinecone에 임베딩하여 저장
    
    Args:
        announcements_data: 지원사업 데이터 딕셔너리
        
    Returns:
        Tuple[bool, str]: (성공 여부, 메시지)
    """
    try:
        logger.info("Pinecone 데이터 저장 시작...")
        
        # RAG 시스템 인스턴스 가져오기
        chatbot = get_rag_chatbot()
        
        if not chatbot.embedding_manager.model:
            return False, "임베딩 모델이 초기화되지 않았습니다."
        
        if not chatbot.pinecone_manager.index:
            # Pinecone 재초기화 시도
            logger.info("Pinecone 인덱스가 초기화되지 않아 재초기화를 시도합니다...")
            try:
                chatbot.pinecone_manager._initialize_pinecone()
                if not chatbot.pinecone_manager.index:
                    return False, "Pinecone 인덱스 재초기화에 실패했습니다."
                logger.info("Pinecone 인덱스 재초기화 성공")
            except Exception as e:
                return False, f"Pinecone 인덱스 재초기화 실패: {str(e)}"
        
        # 벡터 데이터 준비
        vectors_to_upsert = []
        processed_count = 0
        skipped_count = 0
        
        logger.info(f"총 {len(announcements_data)}개의 공고 데이터 처리 시작...")
        
        for announcement_id, announcement in announcements_data.items():
            try:
                # 텍스트 내용 구성 (임베딩을 위한 텍스트)
                text_content = _build_announcement_text(announcement)
                
                if not text_content.strip():
                    skipped_count += 1
                    continue
                
                # 임베딩 생성
                embedding = chatbot.embedding_manager.create_embedding(text_content)
                
                # 메타데이터 구성
                metadata = _build_announcement_metadata(announcement)
                
                # 벡터 ID 생성 (고유한 ID)
                vector_id = f"announcement_{announcement_id}"
                
                # 벡터 데이터 구성
                vector_data = {
                    "id": vector_id,
                    "values": embedding,
                    "metadata": metadata
                }
                
                vectors_to_upsert.append(vector_data)
                processed_count += 1
                
                # 배치 크기에 도달하면 업서트 실행
                if len(vectors_to_upsert) >= 100:
                    success = chatbot.pinecone_manager.upsert_vectors(vectors_to_upsert)
                    if not success:
                        logger.error(f"배치 업서트 실패 (processed: {processed_count})")
                        return False, f"벡터 업서트 실패 (처리된 데이터: {processed_count}개)"
                    
                    vectors_to_upsert.clear()
                    logger.info(f"진행상황: {processed_count}개 처리 완료")
                
            except Exception as e:
                logger.error(f"공고 {announcement_id} 처리 중 오류: {e}")
                skipped_count += 1
                continue
        
        # 남은 벡터들 업서트
        if vectors_to_upsert:
            success = chatbot.pinecone_manager.upsert_vectors(vectors_to_upsert)
            if not success:
                logger.error("마지막 배치 업서트 실패")
                return False, f"마지막 배치 업서트 실패 (처리된 데이터: {processed_count}개)"
        
        message = f"Pinecone 저장 완료: {processed_count}개 저장, {skipped_count}개 스킵"
        logger.info(message)
        
        return True, message
        
    except Exception as e:
        error_msg = f"Pinecone 데이터 저장 중 오류 발생: {e}"
        logger.error(error_msg)
        return False, error_msg

def _build_announcement_text(announcement: Dict[str, Any]) -> str:
    """
    공고 데이터를 임베딩을 위한 텍스트로 변환 (모든 필드 포함)
    
    Args:
        announcement: 공고 데이터
        
    Returns:
        str: 임베딩용 텍스트
    """
    # 모든 필드를 포함한 텍스트 구성
    text_parts = []
    
    # 제목
    title = announcement.get('title', '')
    if title:
        text_parts.append(f"제목: {title}")
    
    # 기관 정보
    org_name = announcement.get('org_name_ref', '')
    if org_name:
        text_parts.append(f"기관: {org_name}")
    
    # 지원분야
    support_field = announcement.get('support_field', '')
    if support_field:
        text_parts.append(f"분야: {support_field}")
    
    # 대상
    target_audience = announcement.get('target_audience', '')
    if target_audience:
        text_parts.append(f"대상: {target_audience}")
    
    # 연령대
    target_age = announcement.get('target_age', '')
    if target_age:
        text_parts.append(f"연령대: {target_age}")
    
    # 창업경험
    startup_experience = announcement.get('startup_experience', '')
    if startup_experience:
        text_parts.append(f"창업경험: {startup_experience}")
    
    # 지역
    region = announcement.get('region', '')
    if region:
        text_parts.append(f"지역: {region}")
    
    # 지원내용
    support_content = announcement.get('support_content', '')
    if support_content:
        # 지원내용이 길 수 있으므로 일부만 포함
        support_content_short = support_content[:500] if len(support_content) > 500 else support_content
        text_parts.append(f"지원내용: {support_content_short}")
    
    # 상세 설명
    description = announcement.get('description', '')
    if description:
        # 설명이 길 수 있으므로 일부만 포함
        description_short = description[:500] if len(description) > 500 else description
        text_parts.append(f"설명: {description_short}")
    
    # 신청방법
    application_method = announcement.get('application_method', [])
    if application_method and isinstance(application_method, list):
        methods = [method for method in application_method if method and 'None' not in method]
        if methods:
            text_parts.append(f"신청방법: {', '.join(methods[:3])}")  # 최대 3개만
    
    # 접수기간
    application_period = announcement.get('application_period', '')
    if application_period:
        text_parts.append(f"접수기간: {application_period}")
    
    # 마감일 (추출된 마감일)
    deadline = announcement.get('deadline', '')
    if deadline:
        text_parts.append(f"마감일: {deadline}")
    
    # 공고일자
    announcement_date = announcement.get('announcement_date', '')
    if announcement_date:
        text_parts.append(f"공고일: {announcement_date}")
    
    # 부서
    department = announcement.get('department', '')
    if department:
        text_parts.append(f"담당부서: {department}")
    
    return " | ".join(text_parts)

def _build_announcement_metadata(announcement: Dict[str, Any]) -> Dict[str, Any]:
    """
    공고 데이터를 메타데이터로 변환 (모든 필드 포함)
    
    Args:
        announcement: 공고 데이터
        
    Returns:
        Dict[str, Any]: 메타데이터
    """
    # 설명과 지원내용 길이 제한 (Pinecone 메타데이터 크기 제한 고려)
    description = announcement.get('description', '')
    if description and len(description) > 1000:
        description = description[:1000] + "..."
    
    support_content = announcement.get('support_content', '')
    if support_content and len(support_content) > 1000:
        support_content = support_content[:1000] + "..."
    
    # 신청방법 처리 (리스트를 문자열로 변환)
    application_method = announcement.get('application_method', [])
    if isinstance(application_method, list):
        # None이 아닌 유효한 방법들만 필터링
        valid_methods = [method for method in application_method if method and 'None' not in method]
        application_method_str = ' | '.join(valid_methods) if valid_methods else '정보 없음'
    else:
        application_method_str = str(application_method) if application_method else '정보 없음'
    
    # 첨부파일 처리
    attachments = announcement.get('attachments', [])
    attachments_str = str(len(attachments)) + '개' if attachments else '없음'
    
    # 모든 메타데이터 구성
    metadata = {
        # 기본 정보
        "title": announcement.get('title', '제목 없음'),
        "organization": announcement.get('org_name_ref', '기관 정보 없음'),
        "org_id": announcement.get('org_id', ''),
        "department": announcement.get('department', ''),
        
        # 분야 및 대상
        "support_field": announcement.get('support_field', '분야 정보 없음'),
        "target_audience": announcement.get('target_audience', '대상 정보 없음'),
        "target_age": announcement.get('target_age', ''),
        "startup_experience": announcement.get('startup_experience', ''),
        
        # 지역 및 일정
        "region": announcement.get('region', '지역 정보 없음'),
        "application_period": announcement.get('application_period', '접수기간 정보 없음'),
        "deadline": announcement.get('deadline', ''),  # 추출된 마감일
        "announcement_date": announcement.get('announcement_date', ''),
        "announcement_number": str(announcement.get('announcement_number', '')),
        
        # 내용
        "description": description or "설명 없음",
        "support_content": support_content or "지원내용 정보 없음",
        
        # 신청 관련
        "application_method": application_method_str,
        "submission_documents": announcement.get('submission_documents', '제출서류 정보 없음'),
        "selection_procedure": announcement.get('selection_procedure', ''),
        
        # 연락처
        "contact": announcement.get('contact', '연락처 정보 없음'),
        "inquiry": announcement.get('inquiry', ''),
        
        # 기타
        "attachments_count": attachments_str,
        
        # 시스템 정보
        "ingested_at": datetime.now().isoformat(),
        "data_source": "k_startup_api"
    }
    
    # 빈 값들을 기본값으로 대체
    for key, value in metadata.items():
        if not value or value == '':
            if key in ['title', 'organization', 'support_field', 'target_audience', 'region']:
                metadata[key] = f"{key} 정보 없음"
            else:
                metadata[key] = "정보 없음"
    
    return metadata

if __name__ == "__main__":
    # 테스트 코드
    chatbot = get_rag_chatbot()
    
    # 시스템 상태 확인
    status = chatbot.get_system_status()
    print("RAG 시스템 상태:")
    for key, value in status.items():
        print(f"  {key}: {value}")
    
    # 간단한 질문 테스트 (실제 데이터가 있을 때)
    # test_query = "스타트업 지원사업이 있나요?"
    # response = chatbot.get_response(test_query)
    # print(f"\n질문: {test_query}")
    # print(f"답변: {response['answer']}")
    # print(f"신뢰도: {response['confidence']}") 