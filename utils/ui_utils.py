"""
UI 유틸리티 모듈
Streamlit 애플리케이션의 UI 관련 공통 함수들을 관리합니다.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any
import time
import logging

from logger import get_logger, log_user_action
import data_handler
from utils.data_utils import clear_announcements_cache

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
    """공고 수정 폼 - 개선된 UI 및 Pinecone 업데이트 포함"""
    st.markdown("---")
    st.markdown(f"### ✏️ 공고 수정: {current_data.get('title', '제목없음')}")

    # 수정 전 원본 데이터 표시
    with st.expander("📋 현재 데이터 미리보기", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.write("**제목:**", current_data.get('title', 'N/A'))
            st.write("**기관:**", current_data.get('organization', current_data.get('org_name_ref', 'N/A')))
            st.write("**분야:**", current_data.get('category', current_data.get('support_field', 'N/A')))
        with col2:
            st.write("**지역:**", current_data.get('region', 'N/A'))
            st.write("**마감일:**", current_data.get('deadline', 'N/A'))
            st.write("**대상:**", current_data.get('target_audience', 'N/A'))

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
            
            # 마감일 입력 처리 개선
            deadline_value = None
            if current_data.get('deadline'):
                try:
                    deadline_str = current_data.get('deadline')
                    if hasattr(deadline_str, 'date'):
                        deadline_value = deadline_str.date()
                    else:
                        deadline_value = pd.to_datetime(deadline_str).date()
                except Exception as e:
                    logger.warning(f"마감일 파싱 오류: {e}")
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
            # 연락처 데이터 처리 개선
            contact_value = current_data.get('contact', '')
            if not contact_value:
                inquiry_data = current_data.get('inquiry', [])
                if isinstance(inquiry_data, list) and inquiry_data:
                    contact_value = ', '.join(str(item) for item in inquiry_data if item)
                else:
                    contact_value = str(inquiry_data) if inquiry_data else ''
            
            new_contact = st.text_area(
                "연락처", 
                value=contact_value,
                height=100,
                help="담당자 연락처나 문의처를 입력하세요"
            )
        
        with contact_col2:
            # 지원내용 데이터 처리 개선
            support_value = current_data.get('support_content', '')
            if not support_value:
                support_value = current_data.get('budget', '')
            if isinstance(support_value, list):
                support_value = ', '.join(str(item) for item in support_value if item)
            
            new_support_content = st.text_area(
                "지원내용", 
                value=str(support_value) if support_value else '',
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
            # 신청방법 데이터 처리
            app_method_value = current_data.get('application_method', [])
            if isinstance(app_method_value, list):
                app_method_value = ', '.join(str(item) for item in app_method_value if item and 'None' not in str(item))
            
            new_app_method = st.text_area(
                "신청방법", 
                value=str(app_method_value) if app_method_value else '',
                height=100,
                help="신청방법과 절차를 입력하세요"
            )
        
        with app_info_col2:
            # 제출서류 데이터 처리
            documents_value = current_data.get('submission_documents', [])
            if isinstance(documents_value, list):
                documents_value = ', '.join(str(item) for item in documents_value if item and 'None' not in str(item))
            
            new_documents = st.text_area(
                "제출서류", 
                value=str(documents_value) if documents_value else '',
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
                    # 진행 상태 표시
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    try:
                        # 1단계: 데이터 구성
                        status_text.text("📝 수정 데이터 구성 중...")
                        progress_bar.progress(25)
                        
                        # pblancId 가져오기 (기존 데이터에서)
                        pblancId = current_data.get('pblancId', announcement_id)
                        
                        updated_data = {
                            "title": new_title.strip(),
                            "organization": new_organization.strip(),
                            "org_name_ref": new_organization.strip(),
                            "category": new_category.strip(),
                            "support_field": new_category.strip(),
                            "region": new_region.strip() or "전국",
                            "target_audience": new_target.strip() or "제한 없음",
                            "deadline": new_deadline.isoformat() if new_deadline else None,
                            "contact": new_contact.strip(),
                            "inquiry": [new_contact.strip()] if new_contact.strip() else [],
                            "support_content": new_support_content.strip(),
                            "budget": new_support_content.strip(),
                            "description": new_description.strip(),
                            "application_method": [method.strip() for method in new_app_method.split(',') if method.strip()] if new_app_method else ['온라인 신청'],
                            "submission_documents": [doc.strip() for doc in new_documents.split(',') if doc.strip()] if new_documents else [],
                            "updated_at": datetime.now().isoformat()
                        }
                        
                        # 2단계: 데이터베이스 업데이트 (JSON 파일 + Pinecone)
                        status_text.text("💾 데이터베이스 업데이트 중...")
                        progress_bar.progress(50)
                        
                        # update_announcement 함수 사용 (Pinecone 업데이트 포함)
                        success = data_handler.update_announcement(pblancId, updated_data)
                        
                        if success:
                            # 3단계: AI 시스템 업데이트 완료
                            status_text.text("🤖 AI 검색 시스템 업데이트 완료!")
                            progress_bar.progress(100)
                            
                            st.success("✅ 수정이 완료되었습니다! (JSON 파일과 AI 검색 시스템이 모두 업데이트되었습니다)")
                            
                            # 로깅
                            log_user_action("update_announcement", details={
                                "id": pblancId,
                                "title": new_title,
                                "organization": new_organization
                            })
                            
                            # 캐시 초기화 및 실시간 데이터 로드 플래그 설정
                            if hasattr(st, 'cache_data'):
                                st.cache_data.clear()
                            
                            # 모든 관련 캐시 초기화
                            clear_announcements_cache()
                            
                            # 다음 페이지 로드 시 실시간 데이터 사용하도록 플래그 설정
                            st.session_state['need_refresh'] = True
                            
                            # 성공 후 안내
                            st.info("🔄 수정이 완료되었습니다! 페이지를 새로고침합니다...")
                            time.sleep(2)
                            st.session_state['editing_id'] = None
                            st.rerun()
                        else:
                            status_text.text("❌ 업데이트 실패")
                            progress_bar.progress(0)
                            st.error("❌ 수정 중 오류가 발생했습니다.")
                    
                    except Exception as e:
                        status_text.text("❌ 오류 발생")
                        progress_bar.progress(0)
                        st.error(f"❌ 오류가 발생했습니다: {str(e)}")
                        st.info("📞 문제가 지속되면 시스템 관리자에게 문의하세요.")
                        logger.error(f"공고 수정 실패 - ID: {pblancId}, Error: {e}")
                    
                    finally:
                        # 진행 상태 UI 정리
                        time.sleep(1)
                        progress_bar.empty()
                        status_text.empty()
        
        with submit_col2:
            if st.form_submit_button("❌ 취소", type="secondary"):
                st.info("수정이 취소되었습니다.")
                st.session_state['editing_id'] = None
                st.rerun()
        
        with submit_col3:
            st.caption("* 표시된 항목은 필수 입력 사항입니다.")
        st.caption("💡 수정 시 AI 검색 시스템도 자동으로 업데이트됩니다.") 