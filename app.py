"""
K-Startup 지원사업 관리 Streamlit 애플리케이션
Cursor Rules에 따른 체계적인 4페이지 구조 구현
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
import time

# streamlit-option-menu 추가
try:
    from streamlit_option_menu import option_menu
    OPTION_MENU_AVAILABLE = True
except ImportError:
    OPTION_MENU_AVAILABLE = False
    st.warning("streamlit-option-menu이 설치되지 않았습니다. pip install streamlit-option-menu로 설치해주세요.")

# 프로젝트 모듈 임포트
from config import config
from logger import get_logger, log_user_action, HealthChecker
import data_handler
import crawler
from rag_system import get_rag_chatbot, ingest_announcements_to_pinecone

# 로거 설정
logger = get_logger(__name__)

# Streamlit 페이지 설정
st.set_page_config(
    page_title=config.STREAMLIT_PAGE_TITLE,
    layout=config.STREAMLIT_LAYOUT,
    initial_sidebar_state="expanded",
    page_icon="🚀",
    menu_items={
        'About': f"# {config.APP_TITLE}\n\n데이터 구조화 기반 지원사업 관리 시스템",
        'Report a bug': None,
        'Get Help': None
    }
)

# 커스텀 CSS 스타일 적용
def apply_custom_styles():
    """커스텀 CSS 스타일 적용"""
    st.markdown("""
    <style>
    /* 전체 앱 스타일 */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }
    
    /* 사이드바 스타일 - 최신 Streamlit 버전 호환 */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #262730 0%, #262730 100%);
    }
    
    section[data-testid="stSidebar"] .css-1d391kg {
        background: linear-gradient(180deg, #262730 0%, #262730 100%);
    }
    
    /* 사이드바 텍스트 */
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] label {
        color: white !important;
    }
    
    /* 라디오 버튼 스타일 */
    section[data-testid="stSidebar"] .stRadio > div {
        background: rgba(255,255,255,0.1);
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    /* 메트릭 카드 스타일 */
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border: none;
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        transition: transform 0.2s ease;
    }
    
    [data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 40px rgba(0,0,0,0.15);
    }
    
    [data-testid="metric-container"] > div {
        color: white !important;
    }
    
    [data-testid="metric-container"] [data-testid="metric-value"] {
        color: white !important;
        font-size: 2rem !important;
        font-weight: 700;
    }
    
    [data-testid="metric-container"] [data-testid="metric-label"] {
        color: rgba(255,255,255,0.8) !important;
        font-weight: 600;
    }
    
    /* 버튼 스타일 */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.7rem 1.5rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.2);
        background: linear-gradient(135deg, #5a67d8 0%, #6b46c1 100%);
    }
    
    /* 주요 버튼 스타일 */
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    }
    
    .stButton > button[kind="secondary"] {
        background: linear-gradient(135deg, #444550 0%, #444550 100%);
    }
    
    /* 입력 필드 스타일 */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div > select {
        border-radius: 10px;
        border: 2px solid #e5e7eb;
        padding: 0.75rem;
        transition: border-color 0.3s ease;
    }
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus,
    .stSelectbox > div > div > select:focus {
        border-color: #3b82f6;
        box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }
    
    /* 제목 스타일 */
    h1 {
        color: #1f2937;
        font-weight: 800;
        margin-bottom: 2rem;
        text-align: center;
    }
    
    h2, h3 {
        color: #374151;
        font-weight: 700;
        margin: 1.5rem 0 1rem 0;
    }
    
    /* 차트 컨테이너 스타일 */
    .js-plotly-plot {
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    }
    
    /* 반응형 디자인 */
    @media (max-width: 768px) {
        .main .block-container {
            padding: 1rem;
        }
        
        [data-testid="metric-container"] {
            padding: 1rem;
        }
        
        .stButton > button {
            width: 100%;
            margin: 0.5rem 0;
        }
    }
    </style>
    """, unsafe_allow_html=True)

# 세션 상태 초기화
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

# 데이터 로딩 함수
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

# 사이드바 네비게이션
def render_sidebar():
    """사이드바 메뉴 렌더링 - streamlit-option-menu 활용"""
    
    # 사이드바 헤더
    with st.sidebar:
        st.markdown("""
        <div style="text-align: center; padding: 1rem 0;">
            <h1 style="color: white; font-size: 2rem; margin: 0;">🚀 K-Startup</h1>
            <p style="color: rgba(255,255,255,0.8); margin: 0.5rem 0;">지원사업 관리시스템</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 프로젝트 소개
        st.markdown("""
        <div style="background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
            <p style="color: rgba(255,255,255,0.9); font-size: 0.9rem; margin: 0; line-height: 1.4;">
                💡 <strong>K-Startup 지원사업 통합 관리 플랫폼</strong><br/>
                • 실시간 지원사업 정보 수집 및 관리<br/>
                • AI 기반 맞춤형 지원사업 추천<br/>
                • 신청 기간 기반 스마트 필터링<br/>
                • 대화형 챗봇을 통한 상담 서비스
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # K-Startup API 데이터 수집 버튼 (상단으로 이동)
        if st.button("🌐 K-Startup API 데이터 수집", help="K-Startup API에서 최신 10,000개 데이터를 수집하고 Pinecone에 저장합니다", key="crawl_btn", type="primary", use_container_width=True):
            collect_and_store_data()
        
        st.markdown("---")
        
        # 메인 네비게이션 메뉴
        if OPTION_MENU_AVAILABLE:
            page_options = ["대시보드", "신규 지원사업 생성", "지원사업 검색 및 필터링", "챗봇"]
            page_icons = ["📊", "➕", "🔍", "🤖"]
            
            # 현재 페이지 인덱스 찾기
            current_index = 0
            if st.session_state.current_page in page_options:
                current_index = page_options.index(st.session_state.current_page)
            
            selected = option_menu(
                menu_title=None,
                options=page_options,
                icons=["bar-chart", "plus-circle", "search", "robot"],
                menu_icon="cast",
                default_index=current_index,
                orientation="vertical",
                styles={
                    "container": {"padding": "0!important", "background-color": "transparent"},
                    "icon": {"color": "white", "font-size": "18px"}, 
                    "nav-link": {
                        "font-size": "14px", 
                        "text-align": "left", 
                        "margin": "2px",
                        "color": "white",
                        "background-color": "rgba(255,255,255,0.1)",
                        "border-radius": "8px"
                    },
                    "nav-link-selected": {
                        "background-color": "rgba(255,255,255,0.3)",
                        "color": "white",
                        "font-weight": "bold"
                    },
                }
            )
            
            st.session_state.current_page = selected
        else:
            # 폴백: 기존 라디오 버튼 사용
            page_options = {
                "📊 대시보드": "대시보드",
                "➕ 신규 생성": "신규 지원사업 생성", 
                "🔍 검색 및 관리": "지원사업 검색 및 필터링",
                "🤖 AI 챗봇": "챗봇"
            }
            
            current_page_display = None
            for display_name, page_name in page_options.items():
                if st.session_state.current_page == page_name:
                    current_page_display = display_name
                    break
            
            if not current_page_display:
                current_page_display = "📊 대시보드"
            
            selected_display = st.radio(
                "페이지 선택",
                list(page_options.keys()),
                index=list(page_options.keys()).index(current_page_display),
                label_visibility="collapsed"
            )
            
            st.session_state.current_page = page_options[selected_display]
        
        # 사이드바 푸터
        st.markdown("---")
        st.caption("© 2025 2025-1 DSC1 2조 | Version 1.0.0")

def collect_and_store_data():
    """K-Startup API에서 데이터를 수집하고 Pinecone에 저장하는 함수"""
    progress_container = st.container()
    
    with progress_container:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # 0단계: Pinecone 인덱스 준비
            status_text.text("🔧 Pinecone 벡터 DB 준비 중...")
            progress_bar.progress(5)
            
            # RAG 시스템 초기화 (이때 자동으로 인덱스 차원 확인 및 재생성)
            chatbot = get_rag_chatbot()
            
            if not chatbot.embedding_manager.model:
                st.error("❌ 임베딩 모델 초기화 실패")
                return
            
            if not chatbot.pinecone_manager.index:
                st.error("❌ Pinecone 인덱스 초기화 실패")
                return
            
            # 1단계: API 데이터 수집
            status_text.text("🌐 K-Startup API 연결 중...")
            progress_bar.progress(10)
            
            logger.info("K-Startup API 데이터 수집 시작")
            
            # crawler.py의 fetch_all_announcements_from_api() 함수 호출
            status_text.text("📥 API 데이터 수집 중... (최대 10,000개)")
            progress_bar.progress(30)
            
            # 실제 크롤링 실행
            crawler.fetch_all_announcements_from_api()
            
            progress_bar.progress(50)
            status_text.text("📊 수집된 데이터 로드 중...")
            
            # 수집된 데이터 로드
            announcements_data = data_handler.get_all_announcements()
            
            if not announcements_data:
                st.error("❌ 수집된 데이터가 없습니다. API 연결을 확인해주세요.")
                return
            
            data_count = len(announcements_data)
            logger.info(f"총 {data_count}개의 공고 데이터 수집 완료")
            
            progress_bar.progress(60)
            status_text.text(f"✅ {data_count:,}개 데이터 수집 완료")
            
            # 2단계: Pinecone에 임베딩하여 저장
            status_text.text("🧠 AI 벡터 변환 및 저장 중...")
            progress_bar.progress(70)
            
            # Pinecone에 데이터 저장
            success, message = ingest_announcements_to_pinecone(announcements_data)
            
            progress_bar.progress(90)
            
            if success:
                progress_bar.progress(100)
                status_text.text("🎉 모든 작업 완료!")
                
                st.success(f"""
                ✅ **데이터 수집 및 저장 완료!**
                
                📊 **수집 결과:**
                - API 데이터: {data_count:,}개 공고
                - {message}
                
                🤖 **이제 AI 챗봇에서 최신 데이터로 질문하실 수 있습니다!**
                """)
                
                # 캐시 초기화
                st.cache_data.clear()
                st.session_state.last_refresh = datetime.now()
                
                # 로깅
                log_user_action("data_crawl_and_store", details={
                    "timestamp": datetime.now().isoformat(),
                    "data_count": data_count,
                    "pinecone_result": message
                })
                
                logger.info(f"데이터 수집 및 Pinecone 저장 완료: {data_count}개 데이터")
                
            else:
                st.error(f"❌ Pinecone 저장 실패: {message}")
                logger.error(f"Pinecone 저장 실패: {message}")
                
        except Exception as e:
            error_msg = str(e)
            st.error(f"❌ 데이터 수집 중 오류 발생: {error_msg}")
            logger.error(f"데이터 수집 실패: {error_msg}", exc_info=True)
            
            # 문제 해결 제안
            with st.expander("🔧 문제 해결 방법"):
                st.markdown("""
                **일반적인 해결 방법:**
                1. 인터넷 연결 확인
                2. API 키 설정 확인
                3. Pinecone API 키 확인
                4. 시스템 상태 확인 버튼 클릭
                5. 페이지 새로고침 후 재시도
                
                **벡터 차원 불일치 오류 시:**
                - 기존 Pinecone 인덱스가 자동으로 재생성됩니다
                - 문제가 지속되면 "🗑️ 벡터 DB 초기화" 버튼 사용
                
                **지속적인 문제 시:**
                - 개발팀에 문의하세요
                - 로그 파일을 확인하세요
                """)
        
        finally:
            # 프로그레스 바 정리
            progress_bar.empty()
            status_text.empty()

# 1. 대시보드 페이지
def render_dashboard_page():
    """대시보드 페이지 렌더링 - 개선된 UX"""
    # 페이지 헤더
    st.title("📊 K-Startup 대시보드")
    st.markdown("### 실시간 지원사업 현황 및 통계 분석")
    st.markdown("---")
    
    try:
        # 로딩 상태 표시
        with st.spinner("📊 데이터를 불러오는 중..."):
            df_announcements = load_announcements_data()
            organizations = load_organizations_data()
        
        if df_announcements.empty:
            st.warning("⚠️ 데이터가 없습니다")
            st.info("표시할 공고 데이터가 없습니다. 사이드바의 '🌐 데이터 수집' 버튼을 클릭하여 최신 데이터를 가져오세요.")
            return
        
        # 핵심 지표 카드
        st.markdown("### 🎯 핵심 지표")
        
        # 메트릭 계산
        total_announcements = len(df_announcements)
        
        # 안전한 방식으로 활성 상태 카운트
        if 'status' in df_announcements.columns:
            active_announcements = len(df_announcements[df_announcements['status'] == 'active'])
        else:
            active_announcements = total_announcements  # status 컬럼이 없으면 전체를 활성으로 간주
        
        total_organizations = len(organizations)
        
        # 최근 30일 내 공고 수 - 안전한 방식으로 처리
        recent_announcements = 0
        if 'announcement_date' in df_announcements.columns:
            try:
                recent_date = datetime.now() - timedelta(days=30)
                mask = pd.to_datetime(df_announcements['announcement_date'], errors='coerce') >= recent_date
                recent_announcements = len(df_announcements[mask])
            except Exception as e:
                logger.warning(f"최근 공고 수 계산 실패: {e}")
                recent_announcements = 0
        
        # 메트릭 카드 표시
        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
        
        with metric_col1:
            delta_total = f"+{recent_announcements}" if recent_announcements > 0 else None
            st.metric(
                "📢 전체 지원사업", 
                f"{total_announcements:,}",
                delta=delta_total,
                help="전체 등록된 지원사업 수"
            )
        
        with metric_col2:
            active_rate = (active_announcements / total_announcements * 100) if total_announcements > 0 else 0
            st.metric(
                "🟢 진행중인 사업", 
                f"{active_announcements:,}",
                delta=f"{active_rate:.1f}%",
                help="현재 신청 가능한 지원사업 수"
            )
        
        with metric_col3:
            avg_per_org = (total_announcements / total_organizations) if total_organizations > 0 else 0
            st.metric(
                "🏢 참여 기관수", 
                f"{total_organizations:,}",
                delta=f"평균 {avg_per_org:.1f}개",
                help="지원사업을 제공하는 기관 수"
            )
        
        with metric_col4:
            st.metric(
                "📅 최근 30일 신규", 
                f"{recent_announcements:,}",
                delta="이번 달" if recent_announcements > 0 else None,
                help="지난 30일간 새로 등록된 지원사업"
            )
        
        st.divider()
        
        # 차트 섹션
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.subheader("📈 기관별 지원사업 분포")
            try:
                # 기관 컬럼 확인 및 차트 생성
                org_col = None
                for possible_col in ['organization', 'org_name_ref']:
                    if possible_col in df_announcements.columns:
                        org_col = possible_col
                        break
                
                if org_col and df_announcements[org_col].notna().any():
                    org_counts = df_announcements[org_col].value_counts().head(10)
                    
                    if len(org_counts) > 0:
                        fig_bar = px.bar(
                            x=org_counts.values,
                            y=org_counts.index,
                            orientation='h',
                            title="상위 10개 기관별 공고 수",
                            labels={'x': '공고 수', 'y': '기관명'}
                        )
                        fig_bar.update_layout(height=400)
                        st.plotly_chart(fig_bar, use_container_width=True)
                    else:
                        st.info("기관별 분포를 표시할 데이터가 없습니다.")
                else:
                    st.info("기관별 분포 데이터가 없습니다.")
            
            except Exception as e:
                logger.error(f"기관별 분포 차트 생성 실패: {e}")
                st.error(f"차트 생성 중 오류 발생: {e}")
        
        with col_right:
            st.subheader("🎯 지원분야별 분포")
            try:
                # 카테고리 컬럼 확인 및 차트 생성
                category_col = None
                for possible_col in ['category', 'support_field']:
                    if possible_col in df_announcements.columns:
                        category_col = possible_col
                        break
                
                if category_col and df_announcements[category_col].notna().any():
                    category_counts = df_announcements[category_col].value_counts().head(8)
                    
                    if len(category_counts) > 0:
                        fig_pie = px.pie(
                            values=category_counts.values,
                            names=category_counts.index,
                            title="분야별 지원사업 비율"
                        )
                        fig_pie.update_layout(height=400)
                        st.plotly_chart(fig_pie, use_container_width=True)
                    else:
                        st.info("분야별 분포를 표시할 데이터가 없습니다.")
                else:
                    st.info("분야별 분포 데이터가 없습니다.")
            
            except Exception as e:
                logger.error(f"분야별 분포 차트 생성 실패: {e}")
                st.error(f"차트 생성 중 오류 발생: {e}")
        
        # 최신 공고 리스트
        st.subheader("🆕 최신 지원사업 공고")
        try:
            if 'announcement_date' in df_announcements.columns:
                # 날짜가 있는 경우 최신순으로 정렬
                date_col = pd.to_datetime(df_announcements['announcement_date'], errors='coerce')
                valid_dates_mask = date_col.notna()
                
                if valid_dates_mask.any():
                    latest_announcements = df_announcements[valid_dates_mask].nlargest(5, 'announcement_date')
                else:
                    latest_announcements = df_announcements.head(5)  # 날짜가 유효하지 않으면 상위 5개
            else:
                latest_announcements = df_announcements.head(5)  # 날짜 컬럼이 없으면 상위 5개
            
            if not latest_announcements.empty:
                for idx, row in latest_announcements.iterrows():
                    with st.container():
                        col_info, col_action = st.columns([4, 1])
                        
                        with col_info:
                            title = row.get('title', '제목 없음')
                            st.markdown(f"**{title}**")
                            
                            # 날짜와 기관 정보
                            date_str = 'N/A'
                            if 'announcement_date' in row and pd.notna(row['announcement_date']):
                                try:
                                    if hasattr(row['announcement_date'], 'strftime'):
                                        date_str = row['announcement_date'].strftime('%Y-%m-%d')
                                    else:
                                        date_str = str(row['announcement_date'])
                                except:
                                    date_str = 'N/A'
                            
                            org_name = row.get('organization', row.get('org_name_ref', 'N/A'))
                            st.caption(f"📅 {date_str} | 🏢 {org_name}")
                        
                        with col_action:
                            if st.button("상세보기", key=f"detail_{idx}"):
                                st.session_state.selected_announcement_id = str(idx)
                                st.session_state.current_page = "지원사업 검색 및 필터링"
                                st.rerun()
                        
                        st.divider()
            else:
                st.info("표시할 최신 공고가 없습니다.")
        
        except Exception as e:
            logger.error(f"최신 공고 리스트 생성 실패: {e}")
            st.error(f"최신 공고 표시 중 오류 발생: {e}")
        
        # 마지막 업데이트 정보
        if st.session_state.last_refresh:
            st.caption(f"마지막 업데이트: {st.session_state.last_refresh.strftime('%Y-%m-%d %H:%M:%S')}")
        
        log_user_action("view_dashboard")
    
    except Exception as e:
        logger.error(f"대시보드 페이지 렌더링 실패: {e}")
        st.error(f"대시보드 로드 중 오류가 발생했습니다: {str(e)}")
        st.info("데이터를 새로고침해보세요.")

# 2. 신규 지원사업 생성 페이지
def render_create_page():
    """신규 지원사업 생성 페이지 - 개선된 UX"""
    # 페이지 헤더
    st.title("➕ 신규 지원사업 생성")
    st.markdown("### 새로운 지원사업 정보를 등록하여 창업 생태계를 확장하세요")
    st.markdown("---")
    
    # 도움말 섹션
    with st.expander("📝 작성 가이드", expanded=False):
        st.markdown("""
        **필수 입력 항목** (⭐ 표시)
        - **제목**: 명확하고 간결한 지원사업명
        - **주관기관**: 지원사업을 주관하는 기관명
        - **지원분야**: 해당하는 지원 분야 선택
        - **신청마감일**: 지원자가 신청할 수 있는 마지막 날짜
        - **상세설명**: 지원사업의 목적, 내용, 신청방법 등
        
        **작성 팁**
        - 📋 명확하고 구체적인 정보 제공
        - 🎯 지원 대상을 명확히 기술
        - 💰 지원 금액과 조건을 상세히 설명
        - 📞 문의처 정보를 정확히 입력
        """)
    
    st.markdown("---")
    
    with st.form("create_announcement_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### ⭐ 필수 정보")
            title = st.text_input(
                "지원사업 제목*", 
                placeholder="예: 2024년 초기창업패키지",
                help="명확하고 간결한 지원사업명을 입력하세요"
            )
            organization = st.text_input(
                "주관기관*", 
                placeholder="예: 중소벤처기업부",
                help="지원사업을 주관하는 기관명을 입력하세요"
            )
            category = st.selectbox(
                "지원분야*",
                ["기술개발", "사업화", "창업지원", "마케팅", "해외진출", "기타"],
                help="해당하는 지원 분야를 선택하세요"
            )
            deadline = st.date_input(
                "신청마감일*",
                help="지원자가 신청할 수 있는 마지막 날짜를 선택하세요"
            )
        
        with col2:
            st.markdown("#### 📋 추가 정보")
            budget = st.text_input(
                "지원금액", 
                placeholder="예: 최대 5천만원",
                help="지원 금액이나 지원 규모를 입력하세요"
            )
            region = st.text_input(
                "지역", 
                placeholder="예: 전국, 서울시 등",
                help="지원사업이 진행되는 지역을 입력하세요"
            )
            target_audience = st.text_input(
                "신청대상", 
                placeholder="예: 예비창업자, 초기창업자",
                help="지원사업의 신청 대상을 입력하세요"
            )
            contact = st.text_input(
                "문의처", 
                placeholder="예: 02-1234-5678",
                help="문의 가능한 연락처를 입력하세요"
            )
        
        description = st.text_area(
            "상세설명*",
            placeholder="지원사업의 목적, 내용, 신청방법 등을 자세히 입력하세요.",
            height=150
        )
        
        # 제출 버튼
        submit_button = st.form_submit_button("🚀 지원사업 생성", type="primary")
        
        if submit_button:
            # 필수 필드 검증
            required_fields = {
                "제목": title,
                "주관기관": organization,
                "지원분야": category,
                "신청마감일": deadline,
                "상세설명": description
            }
            
            missing_fields = [field for field, value in required_fields.items() if not value]
            
            if missing_fields:
                st.error(f"다음 필수 항목을 입력해주세요: {', '.join(missing_fields)}")
            else:
                try:
                    # 데이터 구성
                    new_announcement = {
                        "title": title,
                        "organization": organization,
                        "category": category,
                        "deadline": deadline.isoformat(),
                        "budget": budget or "정보 없음",
                        "region": region or "전국",
                        "target_audience": target_audience or "제한 없음",
                        "contact": contact or "정보 없음",
                        "description": description,
                        "status": "active",
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat()
                    }
                    
                    # 데이터 저장
                    success = data_handler.create_announcement(new_announcement)
                    
                    if success:
                        st.success("✅ 지원사업이 성공적으로 생성되었습니다!")
                        st.balloons()
                        
                        # 캐시 초기화
                        st.cache_data.clear()
                        
                        # 로깅
                        log_user_action("create_announcement", details={
                            "title": title,
                            "organization": organization
                        })
                        
                        # 3초 후 목록 페이지로 이동
                        st.info("3초 후 검색 페이지로 이동합니다...")
                        import time
                        time.sleep(3)
                        st.session_state.current_page = "지원사업 검색 및 필터링"
                        st.rerun()
                    else:
                        st.error("❌ 지원사업 생성 중 오류가 발생했습니다.")
                
                except Exception as e:
                    st.error(f"오류가 발생했습니다: {e}")
                    logger.error(f"지원사업 생성 실패: {e}")

# 3. 지원사업 검색 및 필터링 페이지
def render_search_page():
    """지원사업 검색 및 필터링 페이지 - 개선된 UX"""
    # 페이지 헤더
    st.title("🔍 지원사업 검색 및 관리")
    st.markdown("### 원하는 지원사업을 빠르게 찾고 관리하세요")
    
    # 데이터 로드
    with st.spinner("🔍 검색 데이터를 준비하는 중..."):
        df_announcements = load_announcements_data()
    
    if df_announcements.empty:
        st.warning("⚠️ 검색할 데이터가 없습니다")
        st.info("검색할 공고 데이터가 없습니다. 먼저 데이터를 수집해주세요.")
        return
    
    st.markdown("---")
    
    # 검색 및 필터 섹션 개선
    with st.expander("🔍 고급 검색 및 필터", expanded=True):
        # 검색어 입력
        col_search1, col_search2 = st.columns([3, 1])
        with col_search1:
            search_query = st.text_input(
                "🔎 통합 검색",
                value=st.session_state.search_query,
                placeholder="제목, 기관명, 내용, 지역, 분야 등으로 검색...",
                help="여러 키워드를 공백으로 구분하여 입력하세요"
            )
            st.session_state.search_query = search_query
        
        with col_search2:
            # 실시간 검색 토글
            real_time_search = st.checkbox("실시간 검색", value=True, help="입력과 동시에 검색 결과 업데이트")
        
        # 필터 섹션
        filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)
        
        with filter_col1:
            # 안전한 방식으로 카테고리 옵션 가져오기
            available_categories = []
            for col in ['category', 'support_field']:
                if col in df_announcements.columns:
                    categories = df_announcements[col].dropna().unique()
                    available_categories.extend(categories)
            available_categories = list(set(available_categories))
            selected_category = st.selectbox("📂 지원분야", ["전체"] + sorted(available_categories))
        
        with filter_col2:
            # 지역 필터
            available_regions = []
            if 'region' in df_announcements.columns:
                regions = df_announcements['region'].dropna().unique()
                available_regions = sorted(list(set(regions)))
            selected_region = st.selectbox("📍 지역", ["전체"] + available_regions)
        
        with filter_col3:
            # 상태 필터
            status_options = ["전체", "진행중", "마감", "마감임박"]
            selected_status = st.selectbox("📅 상태", status_options)
        
        with filter_col4:
            # 기관 필터
            available_orgs = []
            for col in ['organization', 'org_name_ref']:
                if col in df_announcements.columns:
                    orgs = df_announcements[col].dropna().unique()
                    available_orgs.extend(orgs)
            available_orgs = sorted(list(set(available_orgs)))[:20]  # 상위 20개만
            selected_org = st.selectbox("🏢 주관기관", ["전체"] + available_orgs)
        
        # 추가 필터
        adv_filter_col1, adv_filter_col2, adv_filter_col3 = st.columns(3)
        
        with adv_filter_col1:
            # 날짜 필터
            date_filter = st.selectbox("📅 마감일 필터", [
                "전체", "오늘", "1주일 이내", "1개월 이내", "3개월 이내", "만료된 공고"
            ])
        
        with adv_filter_col2:
            # 대상 필터
            target_options = []
            if 'target_audience' in df_announcements.columns:
                targets = df_announcements['target_audience'].dropna().str.split(',').explode().str.strip().unique()
                target_options = sorted([t for t in targets if t and len(t) > 1])[:15]
            selected_target = st.selectbox("🎯 신청대상", ["전체"] + target_options)
        
        with adv_filter_col3:
            # 결과 수 제한
            max_results = st.selectbox("📊 표시 개수", [10, 25, 50, 100, "전체"], index=2)
    
    # 검색 결과 필터링
    filtered_df = apply_advanced_filters(
        df_announcements, search_query, selected_category, selected_region, 
        selected_status, selected_org, date_filter, selected_target
    )
    
    # 정렬 및 결과 표시
    st.markdown("---")
    
    # 검색 결과 헤더
    result_col1, result_col2, result_col3 = st.columns([2, 1, 1])
    
    with result_col1:
        st.markdown(f"### 📋 검색 결과 ({len(filtered_df):,}개)")
        if search_query:
            st.caption(f"'{search_query}' 검색 결과")
    
    with result_col2:
        # 정렬 옵션
        sort_options = {
            "최신순": ("announcement_date", False),
            "제목순": ("title", True),
            "기관명순": ("organization", True),
            "마감일순": ("deadline", True)
        }
        sort_by = st.selectbox("정렬", list(sort_options.keys()))
        sort_column, ascending = sort_options[sort_by]
    
    with result_col3:
        # 보기 모드
        view_mode = st.selectbox("보기 모드", ["카드형", "테이블형", "간단형"])
    
    # 정렬 적용
    if sort_column in filtered_df.columns:
        filtered_df = filtered_df.sort_values(sort_column, ascending=ascending, na_position='last')
    
    # 결과 수 제한
    if max_results != "전체":
        display_df = filtered_df.head(max_results)
    else:
        display_df = filtered_df
    
    # 결과가 없을 때
    if display_df.empty:
        st.info("🔍 검색 조건에 맞는 지원사업이 없습니다.")
        st.markdown("""
        **검색 팁:**
        - 키워드를 더 간단하게 입력해보세요
        - 필터 조건을 조정해보세요
        - '전체' 옵션으로 필터를 초기화해보세요
        """)
        return
    
    # 결과 표시 모드별로 렌더링
    if view_mode == "카드형":
        render_card_view(display_df)
    elif view_mode == "테이블형":
        render_table_view(display_df)
    else:  # 간단형
        render_simple_view(display_df)
    
    # 검색 통계 및 액션
    st.markdown("---")
    
    stats_col1, stats_col2, stats_col3 = st.columns(3)
    
    with stats_col1:
        if st.button("📥 검색 결과 다운로드 (CSV)", help="현재 검색 결과를 CSV 파일로 다운로드"):
            csv_data = prepare_csv_download(display_df)
            st.download_button(
                label="💾 CSV 다운로드",
                data=csv_data,
                file_name=f"지원사업_검색결과_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
    
    with stats_col2:
        if st.button("🔄 필터 초기화", help="모든 검색 조건을 초기화"):
            st.session_state.search_query = ""
            st.rerun()
    
    with stats_col3:
        # 즐겨찾기 기능 (세션 상태로 간단 구현)
        if 'favorites' not in st.session_state:
            st.session_state.favorites = set()
        
        favorites_count = len(st.session_state.favorites)
        st.metric("⭐ 즐겨찾기", f"{favorites_count}개")
    
    # 사용자 액션 로깅
    log_user_action("search_announcements", details={
        "query": search_query, 
        "results": len(filtered_df),
        "filters": {
            "category": selected_category,
            "region": selected_region,
            "status": selected_status,
            "organization": selected_org
        }
    })

def apply_advanced_filters(df, search_query, category, region, status, organization, date_filter, target):
    """고급 필터링 적용"""
    filtered_df = df.copy()
    
    # 텍스트 검색 (향상된 검색)
    if search_query:
        search_terms = search_query.lower().split()
        text_columns = ['title', 'organization', 'description', 'org_name_ref', 'support_field', 'region', 'target_audience']
        
        mask = pd.Series([False] * len(filtered_df))
        
        for term in search_terms:
            term_mask = pd.Series([False] * len(filtered_df))
            for col in text_columns:
                if col in filtered_df.columns:
                    term_mask |= filtered_df[col].astype(str).str.lower().str.contains(term, na=False)
            mask |= term_mask
        
        filtered_df = filtered_df[mask]
    
    # 카테고리 필터
    if category != "전체":
        category_cols = ['category', 'support_field']
        for col in category_cols:
            if col in filtered_df.columns:
                filtered_df = filtered_df[filtered_df[col] == category]
                break
    
    # 지역 필터
    if region != "전체" and 'region' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['region'] == region]
    
    # 기관 필터
    if organization != "전체":
        org_cols = ['organization', 'org_name_ref']
        for col in org_cols:
            if col in filtered_df.columns:
                filtered_df = filtered_df[filtered_df[col] == organization]
                break
    
    # 대상 필터
    if target != "전체" and 'target_audience' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['target_audience'].str.contains(target, na=False)]
    
    # 날짜 필터
    if date_filter != "전체" and 'deadline' in filtered_df.columns:
        today = datetime.now()
        
        if date_filter == "오늘":
            filtered_df = filtered_df[
                pd.to_datetime(filtered_df['deadline'], errors='coerce').dt.date == today.date()
            ]
        elif date_filter == "1주일 이내":
            week_later = today + timedelta(days=7)
            filtered_df = filtered_df[
                (pd.to_datetime(filtered_df['deadline'], errors='coerce') >= today) &
                (pd.to_datetime(filtered_df['deadline'], errors='coerce') <= week_later)
            ]
        elif date_filter == "1개월 이내":
            month_later = today + timedelta(days=30)
            filtered_df = filtered_df[
                (pd.to_datetime(filtered_df['deadline'], errors='coerce') >= today) &
                (pd.to_datetime(filtered_df['deadline'], errors='coerce') <= month_later)
            ]
        elif date_filter == "3개월 이내":
            three_months_later = today + timedelta(days=90)
            filtered_df = filtered_df[
                (pd.to_datetime(filtered_df['deadline'], errors='coerce') >= today) &
                (pd.to_datetime(filtered_df['deadline'], errors='coerce') <= three_months_later)
            ]
        elif date_filter == "만료된 공고":
            filtered_df = filtered_df[
                pd.to_datetime(filtered_df['deadline'], errors='coerce') < today
            ]
    
    return filtered_df

def render_card_view(df):
    """카드형 보기 - 모든 상세 정보 표시"""
    st.markdown("### 📋 상세 카드 보기")
    
    for idx, row in df.iterrows():
        # 마감 상태 확인
        deadline_status = get_deadline_status(row.get('deadline', ''))
        status_color = get_status_color(deadline_status)
        
        # 카드 컨테이너
        with st.container():
            # 카드 헤더
            header_col1, header_col2, header_col3 = st.columns([3, 1, 1])
            
            with header_col1:
                title = row.get('title', '제목 없음')
                st.markdown(f"## 📢 {title}")
                
                # 상태 배지
                st.markdown(f"<span style='background-color: {status_color}; color: white; padding: 0.2rem 0.5rem; border-radius: 10px; font-size: 0.8rem;'>{deadline_status}</span>", unsafe_allow_html=True)
            
            with header_col2:
                # 즐겨찾기 버튼
                is_favorite = str(idx) in st.session_state.get('favorites', set())
                fav_icon = "⭐" if is_favorite else "☆"
                if st.button(f"{fav_icon} 즐겨찾기", key=f"fav_{idx}"):
                    if 'favorites' not in st.session_state:
                        st.session_state.favorites = set()
                    
                    if str(idx) in st.session_state.favorites:
                        st.session_state.favorites.remove(str(idx))
                        st.success("즐겨찾기에서 제거되었습니다!")
                    else:
                        st.session_state.favorites.add(str(idx))
                        st.success("즐겨찾기에 추가되었습니다!")
                    st.rerun()
            
            with header_col3:
                # 공유 버튼
                if st.button("📤 공유", key=f"share_{idx}"):
                    share_url = f"지원사업: {title}\n기관: {row.get('organization', row.get('org_name_ref', 'N/A'))}"
                    st.code(share_url, language=None)
                    st.success("공유 정보가 복사되었습니다!")
            
            # 기본 정보 섹션
            info_col1, info_col2 = st.columns(2)
            
            with info_col1:
                st.markdown("#### 📊 기본 정보")
                
                org_name = row.get('organization', row.get('org_name_ref', 'N/A'))
                st.markdown(f"**🏢 주관기관:** {org_name}")
                
                category = row.get('category', row.get('support_field', 'N/A'))
                st.markdown(f"**🎯 지원분야:** {category}")
                
                region = row.get('region', 'N/A')
                st.markdown(f"**📍 지역:** {region}")
                
                target = row.get('target_audience', 'N/A')
                st.markdown(f"**👥 신청대상:** {target}")
            
            with info_col2:
                st.markdown("#### 📅 일정 및 연락처")
                
                if 'deadline' in row and pd.notna(row['deadline']):
                    deadline_str = row['deadline'].strftime('%Y-%m-%d') if hasattr(row['deadline'], 'strftime') else str(row['deadline'])
                    st.markdown(f"**⏰ 마감일:** {deadline_str}")
                else:
                    st.markdown("**⏰ 마감일:** 정보 없음")
                
                announcement_date = row.get('announcement_date', 'N/A')
                if announcement_date != 'N/A' and pd.notna(announcement_date):
                    if hasattr(announcement_date, 'strftime'):
                        announcement_date = announcement_date.strftime('%Y-%m-%d')
                st.markdown(f"**📅 공고일:** {announcement_date}")
                
                contact = row.get('contact', row.get('inquiry', 'N/A'))
                st.markdown(f"**📞 문의처:** {contact}")
                
                budget = row.get('support_content', row.get('budget', 'N/A'))
                if len(str(budget)) > 50:
                    budget = str(budget)[:50] + "..."
                st.markdown(f"**💰 지원내용:** {budget}")
            
            # 상세 설명 섹션
            st.markdown("#### 📝 상세 설명")
            description = row.get('description', '상세 설명이 없습니다.')
            
            # 설명이 너무 길면 접기/펼치기 기능
            if len(description) > 300:
                with st.expander("📖 전체 설명 보기", expanded=False):
                    st.markdown(description)
                st.markdown(f"{description[:300]}...")
            else:
                st.markdown(description)
            
            # 신청 정보 섹션
            app_col1, app_col2 = st.columns(2)
            
            with app_col1:
                st.markdown("#### 📋 신청 방법")
                app_method = row.get('application_method', 'N/A')
                if app_method != 'N/A' and pd.notna(app_method):
                    if isinstance(app_method, list):
                        for method in app_method:
                            st.markdown(f"• {method}")
                    else:
                        st.markdown(app_method)
                else:
                    st.markdown("신청방법 정보가 없습니다.")
            
            with app_col2:
                st.markdown("#### 📄 제출 서류")
                documents = row.get('submission_documents', 'N/A')
                if documents != 'N/A' and pd.notna(documents):
                    st.markdown(documents)
                else:
                    st.markdown("제출서류 정보가 없습니다.")
            
            # 액션 버튼
            action_col1, action_col2, action_col3, action_col4 = st.columns(4)
            
            with action_col1:
                if st.button("✏️ 수정", key=f"edit_{idx}"):
                    edit_announcement(str(idx), row)
            
            with action_col2:
                if st.button("🗑️ 삭제", key=f"delete_{idx}", type="secondary"):
                    if st.session_state.get(f"confirm_delete_{idx}", False):
                        success = data_handler.delete_announcement(str(idx))
                        if success:
                            st.success("삭제되었습니다.")
                            log_user_action("delete_announcement", details={"id": str(idx)})
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error("삭제 실패")
                    else:
                        st.session_state[f"confirm_delete_{idx}"] = True
                        st.warning("다시 클릭하면 삭제됩니다.")
            
            with action_col3:
                if st.button("📋 복사", key=f"copy_{idx}"):
                    # 공고 정보를 텍스트로 정리
                    copy_text = f"""
{title}
주관기관: {org_name}
지원분야: {category}
마감일: {deadline_str if 'deadline_str' in locals() else 'N/A'}
연락처: {contact}
                    """.strip()
                    st.code(copy_text, language=None)
                    st.success("공고 정보가 복사 가능한 형태로 표시되었습니다!")
            
            with action_col4:
                if st.button("🔗 링크", key=f"link_{idx}"):
                    # 외부 링크나 상세 페이지로 이동 (구현에 따라 조정)
                    st.info("원본 페이지 링크 기능은 추후 구현 예정입니다.")
            
            # 구분선
            st.markdown("---")

def render_table_view(df):
    """테이블형 보기"""
    st.markdown("### 📊 테이블 보기")
    
    # 표시할 컬럼 선택
    display_columns = ['title', 'organization', 'org_name_ref', 'support_field', 'category', 'region', 'deadline', 'target_audience']
    available_columns = [col for col in display_columns if col in df.columns]
    
    if available_columns:
        # 컬럼명 한글화
        column_mapping = {
            'title': '제목',
            'organization': '기관',
            'org_name_ref': '기관명',
            'support_field': '분야',
            'category': '카테고리',
            'region': '지역',
            'deadline': '마감일',
            'target_audience': '신청대상'
        }
        
        display_df = df[available_columns].copy()
        display_df.columns = [column_mapping.get(col, col) for col in available_columns]
        
        # 테이블 표시
        st.dataframe(
            display_df,
            use_container_width=True,
            height=600,
            column_config={
                "제목": st.column_config.TextColumn("제목", width="large"),
                "마감일": st.column_config.DateColumn("마감일"),
            }
        )
    else:
        st.error("표시할 수 있는 컬럼이 없습니다.")

def render_simple_view(df):
    """간단형 보기"""
    st.markdown("### 📝 간단 목록")
    
    for idx, row in df.head(50).iterrows():  # 성능을 위해 50개만 표시
        title = row.get('title', '제목 없음')
        org = row.get('organization', row.get('org_name_ref', '기관 정보 없음'))
        category = row.get('category', row.get('support_field', '분야 정보 없음'))
        
        deadline_status = get_deadline_status(row.get('deadline', ''))
        status_color = get_status_color(deadline_status)
        
        # 간단한 한 줄 표시
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        
        with col1:
            st.markdown(f"**{title}**")
        
        with col2:
            st.markdown(f"🏢 {org}")
        
        with col3:
            st.markdown(f"🎯 {category}")
        
        with col4:
            st.markdown(f"<span style='color: {status_color}; font-weight: bold;'>{deadline_status}</span>", unsafe_allow_html=True)

def get_deadline_status(deadline):
    """마감일 상태 확인"""
    if not deadline or pd.isna(deadline):
        return "정보없음"
    
    try:
        if hasattr(deadline, 'date'):
            deadline_date = deadline.date()
        else:
            deadline_date = pd.to_datetime(deadline).date()
        
        today = datetime.now().date()
        diff = (deadline_date - today).days
        
        if diff < 0:
            return "마감"
        elif diff == 0:
            return "오늘마감"
        elif diff <= 7:
            return f"D-{diff}"
        elif diff <= 30:
            return "진행중"
        else:
            return "진행중"
    
    except:
        return "정보없음"

def get_status_color(status):
    """상태별 색상 반환"""
    color_map = {
        "마감": "#dc3545",
        "오늘마감": "#fd7e14", 
        "진행중": "#28a745",
        "정보없음": "#6c757d"
    }
    
    # D-숫자 형태 처리
    if status.startswith("D-"):
        return "#ffc107"
    
    return color_map.get(status, "#6c757d")

def prepare_csv_download(df):
    """CSV 다운로드용 데이터 준비"""
    # 중요 컬럼만 선택하여 CSV 생성
    export_columns = ['title', 'organization', 'org_name_ref', 'support_field', 'category', 
                     'region', 'deadline', 'target_audience', 'description', 'contact']
    
    available_columns = [col for col in export_columns if col in df.columns]
    export_df = df[available_columns].copy()
    
    # 컬럼명 한글화
    column_mapping = {
        'title': '제목',
        'organization': '주관기관',
        'org_name_ref': '기관명',
        'support_field': '지원분야',
        'category': '카테고리',
        'region': '지역',
        'deadline': '마감일',
        'target_audience': '신청대상',
        'description': '상세설명',
        'contact': '연락처'
    }
    
    export_df.columns = [column_mapping.get(col, col) for col in available_columns]
    
    return export_df.to_csv(index=False, encoding='utf-8-sig')

# 4. 챗봇 페이지
def render_chatbot_page():
    """RAG 챗봇 페이지 - 메모리 기능 포함"""
    # 현재 시간 정보 가져오기
    from datetime import datetime, timezone, timedelta
    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst)
    
    current_time_info = {
        "current_date": now.strftime("%Y년 %m월 %d일"),
        "current_time": now.strftime("%H시 %M분"),
        "korean_day": ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"][now.weekday()]
    }
    
    # 페이지 헤더
    st.markdown(f"""
    <div style="text-align: center; padding: 2rem 0; background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%); 
                border-radius: 15px; margin-bottom: 1rem; color: white;">
        <h1 style="margin: 0; font-size: 2.5rem; font-weight: 800;">🤖 AI 지원사업 상담 챗봇</h1>
        <p style="margin: 0.5rem 0 0 0; font-size: 1.2rem; opacity: 0.9;">
            AI 기반 맞춤형 지원사업 정보 제공 및 상담 서비스 (대화 기억 기능)
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # 현재 시간 정보 표시
    st.markdown(f"""
    <div style="text-align: center; padding: 1rem; background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%); 
                border-radius: 10px; margin-bottom: 1.5rem; border: 1px solid #d1d5db;">
        <h3 style="margin: 0; color: #374151; font-size: 1.2rem;">
            📅 현재 시간: {current_time_info['current_date']} ({current_time_info['korean_day']}) {current_time_info['current_time']}
        </h3>
        <p style="margin: 0.5rem 0 0 0; color: #6b7280; font-size: 0.9rem;">
            ⏰ 마감일 기준으로 시의적절한 지원사업 정보를 제공합니다
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # RAG 시스템 초기화
    try:
        chatbot = get_rag_chatbot()
        system_status = chatbot.get_system_status()
        memory_status = chatbot.get_memory_status()
        
        # 시스템 상태 및 메모리 상태 표시
        status_col1, status_col2, status_col3, status_col4 = st.columns(4)
        
        with status_col1:
            if system_status.get('embedding_model_loaded', False):
                st.success("✅ 임베딩 모델")
            else:
                st.error("❌ 임베딩 모델")
        
        with status_col2:
            if system_status.get('pinecone_connected', False):
                st.success("✅ 벡터DB")
            else:
                st.warning("⚠️ 벡터DB")
        
        with status_col3:
            if system_status.get('openai_available', False):
                st.success("✅ AI 모델")
            else:
                st.warning("⚠️ AI 모델")
        
        with status_col4:
            memory_count = memory_status.get('total_conversations', 0)
            max_memory = memory_status.get('max_memory_turns', 5)
            if memory_count > 0:
                st.info(f"🧠 메모리 {memory_count}/{max_memory}")
            else:
                st.info("🧠 메모리 비어있음")
    
    except Exception as e:
        st.error(f"챗봇 시스템 초기화 실패: {e}")
        logger.error(f"챗봇 초기화 실패: {e}")
        return
    
    # 사용 가이드 및 메모리 관리
    guide_col, memory_col = st.columns([2, 1])
    
    with guide_col:
        with st.expander("💡 챗봇 사용 가이드", expanded=False):
            st.markdown("""
            **🧠 메모리 기능:**
            - 최근 5개 대화를 기억합니다
            - 이전 대화 내용을 참고하여 연속성 있는 답변을 제공합니다
            - 관심 분야나 조건을 기억하여 맞춤형 추천을 합니다
            
            **이런 질문을 해보세요:**
            - 🏢 "서울에서 진행하는 창업 지원사업이 있나요?"
            - 💰 "5천만원 이하 지원금을 받을 수 있는 사업은?"
            - 🎯 "IT 분야 예비창업자에게 맞는 프로그램은?"
            - 📅 "이번 달 마감인 지원사업을 알려주세요"
            - ⏰ "마감이 임박한 지원사업은 어떤 것들이 있나요?"
            - 🚨 "오늘 마감인 지원사업이 있나요?"
            - ✅ "아직 신청 가능한 지원사업을 추천해주세요"
            - 🔄 "앞서 말한 조건에 맞는 다른 사업도 있나요?"
            
            **AI 답변 품질 향상 팁:**
            - 구체적인 조건을 포함해 질문하세요
            - 지역, 분야, 금액 등 세부 정보를 제공하세요
            - 이전 대화를 참조하여 추가 질문 가능합니다
            """)
    
    with memory_col:
        st.markdown("#### 🧠 대화 메모리 관리")
        
        # 메모리 상태 표시
        if memory_status.get('total_conversations', 0) > 0:
            st.markdown(f"**기억 중인 대화:** {memory_status['memory_usage']}")
            
            # 대화 요약 표시
            if st.button("📋 대화 요약 보기"):
                summary = chatbot.get_conversation_summary()
                st.text_area("대화 요약", summary, height=150, disabled=True)
        else:
            st.info("아직 기억하고 있는 대화가 없습니다.")
        
        # 메모리 초기화 버튼
        if st.button("🗑️ 대화 기록 초기화", help="모든 대화 기록을 삭제합니다"):
            if st.session_state.get('confirm_memory_clear', False):
                chatbot.clear_conversation_memory()
                st.session_state.chatbot_messages = []
                st.success("대화 기록이 초기화되었습니다!")
                st.session_state.confirm_memory_clear = False
                st.rerun()
            else:
                st.session_state.confirm_memory_clear = True
                st.warning("다시 클릭하면 모든 대화 기록이 삭제됩니다.")
    
    st.markdown("---")
    
    # 채팅 기록 표시
    chat_container = st.container()
    
    # 세션 상태에서 채팅 기록 가져오기
    if 'chatbot_messages' not in st.session_state:
        st.session_state.chatbot_messages = []
    
    # 채팅 기록 표시
    with chat_container:
        for i, message in enumerate(st.session_state.chatbot_messages):
            with st.chat_message(message["role"]):
                st.write(message["content"])
                
                # 소스 정보 표시 (assistant 메시지의 경우)
                if message["role"] == "assistant" and "sources" in message:
                    sources = message["sources"]
                    confidence = message.get("confidence", 0.0)
                    memory_used = message.get("memory_used", False)
                    applicable_count = message.get("applicable_count", 0)
                    urgent_count = message.get("urgent_count", 0)
                    total_results = message.get("total_results", 0)
                    
                    # 신청 가능 여부 통계 표시
                    if total_results > 0:
                        st.markdown("---")
                        stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)
                        
                        with stats_col1:
                            st.metric("📊 검색 결과", f"{total_results}개")
                        
                        with stats_col2:
                            if applicable_count > 0:
                                st.metric("✅ 신청 가능", f"{applicable_count}개", delta="추천")
                            else:
                                st.metric("❌ 신청 가능", "0개", delta="없음")
                        
                        with stats_col3:
                            if urgent_count > 0:
                                st.metric("🚨 긴급 마감", f"{urgent_count}개", delta="주의")
                            else:
                                st.metric("⏰ 긴급 마감", "0개")
                        
                        with stats_col4:
                            expired_count = total_results - applicable_count
                            if expired_count > 0:
                                st.metric("❌ 마감됨", f"{expired_count}개", delta="참고용")
                            else:
                                st.metric("❌ 마감됨", "0개")
                    
                    # 메타 정보 표시
                    meta_col1, meta_col2, meta_col3 = st.columns(3)
                    
                    with meta_col1:
                        if confidence > 0:
                            confidence_color = "green" if confidence > 0.7 else "orange" if confidence > 0.4 else "red"
                            st.markdown(f"**신뢰도:** :{confidence_color}[{confidence:.1%}]")
                    
                    with meta_col2:
                        if memory_used:
                            st.markdown("🧠 **메모리 활용됨**")
                    
                    with meta_col3:
                        if sources:
                            st.markdown(f"📚 **참고자료:** {len(sources)}개")
                    
                    # 소스 정보 상세 표시
                    if sources:
                        with st.expander("📚 참고 자료 상세"):
                            for j, source in enumerate(sources[:3]):  # 상위 3개만 표시
                                st.write(f"**{j+1}. {source.get('title', '제목 없음')}**")
                                st.write(f"   🏢 기관: {source.get('organization', 'N/A')}")
                                st.write(f"   📊 유사도: {source.get('score', 0):.2f}")
                                if j < len(sources) - 1:
                                    st.write("---")
    
    # 채팅 입력
    if prompt := st.chat_input("지원사업에 대해 질문하세요... (이전 대화를 기억합니다!)"):
        # 사용자 메시지 추가
        st.session_state.chatbot_messages.append({"role": "user", "content": prompt})
        
        # 사용자 메시지 즉시 표시
        with st.chat_message("user"):
            st.write(prompt)
        
        # AI 응답 생성
        with st.chat_message("assistant"):
            with st.spinner("🧠 이전 대화를 참고하여 답변을 생성하고 있습니다..."):
                try:
                    response_data = chatbot.get_response(prompt)
                    
                    answer = response_data.get("answer", "죄송합니다. 답변을 생성할 수 없습니다.")
                    sources = response_data.get("sources", [])
                    confidence = response_data.get("confidence", 0.0)
                    memory_used = response_data.get("memory_used", False)
                    applicable_count = response_data.get("applicable_count", 0)
                    urgent_count = response_data.get("urgent_count", 0)
                    total_results = response_data.get("total_results", 0)
                    
                    # 답변 표시
                    st.write(answer)
                    
                    # 신청 가능 여부 통계 표시
                    if total_results > 0:
                        st.markdown("---")
                        stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)
                        
                        with stats_col1:
                            st.metric("📊 검색 결과", f"{total_results}개")
                        
                        with stats_col2:
                            if applicable_count > 0:
                                st.metric("✅ 신청 가능", f"{applicable_count}개", delta="추천")
                            else:
                                st.metric("❌ 신청 가능", "0개", delta="없음")
                        
                        with stats_col3:
                            if urgent_count > 0:
                                st.metric("🚨 긴급 마감", f"{urgent_count}개", delta="주의")
                            else:
                                st.metric("⏰ 긴급 마감", "0개")
                        
                        with stats_col4:
                            expired_count = total_results - applicable_count
                            if expired_count > 0:
                                st.metric("❌ 마감됨", f"{expired_count}개", delta="참고용")
                            else:
                                st.metric("❌ 마감됨", "0개")
                    
                    # 메타 정보 표시
                    meta_col1, meta_col2, meta_col3 = st.columns(3)
                    
                    with meta_col1:
                        if confidence > 0:
                            confidence_color = "green" if confidence > 0.7 else "orange" if confidence > 0.4 else "red"
                            st.markdown(f"**신뢰도:** :{confidence_color}[{confidence:.1%}]")
                    
                    with meta_col2:
                        if memory_used:
                            st.markdown("🧠 **메모리 활용됨**")
                        else:
                            st.markdown("🆕 **새로운 대화**")
                    
                    with meta_col3:
                        if sources:
                            st.markdown(f"📚 **참고자료:** {len(sources)}개")
                    
                    # 소스 정보 표시
                    if sources:
                        with st.expander("📚 참고 자료 상세"):
                            for i, source in enumerate(sources[:3]):
                                st.write(f"**{i+1}. {source.get('title', '제목 없음')}**")
                                st.write(f"   🏢 기관: {source.get('organization', 'N/A')}")
                                st.write(f"   📊 유사도: {source.get('score', 0):.2f}")
                                if i < len(sources) - 1:
                                    st.write("---")
                    
                    # 세션에 assistant 메시지 추가 (메타데이터 포함)
                    st.session_state.chatbot_messages.append({
                        "role": "assistant", 
                        "content": answer,
                        "sources": sources,
                        "confidence": confidence,
                        "memory_used": memory_used,
                        "applicable_count": applicable_count,
                        "urgent_count": urgent_count,
                        "total_results": total_results
                    })
                    
                except Exception as e:
                    error_msg = f"죄송합니다. 오류가 발생했습니다: {str(e)}"
                    st.error(error_msg)
                    st.session_state.chatbot_messages.append({
                        "role": "assistant", 
                        "content": error_msg
                    })
                    logger.error(f"챗봇 응답 생성 실패: {e}")
    
    # 페이지 하단 통계
    st.markdown("---")
    
    stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)
    
    with stats_col1:
        total_messages = len(st.session_state.chatbot_messages)
        st.metric("💬 총 대화 수", f"{total_messages}개")
    
    with stats_col2:
        user_messages = len([m for m in st.session_state.chatbot_messages if m["role"] == "user"])
        st.metric("❓ 질문 수", f"{user_messages}개")
    
    with stats_col3:
        memory_conversations = memory_status.get('total_conversations', 0)
        st.metric("🧠 기억 중인 대화", f"{memory_conversations}개")
    
    with stats_col4:
        if memory_status.get('latest_conversation'):
            latest_time = memory_status['latest_conversation'][:19]  # YYYY-MM-DD HH:MM:SS
            st.metric("🕐 마지막 대화", latest_time.split('T')[1])
        else:
            st.metric("🕐 마지막 대화", "없음")

def edit_announcement(announcement_id: str, current_data):
    """공고 수정 폼 - 개선된 UI"""
    st.markdown("---")
    st.markdown(f"### ✏️ 공고 수정: {current_data.get('title', '제목없음')}")
    
    with st.form(f"edit_form_{announcement_id}"):
        # 기본 정보 섹션
        st.markdown("#### 📊 기본 정보")
        edit_col1, edit_col2 = st.columns(2)
        
        with edit_col1:
            new_title = st.text_input(
                "제목 *", 
                value=current_data.get('title', ''),
                help="지원사업의 제목을 입력하세요"
            )
            new_organization = st.text_input(
                "주관기관 *", 
                value=current_data.get('organization', current_data.get('org_name_ref', '')),
                help="주관기관명을 입력하세요"
            )
            new_category = st.text_input(
                "지원분야", 
                value=current_data.get('category', current_data.get('support_field', '')),
                help="지원분야를 입력하세요 (예: IT/SW, 바이오, 제조업)"
            )
        
        with edit_col2:
            new_region = st.text_input(
                "지역", 
                value=current_data.get('region', ''),
                help="지역 정보를 입력하세요"
            )
            new_target = st.text_input(
                "신청대상", 
                value=current_data.get('target_audience', ''),
                help="신청 가능한 대상을 입력하세요"
            )
            
            # 마감일 입력
            deadline_value = current_data.get('deadline', '')
            if deadline_value and pd.notna(deadline_value):
                if hasattr(deadline_value, 'date'):
                    deadline_value = deadline_value.date()
                else:
                    try:
                        deadline_value = pd.to_datetime(deadline_value).date()
                    except:
                        deadline_value = None
            else:
                deadline_value = None
            
            new_deadline = st.date_input(
                "마감일", 
                value=deadline_value,
                help="지원사업 마감일을 선택하세요"
            )
        
        # 연락처 및 지원내용 섹션
        st.markdown("#### 📞 연락처 및 지원내용")
        contact_col1, contact_col2 = st.columns(2)
        
        with contact_col1:
            new_contact = st.text_area(
                "연락처", 
                value=current_data.get('contact', current_data.get('inquiry', '')),
                height=100,
                help="담당자 연락처나 문의처를 입력하세요"
            )
        
        with contact_col2:
            new_support_content = st.text_area(
                "지원내용", 
                value=current_data.get('support_content', current_data.get('budget', '')),
                height=100,
                help="지원금액, 지원내용 등을 입력하세요"
            )
        
        # 상세 설명 섹션
        st.markdown("#### 📝 상세 설명")
        new_description = st.text_area(
            "상세설명", 
            value=current_data.get('description', ''),
            height=200,
            help="지원사업에 대한 상세한 설명을 입력하세요"
        )
        
        # 신청 정보 섹션
        st.markdown("#### 📋 신청 정보")
        app_info_col1, app_info_col2 = st.columns(2)
        
        with app_info_col1:
            new_app_method = st.text_area(
                "신청방법", 
                value=current_data.get('application_method', ''),
                height=100,
                help="신청방법과 절차를 입력하세요"
            )
        
        with app_info_col2:
            new_documents = st.text_area(
                "제출서류", 
                value=current_data.get('submission_documents', ''),
                height=100,
                help="필요한 제출서류를 입력하세요"
            )
        
        # 제출 버튼
        submit_col1, submit_col2, submit_col3 = st.columns([1, 1, 2])
        
        with submit_col1:
            if st.form_submit_button("💾 수정 저장", type="primary"):
                # 입력 검증
                if not new_title.strip():
                    st.error("❌ 제목은 필수 입력 항목입니다.")
                elif not new_organization.strip():
                    st.error("❌ 주관기관은 필수 입력 항목입니다.")
                else:
                    try:
                        updated_data = {
                            "title": new_title.strip(),
                            "organization": new_organization.strip(),
                            "org_name_ref": new_organization.strip(),
                            "category": new_category.strip(),
                            "support_field": new_category.strip(),
                            "region": new_region.strip(),
                            "target_audience": new_target.strip(),
                            "deadline": new_deadline.isoformat() if new_deadline else None,
                            "contact": new_contact.strip(),
                            "inquiry": new_contact.strip(),
                            "support_content": new_support_content.strip(),
                            "budget": new_support_content.strip(),
                            "description": new_description.strip(),
                            "application_method": new_app_method.strip(),
                            "submission_documents": new_documents.strip(),
                            "updated_at": datetime.now().isoformat()
                        }
                        
                        success = data_handler.update_announcement(announcement_id, updated_data)
                        
                        if success:
                            st.success("✅ 수정이 완료되었습니다!")
                            log_user_action("update_announcement", details={
                                "id": announcement_id,
                                "title": new_title
                            })
                            st.cache_data.clear()
                            
                            # 3초 후 자동으로 페이지 새로고침
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error("❌ 수정 중 오류가 발생했습니다.")
                    
                    except Exception as e:
                        st.error(f"❌ 오류가 발생했습니다: {str(e)}")
                        logger.error(f"공고 수정 실패 - ID: {announcement_id}, Error: {e}")
        
        with submit_col2:
            if st.form_submit_button("❌ 취소", type="secondary"):
                st.info("수정이 취소되었습니다.")
                st.rerun()
        
        with submit_col3:
            st.caption("* 표시된 항목은 필수 입력 사항입니다.")

# 메인 애플리케이션
def main():
    """메인 애플리케이션 함수"""
    
    try:
        # 커스텀 스타일 적용
        apply_custom_styles()
        
        # 세션 상태 초기화
        initialize_session_state()
        
        # 사이드바 렌더링
        render_sidebar()
        
        # 현재 페이지에 따른 렌더링
        page = st.session_state.current_page
        logger.info(f"렌더링 중인 페이지: {page}")
        
        if page == "대시보드":
            render_dashboard_page()
        elif page == "신규 지원사업 생성":
            render_create_page()
        elif page == "지원사업 검색 및 필터링":
            render_search_page()
        elif page == "챗봇":
            render_chatbot_page()
        else:
            st.error(f"알 수 없는 페이지입니다: {page}")
            logger.warning(f"알 수 없는 페이지 요청: {page}")
            # 기본 페이지로 리다이렉트
            st.session_state.current_page = "대시보드"
            st.rerun()
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"메인 애플리케이션 오류: {error_msg}", exc_info=True)
        
        st.error("애플리케이션에서 오류가 발생했습니다.")
        st.exception(e)  # 상세한 오류 정보 표시
        
        # 안전한 기본 상태로 초기화
        with st.expander("🔧 문제 해결 옵션"):
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 페이지 새로고침"):
                    st.cache_data.clear()
                    st.session_state.clear()
                    st.rerun()
            with col2:
                if st.button("🏠 홈으로 돌아가기"):
                    st.session_state.current_page = "대시보드"
                    st.rerun()

if __name__ == "__main__":
    main() 