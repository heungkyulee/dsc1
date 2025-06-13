"""
데이터 로딩 및 캐싱 유틸리티 모듈
Streamlit 애플리케이션의 데이터 로딩과 캐싱을 관리합니다.
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any
from datetime import datetime

from config import config
from logger import get_logger
import data_handler

logger = get_logger(__name__)


@st.cache_data(ttl=config.CACHE_TTL)
def load_announcements_data() -> pd.DataFrame:
    """공고 데이터 로드 (캐싱 적용) - 전체 K-Startup 데이터 포함"""
    try:
        # get_all_contests()를 사용하여 전체 데이터 로드 (K-Startup API + 사용자 추가 데이터)
        all_contests = data_handler.get_all_contests()
        logger.info(f"데이터 핸들러에서 받은 데이터 타입: {type(all_contests)}")
        
        if all_contests:
            # list를 DataFrame으로 변환
            if isinstance(all_contests, list):
                logger.info(f"리스트 데이터 길이: {len(all_contests)}")
                df = pd.DataFrame(all_contests)
            elif isinstance(all_contests, dict):
                logger.info(f"딕셔너리 데이터 키 수: {len(all_contests)}")
                # 첫 번째 항목 구조 확인
                if all_contests:
                    first_key = list(all_contests.keys())[0]
                    logger.info(f"첫 번째 항목 구조: {type(all_contests[first_key])}")
                
                df = pd.DataFrame.from_dict(all_contests, orient='index')
            else:
                logger.warning(f"예상치 못한 데이터 타입: {type(all_contests)}")
                df = pd.DataFrame()
            
            if not df.empty:
                logger.info(f"DataFrame 컬럼: {list(df.columns)}")
                logger.info(f"DataFrame 형태: {df.shape}")
                
                # pblancId가 없는 데이터에 인덱스 기반 ID 추가
                if 'pblancId' not in df.columns:
                    df['pblancId'] = df.index.astype(str)
                else:
                    # pblancId가 비어있는 행들에 인덱스 기반 ID 추가
                    for idx, row in df.iterrows():
                        if pd.isna(df.at[idx, 'pblancId']) or not df.at[idx, 'pblancId']:
                            df.at[idx, 'pblancId'] = str(idx)
                
                # 날짜 컬럼 처리
                date_columns = ['announcement_date', 'deadline', 'created_at', 'updated_at']
                for col in date_columns:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col], errors='coerce')
                        logger.debug(f"날짜 컬럼 {col} 처리 완료")
                
                logger.info(f"공고 데이터 로드 완료: {len(df)}개 항목 (K-Startup API + 사용자 추가 데이터)")
                return df
            else:
                logger.warning("빈 DataFrame 반환")
                return pd.DataFrame()
        else:
            logger.warning("공고 데이터가 없습니다")
            return pd.DataFrame()
            
    except Exception as e:
        logger.error(f"공고 데이터 로드 실패: {e}", exc_info=True)
        # Streamlit 에러는 main 함수에서 처리하도록 함
        return pd.DataFrame()


def load_announcements_data_fresh() -> pd.DataFrame:
    """공고 데이터 실시간 로드 (캐시 무시)"""
    try:
        # 캐시를 무시하고 직접 데이터 로드
        data_handler.load_all_data()  # 강제로 최신 데이터 로드
        
        # get_all_contests() 함수 사용 (실시간 데이터)
        all_contests = data_handler.get_all_contests()
        
        logger.info(f"[FRESH] 실시간 데이터 로드 - 타입: {type(all_contests)}, 길이: {len(all_contests) if all_contests else 0}")
        
        if all_contests:
            if isinstance(all_contests, list):
                df = pd.DataFrame(all_contests)
                
                # pblancId가 없는 데이터에 인덱스 기반 ID 추가
                for idx, row in df.iterrows():
                    if 'pblancId' not in df.columns or pd.isna(df.at[idx, 'pblancId']) or not df.at[idx, 'pblancId']:
                        df.at[idx, 'pblancId'] = str(idx)
                        
            elif isinstance(all_contests, dict):
                df = pd.DataFrame.from_dict(all_contests, orient='index')
            else:
                logger.warning(f"[FRESH] 예상치 못한 데이터 타입: {type(all_contests)}")
                return pd.DataFrame()
            
            if not df.empty:
                # 날짜 컬럼 처리
                date_columns = ['announcement_date', 'deadline', 'created_at', 'updated_at']
                for col in date_columns:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col], errors='coerce')
                
                logger.info(f"[FRESH] 실시간 데이터 로드 완료: {len(df)}개 항목")
                return df
            
        logger.warning("[FRESH] 실시간 데이터가 비어있음")
        return pd.DataFrame()
        
    except Exception as e:
        logger.error(f"[FRESH] 실시간 데이터 로드 실패: {e}", exc_info=True)
        return pd.DataFrame()


def clear_announcements_cache():
    """공고 데이터 캐시 클리어"""
    try:
        # Streamlit 캐시 클리어
        if hasattr(st, 'cache_data'):
            load_announcements_data.clear()
            logger.info("공고 데이터 캐시 클리어 완료")
        
        # 세션 상태 클리어
        if 'announcements_data' in st.session_state:
            del st.session_state['announcements_data']
            
        return True
    except Exception as e:
        logger.error(f"캐시 클리어 실패: {e}")
        return False


@st.cache_data(ttl=config.CACHE_TTL)
def load_organizations_data() -> Dict[str, Any]:
    """기관 데이터 로드 (캐싱 적용)"""
    try:
        organizations = data_handler.get_all_organizations()
        logger.info(f"기관 데이터 로드 완료: {len(organizations)}개 기관")
        return organizations
    except Exception as e:
        logger.error(f"기관 데이터 로드 실패: {e}")
        st.error(f"기관 데이터 로드 중 오류가 발생했습니다: {e}")
        return {}


def initialize_session_state():
    """세션 상태 변수 초기화"""
    defaults = {
        'current_page': '대시보드',
        'selected_announcement_id': None,
        'search_query': '',
        'search_filters': {},
        'chat_history': [],
        'announcements_data': None,
        'organizations_data': None,
        'last_refresh': None
    }
    
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value 