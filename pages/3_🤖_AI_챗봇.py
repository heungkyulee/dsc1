"""
🤖 AI 챗봇 페이지
K-Startup 지원사업 관리 시스템 - RAG 기반 AI 상담 챗봇
"""

import streamlit as st
from datetime import datetime, timezone, timedelta
import time

# 프로젝트 모듈 임포트
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config
from logger import get_logger, log_user_action
from ui.styles import apply_custom_styles
from ui.sidebar_info import render_sidebar_info
from utils.data_utils import initialize_session_state

# RAG 시스템 임포트
try:
    from rag_system import get_rag_chatbot
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False

# 로거 설정
logger = get_logger(__name__)

# Streamlit 페이지 설정
st.set_page_config(
    page_title="AI 챗봇 - K-Startup 관리 시스템",
    layout=config.STREAMLIT_LAYOUT,
    page_icon="🤖",
    menu_items={
        'About': f"# {config.APP_TITLE}\n\nRAG 기반 AI 챗봇 페이지",
        'Report a bug': None,
        'Get Help': None
    }
)

def get_current_time_info():
    """현재 시간 정보 가져오기"""
    kst = timezone(timedelta(hours=9))
    now = datetime.now(kst)
    
    return {
        "current_date": now.strftime("%Y년 %m월 %d일"),
        "current_time": now.strftime("%H시 %M분"),
        "korean_day": ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"][now.weekday()]
    }

def initialize_chat_session():
    """채팅 세션 초기화"""
    if 'chat_messages' not in st.session_state:
        st.session_state.chat_messages = []
    
    if 'chat_session_id' not in st.session_state:
        st.session_state.chat_session_id = f"chat_{int(time.time())}"

def add_message(role, content):
    """채팅 메시지 추가"""
    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.now().strftime("%H:%M:%S")
    }
    st.session_state.chat_messages.append(message)

def render_chat_interface():
    """채팅 인터페이스 렌더링"""
    
    # 채팅 히스토리 표시
    chat_container = st.container()
    
    with chat_container:
        if not st.session_state.chat_messages:
            # 초기 환영 메시지
            with st.chat_message("assistant"):
                st.markdown("""
                안녕하세요! 👋 K-Startup 지원사업 AI 상담봇입니다.
                
                **저는 다음과 같은 도움을 드릴 수 있습니다:**
                - 🔍 지원사업 검색 및 추천
                - 📋 지원 자격 및 조건 확인
                - 💰 지원 금액 및 혜택 정보
                - 📅 마감일 및 일정 안내
                - ❓ 지원사업 관련 일반적인 질문
                
                **질문 예시:**
                - "초기창업자를 위한 지원사업을 찾아줘"
                - "IT 분야 지원사업이 있나요?"
                - "마감이 임박한 공고를 알려주세요"
                - "5천만원 이상 지원하는 사업이 있나요?"
                
                궁금한 점을 자유롭게 질문해 주세요! 😊
                """)
        
        # 기존 메시지들 표시
        for message in st.session_state.chat_messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                st.caption(f"🕐 {message['timestamp']}")

def get_chatbot_response(user_input):
    """챗봇 응답 생성"""
    try:
        if RAG_AVAILABLE:
            # RAG 시스템을 통한 응답 생성
            chatbot = get_rag_chatbot()
            
            # 현재 시간 정보 포함
            time_info = get_current_time_info()
            enhanced_query = f"""
현재 시간: {time_info['current_date']} {time_info['korean_day']} {time_info['current_time']}

사용자 질문: {user_input}

위 질문에 대해 K-Startup 지원사업 데이터베이스를 바탕으로 정확하고 도움이 되는 답변을 제공해주세요.
마감일이 관련된 질문의 경우 현재 시간을 고려하여 답변해주세요.
"""
            
            # RAG 시스템 응답 (딕셔너리 형태)
            rag_response = chatbot.get_response(enhanced_query)
            
            # 응답에서 실제 답변 텍스트만 추출
            if isinstance(rag_response, dict):
                answer_text = rag_response.get('answer', '')
                confidence = rag_response.get('confidence', 0.0)
                sources_count = len(rag_response.get('sources', []))
                applicable_count = rag_response.get('applicable_count', 0)
                urgent_count = rag_response.get('urgent_count', 0)
                
                # 응답이 비어있을 때 처리
                if not answer_text or answer_text.strip() == '':
                    answer_text = f"""
죄송합니다. 현재 질문에 대한 구체적인 답변을 찾을 수 없습니다. 🤔

**💡 도움말:**
- 🔍 더 구체적인 키워드로 다시 질문해보세요
- 📊 검색된 지원사업: {sources_count}개
- ✅ 신청 가능한 지원사업: {applicable_count}개
- ⚠️ 마감 임박 지원사업: {urgent_count}개

**예시 질문:**
- "IT 분야 창업지원사업 추천해줘"
- "마감 임박한 지원사업 알려줘"
- "서울에서 신청 가능한 사업이 있나요?"

**대안 방법:**
- 🔍 검색 페이지에서 직접 찾아보기
- 📊 대시보드에서 전체 현황 확인하기
                    """
                
                # 신뢰도가 낮을 때 경고 메시지 추가
                elif confidence < 0.3:
                    answer_text += f"""

---
**🤖 AI 신뢰도:** {confidence:.1%} (낮음)
**💡 참고:** 위 답변의 신뢰도가 낮습니다. 더 정확한 정보를 원하시면 검색 페이지를 이용해주세요.
                    """
                
                # 디버그 정보는 로그에만 기록
                logger.info(f"RAG 응답 - 신뢰도: {confidence:.2f}, 소스: {sources_count}개, 신청가능: {applicable_count}개")
                
                return answer_text
            else:
                # 예상치 못한 응답 형태 - 로그에 기록하고 사용자에게는 친화적 메시지
                logger.error(f"예상치 못한 RAG 응답 형태: {type(rag_response)}")
                return """
죄송합니다. 시스템에서 예상치 못한 응답이 발생했습니다. 😅

**해결 방법:**
- 잠시 후 다시 시도해주세요
- 다른 방식으로 질문을 바꿔서 물어보세요
- 검색 페이지를 대신 이용해주세요

문제가 지속되면 대화 기록을 초기화한 후 다시 시도해보세요.
                """
                
        else:
            # RAG 시스템이 없을 때 기본 응답
            return """
죄송합니다. 현재 AI 챗봇 시스템이 일시적으로 사용할 수 없습니다. 🔧

**대안적 방법:**
1. 🔍 **검색 페이지 이용**: 왼쪽 메뉴의 '지원사업 검색 및 필터링' 페이지에서 원하는 지원사업을 찾을 수 있습니다.
2. ➕ **신규 생성**: 새로운 지원사업 정보가 있다면 '신규 지원사업 생성' 페이지를 이용해주세요.
3. 🏠 **대시보드**: 홈페이지에서 전체 현황을 확인할 수 있습니다.

시스템 복구 후 다시 이용해 주시기 바랍니다.
            """
    
    except Exception as e:
        logger.error(f"챗봇 응답 생성 오류: {e}")
        return f"""
죄송합니다. 응답 생성 중 오류가 발생했습니다. 😓

**해결 방법:**
- 잠시 후 다시 시도해주세요
- 질문을 더 간단하게 바꿔서 물어보세요
- 검색 페이지를 대신 이용해주세요

문제가 지속되면 시스템 관리자에게 문의해주세요.
        """

def render_chat_input():
    """채팅 입력 영역"""
    
    # 사용자 입력
    if user_input := st.chat_input("지원사업에 대해 궁금한 점을 물어보세요..."):
        # 사용자 메시지 추가 및 표시
        add_message("user", user_input)
        with st.chat_message("user"):
            st.markdown(user_input)
            st.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')}")
        
        # 챗봇 응답 생성 및 표시
        with st.chat_message("assistant"):
            with st.spinner("🤖 답변을 생성하는 중..."):
                response = get_chatbot_response(user_input)
            
            st.markdown(response)
            st.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')}")
        
        # 어시스턴트 메시지 추가
        add_message("assistant", response)
        
        # 사용자 액션 로깅
        log_user_action("chatbot_query", details={
            "query": user_input,
            "session_id": st.session_state.chat_session_id
        })
        
        # 화면 새로고침
        st.rerun()
    # """사용법 팁"""
    with st.expander("💡 챗봇 사용법 및 팁", expanded=False):
        st.markdown("""
        ### 🎯 효과적인 질문 방법
        
        **✅ 좋은 질문 예시:**
        - "창업 초기 단계에 적합한 지원사업을 추천해주세요"
        - "IT 분야에서 1억원 이상 지원하는 사업이 있나요?"
        - "이번 달 마감인 공고들을 알려주세요"
        - "중소벤처기업부에서 진행하는 사업들을 찾아주세요"
        
        **❌ 피해야 할 질문:**
        - 너무 일반적인 질문 ("안녕하세요", "뭐해요?")
        - 지원사업과 무관한 질문
        - 개인정보가 포함된 질문
        
        ### 🔧 기능 설명
        - **실시간 검색**: 최신 지원사업 정보를 바탕으로 답변
        - **맞춤 추천**: 조건에 맞는 지원사업 추천
        - **상세 정보**: 지원 조건, 금액, 마감일 등 구체적 정보 제공
        - **대화 기록**: 세션 동안 대화 내용 유지
        
        ### ⚠️ 주의사항
        - AI가 생성한 정보는 참고용이며, 공식 홈페이지에서 최종 확인 필요
        - 개인정보는 입력하지 마세요
        - 문제 발생 시 대화를 새로 시작해보세요
        """)

def main():
    """AI 챗봇 페이지 메인 함수"""
    try:
        # 커스텀 스타일 적용
        apply_custom_styles()
        
        # 세션 상태 초기화
        initialize_session_state()
        initialize_chat_session()
        
        # 현재 시간 정보
        time_info = get_current_time_info()
        
        # 페이지 헤더
        st.markdown(f"""
        <div style="text-align: center; padding: 2rem 0; background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%); 
                    border-radius: 15px; margin-bottom: 1rem; color: white;">
            <h1 style="margin: 0; font-size: 2.5rem;">🤖 AI 지원사업 상담 챗봇</h1>
            <p style="margin: 0.5rem 0; font-size: 1.1rem; opacity: 0.9;">
                RAG 기술로 정확한 지원사업 정보를 제공합니다
            </p>
            <p style="margin: 0; font-size: 0.9rem; opacity: 0.8;">
                📅 {time_info['current_date']} {time_info['korean_day']} {time_info['current_time']}
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # RAG 시스템 상태 표시 및 대화 관리
        col1, col2 = st.columns([3, 1])
        
        with col1:
            if RAG_AVAILABLE:
                st.success("✅ AI 챗봇이 정상적으로 작동 중입니다!")
            else:
                st.warning("⚠️ AI 챗봇 시스템이 일시적으로 사용할 수 없습니다. 검색 페이지를 대신 이용해주세요.")
        
        with col2:
            # 대화 기록 초기화 버튼
            if st.button("🗑️ 대화 기록 지우기", help="대화 기록을 모두 지웁니다"):
                st.session_state.chat_messages = []
                if RAG_AVAILABLE:
                    try:
                        chatbot = get_rag_chatbot()
                        if hasattr(chatbot, 'clear_conversation_memory'):
                            chatbot.clear_conversation_memory()
                    except Exception as e:
                        logger.warning(f"RAG 메모리 초기화 실패: {e}")
                st.success("대화 기록이 초기화되었습니다!")
                st.rerun()
        
        # 채팅 인터페이스
        render_chat_interface()
        
        # 채팅 입력
        render_chat_input()
        
        # 사이드바 정보 렌더링
        render_sidebar_info()
    
    except Exception as e:
        logger.error(f"AI 챗봇 페이지 오류: {e}")
        st.error("AI 챗봇 페이지 로드 중 오류가 발생했습니다.")
        st.exception(e)

if __name__ == "__main__":
    main() 