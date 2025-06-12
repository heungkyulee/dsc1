"""
🏠 K-Startup 지원사업 관리 시스템 - 홈페이지 (대시보드)
Streamlit Multi-page 앱의 메인 대시보드
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

# 프로젝트 모듈 임포트
from config import config
from logger import get_logger, log_user_action

# UI 모듈 임포트
from ui.styles import apply_custom_styles
from ui.sidebar_info import render_sidebar_info

# 유틸리티 모듈 임포트
from utils.data_utils import initialize_session_state, load_announcements_data
from utils.ui_utils import get_deadline_status, get_status_color

# 데이터 수집 모듈 임포트
import crawler
import data_handler
from rag_system import ingest_announcements_to_pinecone

# 로거 설정
logger = get_logger(__name__)

# Streamlit 페이지 설정
st.set_page_config(
    page_title=f"🏠 {config.APP_TITLE}",
    layout=config.STREAMLIT_LAYOUT,
    initial_sidebar_state="expanded",
    page_icon="🏠",
    menu_items={
        'About': f"# {config.APP_TITLE}\n\n데이터 구조화 기반 지원사업 관리 시스템\n\n**주요 기능:**\n- 📊 실시간 대시보드\n- ➕ 신규 지원사업 생성\n- 🔍 고급 검색 및 필터링\n- 🤖 AI 챗봇 상담",
        'Report a bug': None,
        'Get Help': None
    }
)

@st.cache_data(ttl=300)  # 5분 캐시
def load_dashboard_metrics():
    """대시보드 메트릭 데이터 로드"""
    try:
        df = load_announcements_data()
        
        if df.empty:
            return {
                'total_count': 0,
                'active_count': 0,
                'expired_count': 0,
                'urgent_count': 0,
                'organizations': [],
                'categories': [],
                'latest_announcements': []
            }
        
        today = datetime.now()
        week_later = today + timedelta(days=7)
        
        # 기본 통계
        total_count = len(df)
        
        # 마감일 데이터 안전하게 처리
        deadline_series = None
        if 'deadline' in df.columns:
            deadline_series = pd.to_datetime(df['deadline'], errors='coerce')
        elif 'application_period' in df.columns:
            deadline_series = pd.to_datetime(df['application_period'], errors='coerce')
        
        if deadline_series is not None:
            active_count = len(df[deadline_series >= today])
            expired_count = len(df[deadline_series < today])
            urgent_count = len(df[
                (deadline_series >= today) &
                (deadline_series <= week_later)
            ])
        else:
            # 마감일 정보가 없을 때 기본값
            active_count = 0
            expired_count = 0
            urgent_count = 0
        
        # 기관별 분포
        org_columns = ['organization', 'org_name_ref']
        org_data = []
        for col in org_columns:
            if col in df.columns:
                org_counts = df[col].value_counts().head(10)
                org_data = [{'기관': idx, '공고수': val} for idx, val in org_counts.items()]
                break
        
        # 카테고리별 분포
        category_columns = ['category', 'support_field']
        category_data = []
        for col in category_columns:
            if col in df.columns:
                cat_counts = df[col].value_counts()
                category_data = [{'분야': idx, '공고수': val} for idx, val in cat_counts.items()]
                break
        
        # 최신 공고 (최대 5개)
        latest_df = df.copy()
        if 'created_at' in latest_df.columns:
            latest_df = latest_df.sort_values('created_at', ascending=False)
        elif 'announcement_date' in latest_df.columns:
            latest_df = latest_df.sort_values('announcement_date', ascending=False)
        
        latest_announcements = []
        for _, row in latest_df.head(5).iterrows():
            latest_announcements.append({
                'title': row.get('title', '제목 없음'),
                'organization': row.get('organization', row.get('org_name_ref', '기관 정보 없음')),
                'deadline': row.get('deadline', ''),
                'application_period': row.get('application_period', ''),
                'category': row.get('category', row.get('support_field', '분야 정보 없음'))
            })
        
        return {
            'total_count': total_count,
            'active_count': active_count,
            'expired_count': expired_count,
            'urgent_count': urgent_count,
            'organizations': org_data,
            'categories': category_data,
            'latest_announcements': latest_announcements
        }
    
    except Exception as e:
        logger.error(f"대시보드 메트릭 로드 실패: {e}")
        return {}

def create_category_chart(data):
    """카테고리별 분포 차트 생성"""
    if not data:
        return None
    
    df = pd.DataFrame(data)
    
    fig = px.pie(
        df, 
        values='공고수', 
        names='분야',
        title='📊 지원분야별 공고 분포',
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(
        height=400,
        showlegend=True,
        legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.01)
    )
    
    return fig

def create_organization_chart(data):
    """기관별 공고 수 차트 생성"""
    if not data:
        return None
    
    df = pd.DataFrame(data)
    
    fig = px.bar(
        df, 
        x='공고수', 
        y='기관',
        orientation='h',
        title='🏢 주관기관별 공고 현황 (상위 10개)',
        color='공고수',
        color_continuous_scale='Blues'
    )
    
    fig.update_layout(
        height=400,
        yaxis={'categoryorder': 'total ascending'},
        showlegend=False
    )
    
    return fig

def render_welcome_section():
    """환영 메시지 섹션"""
    current_time = datetime.now()
    
    # 시간대별 인사말
    if current_time.hour < 12:
        greeting = "좋은 아침입니다! ☀️"
    elif current_time.hour < 18:
        greeting = "좋은 오후입니다! 🌤️"
    else:
        greeting = "좋은 저녁입니다! 🌙"
    
    st.markdown(f"""
    <div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                border-radius: 15px; margin-bottom: 2rem; color: white;">
        <h1 style="margin: 0; font-size: 2.5rem;">🚀 K-Startup 지원사업 관리 시스템</h1>
        <h3 style="margin: 0.5rem 0; font-weight: 300;">{greeting}</h3>
        <p style="margin: 1rem 0; font-size: 1.1rem; opacity: 0.9;">
            창업 생태계의 모든 지원사업 정보를 한 곳에서 관리하세요
        </p>
        <p style="margin: 0; font-size: 0.9rem; opacity: 0.8;">
            📅 {current_time.strftime('%Y년 %m월 %d일 %A')}
        </p>
    </div>
    """, unsafe_allow_html=True)

def refresh_all_data():
    """전체 데이터 새로고침 - API 호출부터 Pinecone 업데이트까지"""
    try:
        with st.spinner("🔄 데이터 새로고침을 시작합니다..."):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # 1단계: API에서 최신 데이터 수집
            status_text.text("1/4 단계: 공공데이터포털 API에서 최신 데이터 수집 중...")
            progress_bar.progress(25)
            
            try:
                crawler.collect_data()
                st.success("✅ API 데이터 수집 완료")
            except Exception as e:
                st.warning(f"⚠️ API 데이터 수집 중 오류: {str(e)}")
                logger.warning(f"API 데이터 수집 실패: {e}")
            
            # 2단계: 로컬 JSON 데이터 처리
            status_text.text("2/4 단계: 수집된 데이터를 내부 형식으로 처리 중...")
            progress_bar.progress(50)
            
            try:
                data_handler.process_raw_data()
                st.success("✅ 데이터 처리 완료")
            except Exception as e:
                st.warning(f"⚠️ 데이터 처리 중 오류: {str(e)}")
                logger.warning(f"데이터 처리 실패: {e}")
            
            # 3단계: Pinecone 벡터 데이터베이스 업데이트
            status_text.text("3/4 단계: AI 챗봇용 벡터 데이터베이스 업데이트 중...")
            progress_bar.progress(75)
            
            try:
                announcements = data_handler.get_all_announcements()
                if announcements:
                    success, message = ingest_announcements_to_pinecone(announcements)
                    if success:
                        st.success("✅ 벡터 데이터베이스 업데이트 완료")
                    else:
                        st.warning(f"⚠️ 벡터 데이터베이스 업데이트 실패: {message}")
                else:
                    st.warning("⚠️ 업데이트할 공고 데이터가 없습니다")
            except Exception as e:
                st.warning(f"⚠️ 벡터 데이터베이스 업데이트 중 오류: {str(e)}")
                logger.warning(f"Pinecone 업데이트 실패: {e}")
            
            # 4단계: 캐시 클리어 및 완료
            status_text.text("4/4 단계: 캐시 클리어 및 마무리 중...")
            progress_bar.progress(100)
            
            st.cache_data.clear()
            
            # 완료 메시지
            progress_bar.empty()
            status_text.empty()
            
            st.success("🎉 데이터 새로고침이 완료되었습니다!")
            st.info("📊 최신 데이터가 반영되었습니다. 페이지가 자동으로 새로고침됩니다.")
            
            # 사용자 액션 로깅
            log_user_action("refresh_all_data", details={
                "timestamp": datetime.now().isoformat(),
                "success": True
            })
            
            time.sleep(2)  # 사용자가 메시지를 볼 시간 제공
            st.rerun()
            
    except Exception as e:
        st.error(f"❌ 데이터 새로고침 중 오류가 발생했습니다: {str(e)}")
        logger.error(f"데이터 새로고침 실패: {e}")
        
        # 실패 시에도 캐시는 클리어
        st.cache_data.clear()
        
        # 실패 로깅
        log_user_action("refresh_all_data", details={
            "timestamp": datetime.now().isoformat(),
            "success": False,
            "error": str(e)
        })

def render_quick_actions():
    """빠른 액션 버튼들"""
    st.markdown("### 🚀 빠른 액션")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("➕ 신규 지원사업 생성", type="primary", use_container_width=True):
            st.switch_page("pages/1_➕_신규_지원사업_생성.py")
    
    with col2:
        if st.button("🔍 지원사업 검색", use_container_width=True):
            st.switch_page("pages/2_🔍_지원사업_검색_및_필터링.py")
    
    with col3:
        if st.button("🤖 AI 챗봇 상담", use_container_width=True):
            st.switch_page("pages/3_🤖_AI_챗봇.py")
    
    with col4:
        if st.button("🔄 데이터 새로고침", use_container_width=True):
            refresh_all_data()

def render_latest_announcements(announcements):
    """최신 공고 섹션"""
    st.markdown("### 📢 최신 지원사업 공고")
    
    if not announcements:
        st.info("표시할 최신 공고가 없습니다.")
        return
    
    for i, announcement in enumerate(announcements):
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.markdown(f"**{announcement['title']}**")
                st.caption(f"🏢 {announcement['organization']}")
            
            with col2:
                st.markdown(f"🎯 {announcement['category']}")
            
            with col3:
                deadline = announcement.get('deadline', '')
                application_period = announcement.get('application_period', '')
                
                if deadline and deadline != '날짜 정보 없음':
                    deadline_status = get_deadline_status(deadline, application_period)
                    status_color = get_status_color(deadline_status)
                    st.markdown(f"<span style='color: {status_color}; font-weight: bold;'>{deadline_status}</span>", unsafe_allow_html=True)
                elif application_period:
                    deadline_status = get_deadline_status(None, application_period)
                    status_color = get_status_color(deadline_status)
                    st.markdown(f"<span style='color: {status_color}; font-weight: bold;'>{deadline_status}</span>", unsafe_allow_html=True)
                else:
                    st.markdown("📅 미정")
            
            if i < len(announcements) - 1:
                st.divider()

def main():
    """메인 대시보드 함수"""
    try:
        # 커스텀 스타일 적용
        apply_custom_styles()
        
        # 세션 상태 초기화
        initialize_session_state()
        
        # 사이드바에서 새로고침 요청이 있는지 확인
        if st.session_state.get('trigger_refresh', False):
            st.session_state['trigger_refresh'] = False  # 플래그 리셋
            refresh_all_data()
            return  # 새로고침 후 함수 종료
        
        # 환영 섹션
        render_welcome_section()
        
        # 빠른 액션 버튼
        render_quick_actions()
        
        st.markdown("---")
        
        # 대시보드 메트릭 로드
        with st.spinner("📊 대시보드 데이터를 불러오는 중..."):
            metrics = load_dashboard_metrics()
        
        if not metrics:
            st.error("대시보드 데이터를 불러올 수 없습니다.")
            return
        
        # 주요 메트릭 표시
        st.markdown("### 📊 주요 지표")
        
        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
        
        with metric_col1:
            st.metric(
                label="📋 전체 지원사업",
                value=f"{metrics.get('total_count', 0):,}개",
                delta=None
            )
        
        with metric_col2:
            st.metric(
                label="✅ 진행중인 공고",
                value=f"{metrics.get('active_count', 0):,}개",
                delta=None
            )
        
        with metric_col3:
            st.metric(
                label="⚠️ 마감임박 (1주일)",
                value=f"{metrics.get('urgent_count', 0):,}개",
                delta=None
            )
        
        with metric_col4:
            st.metric(
                label="❌ 마감된 공고",
                value=f"{metrics.get('expired_count', 0):,}개",
                delta=None
            )
        
        st.markdown("---")
        
        # 차트 섹션
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            if metrics.get('categories'):
                category_chart = create_category_chart(metrics['categories'])
                if category_chart:
                    st.plotly_chart(category_chart, use_container_width=True)
            else:
                st.info("카테고리별 분포 데이터가 없습니다.")
        
        with chart_col2:
            if metrics.get('organizations'):
                org_chart = create_organization_chart(metrics['organizations'])
                if org_chart:
                    st.plotly_chart(org_chart, use_container_width=True)
            else:
                st.info("기관별 분포 데이터가 없습니다.")
        
        st.markdown("---")
        
        # 최신 공고 섹션
        render_latest_announcements(metrics.get('latest_announcements', []))
        
        # 하단 정보
        st.markdown("---")
        st.markdown("### 💡 시스템 정보")
        
        info_col1, info_col2, info_col3 = st.columns(3)
        
        with info_col1:
            st.markdown("""
            **📈 실시간 업데이트**
            - 5분마다 자동 새로고침
            - K-Startup API 연동
            - 실시간 상태 모니터링
            """)
        
        with info_col2:
            st.markdown("""
            **🔍 고급 기능**
            - 다중 키워드 검색
            - 스마트 필터링
            - 카테고리별 분류
            """)
        
        with info_col3:
            st.markdown("""
            **🤖 AI 지원**
            - RAG 기반 챗봇
            - 맞춤형 추천
            - 자연어 질의응답
            """)
        
        # 사용자 액션 로깅
        log_user_action("view_dashboard", details={
            "total_announcements": metrics.get('total_count', 0),
            "active_announcements": metrics.get('active_count', 0)
        })
        
        # 사이드바 정보 렌더링
        render_sidebar_info()
    
    except Exception as e:
        logger.error(f"대시보드 페이지 오류: {e}")
        st.error("대시보드 로드 중 오류가 발생했습니다.")
        st.exception(e)

if __name__ == "__main__":
    main() 