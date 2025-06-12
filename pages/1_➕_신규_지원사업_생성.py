"""
신규 지원사업 생성 페이지
Streamlit Multi-page 앱의 신규 생성 기능
"""

import streamlit as st
from datetime import datetime
import time

# 프로젝트 모듈 임포트
from config import config
from logger import get_logger, log_user_action
import data_handler

# UI 모듈 임포트
from ui.styles import apply_custom_styles
from ui.sidebar_info import render_sidebar_info

# 유틸리티 모듈 임포트
from utils.data_utils import initialize_session_state

# 로거 설정
logger = get_logger(__name__)

# Streamlit 페이지 설정
st.set_page_config(
    page_title="신규 지원사업 생성 - K-Startup 관리 시스템",
    layout=config.STREAMLIT_LAYOUT,
    page_icon="➕",
    menu_items={
        'About': f"# {config.APP_TITLE}\n\n신규 지원사업 생성 페이지",
        'Report a bug': None,
        'Get Help': None
    }
)

def main():
    """신규 지원사업 생성 페이지 메인 함수"""
    try:
        # 커스텀 스타일 적용
        apply_custom_styles()
        
        # 세션 상태 초기화
        initialize_session_state()
        
        # 페이지 헤더
        st.title("➕ 신규 지원사업 생성")
        
        # 도움말 섹션
        # with st.expander("📝 작성 가이드", expanded=False):
        #     st.markdown("""
        #     **필수 입력 항목** (⭐ 표시)
        #     - **제목**: 명확하고 간결한 지원사업명
        #     - **주관기관**: 지원사업을 주관하는 기관명
        #     - **지원분야**: 해당하는 지원 분야 선택
        #     - **신청마감일**: 지원자가 신청할 수 있는 마지막 날짜
        #     - **상세설명**: 지원사업의 목적, 내용, 신청방법 등
            
        #     **작성 팁**
        #     - 📋 명확하고 구체적인 정보 제공
        #     - 🎯 지원 대상을 명확히 기술
        #     - 💰 지원 금액과 조건을 상세히 설명
        #     - 📞 문의처 정보를 정확히 입력
        #     """)
        
        # st.markdown("---")
        
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
                    # 진행 상태 표시
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    try:
                        # 1단계: 데이터 구성
                        status_text.text("📝 데이터 구성 중...")
                        progress_bar.progress(25)
                        
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
                        
                        # 2단계: JSON 파일 저장
                        status_text.text("💾 JSON 파일에 저장 중...")
                        progress_bar.progress(50)
                        
                        success = data_handler.add_contest(new_announcement)
                        
                        if success:
                            # 3단계: Pinecone 업데이트 (add_contest 함수 내부에서 자동 처리)
                            status_text.text("🔄 AI 검색 시스템 업데이트 중...")
                            progress_bar.progress(75)
                            
                            # 4단계: 완료
                            status_text.text("✅ 생성 완료!")
                            progress_bar.progress(100)
                            
                            # 성공 메시지
                            st.success("✅ 지원사업이 성공적으로 생성되었습니다!")
                            st.balloons()
                            
                            # 캐시 초기화
                            if hasattr(st, 'cache_data'):
                                st.cache_data.clear()
                            
                            # 로깅
                            log_user_action("create_announcement", details={
                                "title": title,
                                "organization": organization,
                                "id": new_announcement.get('pblancId', 'unknown')
                            })
                            
                            # 성공 후 정보
                            with st.container():
                                st.markdown("---")
                                st.markdown("### 🎉 생성 완료!")
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.info("💡 **다음 단계:**\n- 왼쪽 사이드바에서 '🔍 지원사업 검색 및 필터링' 페이지로 이동하여 생성된 지원사업을 확인할 수 있습니다.")
                                
                                with col2:
                                    st.success("🤖 **AI 챗봇 지원:**\n- '🤖 AI 챗봇' 페이지에서 생성한 지원사업에 대해 질문할 수 있습니다.")
                        
                        else:
                            status_text.text("❌ 저장 실패")
                            progress_bar.progress(0)
                            st.error("❌ 지원사업 생성 중 오류가 발생했습니다. 다시 시도해주세요.")
                    
                    except Exception as e:
                        status_text.text("❌ 오류 발생")
                        progress_bar.progress(0)
                        st.error(f"⚠️ 오류가 발생했습니다: {str(e)}")
                        st.info("📞 문제가 지속되면 시스템 관리자에게 문의하세요.")
                        logger.error(f"지원사업 생성 실패: {e}")
                    
                    finally:
                        # 진행 상태 UI 정리
                        time.sleep(1)
                        progress_bar.empty()
                        status_text.empty()
        
        # # 하단 정보
        # st.markdown("---")
        # st.markdown("### 💡 추가 안내")
        
        # info_col1, info_col2, info_col3 = st.columns(3)
        
        # with info_col1:
        #     st.markdown("""
        #     **📝 데이터 품질**
        #     - 정확하고 최신 정보 입력
        #     - 명확한 지원 조건 명시
        #     - 연락처 정보 확인
        #     """)
        
        # with info_col2:
        #     st.markdown("""
        #     **🔍 생성 후 관리**
        #     - 검색 페이지에서 확인 가능
        #     - 언제든지 수정/삭제 가능
        #     - 실시간 상태 업데이트
        #     """)
        
        # with info_col3:
        #     st.markdown("""
        #     **🤖 AI 활용**
        #     - 챗봇에서 자동 검색 가능
        #     - 맞춤형 추천 서비스
        #     - 스마트 필터링 지원
        #     """)
        
        # 사이드바 정보 렌더링
        render_sidebar_info()
    
    except Exception as e:
        logger.error(f"신규 생성 페이지 오류: {e}")
        st.error("페이지 로드 중 오류가 발생했습니다.")
        st.exception(e)

if __name__ == "__main__":
    main() 