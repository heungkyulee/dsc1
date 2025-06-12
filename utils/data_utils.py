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
    """공고 데이터 로드 (캐싱 적용)"""
    try:
        announcements = data_handler.get_all_announcements()
        logger.info(f"데이터 핸들러에서 받은 데이터 타입: {type(announcements)}")
        
        if announcements:
            # dict를 DataFrame으로 변환
            if isinstance(announcements, dict):
                logger.info(f"딕셔너리 데이터 키 수: {len(announcements)}")
                # 첫 번째 항목 구조 확인
                if announcements:
                    first_key = list(announcements.keys())[0]
                    logger.info(f"첫 번째 항목 구조: {type(announcements[first_key])}")
                
                df = pd.DataFrame.from_dict(announcements, orient='index')
            elif isinstance(announcements, list):
                logger.info(f"리스트 데이터 길이: {len(announcements)}")
                df = pd.DataFrame(announcements)
            else:
                logger.warning(f"예상치 못한 데이터 타입: {type(announcements)}")
                df = pd.DataFrame()
            
            if not df.empty:
                logger.info(f"DataFrame 컬럼: {list(df.columns)}")
                logger.info(f"DataFrame 형태: {df.shape}")
                
                # 날짜 컬럼 처리
                date_columns = ['announcement_date', 'deadline', 'created_at', 'updated_at']
                for col in date_columns:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col], errors='coerce')
                        logger.debug(f"날짜 컬럼 {col} 처리 완료")
                
                logger.info(f"공고 데이터 로드 완료: {len(df)}개 항목")
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