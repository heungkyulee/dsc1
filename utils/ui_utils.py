"""
UI 유틸리티 모듈
Streamlit 애플리케이션의 UI 관련 공통 함수들을 관리합니다.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any
import time

from logger import get_logger, log_user_action
import data_handler

logger = get_logger(__name__)


def get_deadline_status(deadline, application_period=None):
    """마감일 상태 확인 - deadline 우선, 없으면 application_period에서 추출"""
    
    # 1. deadline 필드 확인
    if deadline and not pd.isna(deadline):
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
            pass
    
    # 2. application_period에서 마감일 추출 시도
    if application_period and '~' in str(application_period):
        try:
            end_date = str(application_period).split('~')[1].strip()
            if len(end_date) == 8 and end_date.isdigit():
                year = end_date[:4]
                month = end_date[4:6]
                day = end_date[6:8]
                deadline_date = datetime.strptime(f"{year}-{month}-{day}", "%Y-%m-%d").date()
                
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
            pass
    
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