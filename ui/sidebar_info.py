"""
공통 사이드바 정보 컴포넌트
모든 페이지에서 사용되는 미니멀한 서비스 정보
"""

import streamlit as st
from utils.data_utils import load_announcements_data

def render_sidebar_info():
    """사이드바에 서비스 정보 표시"""
    
    # 데이터 현황
    st.sidebar.markdown("### 📊 데이터 현황")
    
    try:
        # 데이터 개수 조회
        df = load_announcements_data()
        data_count = len(df) if not df.empty else 0
        
        st.sidebar.metric(
            label="보유 지원사업",
            value=f"{data_count:,}개",
            delta="실시간 업데이트"
        )
        
        # 간단한 통계
        if not df.empty:
            unique_orgs = df['org_name_ref'].nunique() if 'org_name_ref' in df.columns else 0
            unique_fields = df['support_field'].nunique() if 'support_field' in df.columns else 0
            
            col1, col2 = st.sidebar.columns(2)
            with col1:
                st.metric("기관수", f"{unique_orgs}개")
            with col2:
                st.metric("분야수", f"{unique_fields}개")
    
    except Exception:
        st.sidebar.metric(
            label="보유 지원사업", 
            value="로딩중...",
            delta="데이터 수집중"
        )
    
    # 데이터 새로고침 버튼
    st.sidebar.markdown("### 🔄 데이터 관리")
    if st.sidebar.button("🔄 전체 데이터 새로고침", use_container_width=True, help="API에서 최신 데이터를 가져와 전체 시스템을 업데이트합니다"):
        # 세션 상태에 새로고침 플래그 설정
        st.session_state['trigger_refresh'] = True
        # 대시보드 페이지로 이동하여 새로고침 실행
        st.switch_page("_🏠대시보드.py")
    
    # 서비스 소개
    st.sidebar.markdown("### 🚀 주요 기능")
    st.sidebar.markdown("""
        - 📊 실시간 대시보드
    - 🔍 스마트 검색 & 필터
    - ➕ 신규 사업 등록
    - 🤖 AI 상담 챗봇
    """)
    
    # 팀 정보
    st.sidebar.markdown("### 👥 개발팀")
    st.sidebar.markdown("""    
    🎓 이흥규, 노건준(SKKU DSC)
    
    🌐 GitHub: [Group2](https://github.com/heungkyulee/dsc1)
    """)
    
    # 하단 정보
    st.sidebar.markdown("---")
    st.sidebar.caption("© 2025 SKKU DSC1 Group 2")
    st.sidebar.caption("Ver 1.0")

def render_quick_stats():
    """빠른 통계 정보 (선택적)"""
    try:
        df = load_announcements_data()
        if not df.empty:
            st.sidebar.markdown("### ⚡ 빠른 통계")
            
            # 최근 업데이트
            if 'announcement_date' in df.columns:
                latest_date = df['announcement_date'].max()
                st.sidebar.info(f"📅 최신 공고: {latest_date}")
            
            # 지역별 분포 (상위 3개)
            if 'region' in df.columns:
                top_regions = df['region'].value_counts().head(3)
                st.sidebar.markdown("**🌍 주요 지역**")
                for region, count in top_regions.items():
                    st.sidebar.caption(f"• {region}: {count}건")
    
    except Exception:
        pass  # 통계 로드 실패 시 무시 