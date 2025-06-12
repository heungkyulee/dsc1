"""
UI 스타일 관리 모듈
Streamlit 애플리케이션의 커스텀 CSS 스타일을 관리합니다.
"""

import streamlit as st


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