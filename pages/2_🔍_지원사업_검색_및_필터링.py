"""
🔍 지원사업 검색 및 필터링 페이지
K-Startup 지원사업 관리 시스템
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time

# 프로젝트 모듈 임포트
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config
from logger import get_logger, log_user_action
import data_handler
from ui.styles import apply_custom_styles
from ui.sidebar_info import render_sidebar_info
from utils.data_utils import initialize_session_state, load_announcements_data, load_announcements_data_fresh, clear_announcements_cache
from utils.ui_utils import (
    get_deadline_status, get_status_color, prepare_csv_download, 
    edit_announcement
)

# 로거 설정
logger = get_logger(__name__)

# Streamlit 페이지 설정
st.set_page_config(
    page_title="지원사업 검색 및 필터링 - K-Startup 관리 시스템",
    layout=config.STREAMLIT_LAYOUT,
    page_icon="🔍",
    menu_items={
        'About': f"# {config.APP_TITLE}\n\n지원사업 검색 및 필터링 페이지",
        'Report a bug': None,
        'Get Help': None
    }
)

def apply_advanced_filters(df, search_query, category, region, status, organization, date_filter, target):
    """고급 필터링 적용"""
    if df.empty:
        return df
    
    filtered_df = df.copy()
    
    # 텍스트 검색 (향상된 검색)
    if search_query:
        search_terms = search_query.lower().split()
        text_columns = ['title', 'organization', 'description', 'org_name_ref', 'support_field', 'region', 'target_audience']
        
        # 인덱스를 맞춘 마스크 생성
        mask = pd.Series([False] * len(filtered_df), index=filtered_df.index)
        
        for term in search_terms:
            term_mask = pd.Series([False] * len(filtered_df), index=filtered_df.index)
            for col in text_columns:
                if col in filtered_df.columns:
                    # 안전한 문자열 검색 (regex=False로 특수문자 처리)
                    col_mask = filtered_df[col].astype(str).str.lower().str.contains(term, na=False, regex=False)
                    term_mask = term_mask | col_mask
            mask = mask | term_mask
        
        # 안전한 boolean 인덱싱
        try:
            filtered_df = filtered_df[mask]
        except Exception as e:
            logger.warning(f"검색 필터링 중 오류 발생: {e}")
            # 오류 발생 시 원본 데이터 반환
            pass
    
    # 카테고리 필터
    if category != "전체" and not filtered_df.empty:
        category_cols = ['category', 'support_field']
        for col in category_cols:
            if col in filtered_df.columns:
                try:
                    filtered_df = filtered_df[filtered_df[col] == category]
                    break
                except Exception as e:
                    logger.warning(f"카테고리 필터링 중 오류: {e}")
    
    # 지역 필터
    if region != "전체" and 'region' in filtered_df.columns and not filtered_df.empty:
        try:
            filtered_df = filtered_df[filtered_df['region'] == region]
        except Exception as e:
            logger.warning(f"지역 필터링 중 오류: {e}")
    
    # 기관 필터
    if organization != "전체" and not filtered_df.empty:
        org_cols = ['organization', 'org_name_ref']
        for col in org_cols:
            if col in filtered_df.columns:
                try:
                    filtered_df = filtered_df[filtered_df[col] == organization]
                    break
                except Exception as e:
                    logger.warning(f"기관 필터링 중 오류: {e}")
    
    # 대상 필터
    if target != "전체" and 'target_audience' in filtered_df.columns and not filtered_df.empty:
        try:
            filtered_df = filtered_df[filtered_df['target_audience'].str.contains(target, na=False, regex=False)]
        except Exception as e:
            logger.warning(f"대상 필터링 중 오류: {e}")
    
    # 날짜 필터
    if date_filter != "전체" and 'deadline' in filtered_df.columns and not filtered_df.empty:
        try:
            today = datetime.now()
            deadline_series = pd.to_datetime(filtered_df['deadline'], errors='coerce')
            
            if date_filter == "오늘":
                mask = deadline_series.dt.date == today.date()
                filtered_df = filtered_df[mask]
            elif date_filter == "1주일 이내":
                week_later = today + timedelta(days=7)
                mask = (deadline_series >= today) & (deadline_series <= week_later)
                filtered_df = filtered_df[mask]
            elif date_filter == "1개월 이내":
                month_later = today + timedelta(days=30)
                mask = (deadline_series >= today) & (deadline_series <= month_later)
                filtered_df = filtered_df[mask]
            elif date_filter == "3개월 이내":
                three_months_later = today + timedelta(days=90)
                mask = (deadline_series >= today) & (deadline_series <= three_months_later)
                filtered_df = filtered_df[mask]
            elif date_filter == "만료된 공고":
                mask = deadline_series < today
                filtered_df = filtered_df[mask]
        except Exception as e:
            logger.warning(f"날짜 필터링 중 오류: {e}")
            # 오류 발생 시 날짜 필터 무시
    
    return filtered_df

def render_card_view(df):
    """카드형 보기 - 모든 상세 정보 표시"""
    st.markdown("### 📋 상세 카드 보기")
    
    for idx, row in df.iterrows():
        # 마감 상태 확인
        deadline_status = get_deadline_status(row.get('deadline', ''), row.get('application_period', ''))
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
                
                # 마감일 처리 - deadline 필드 우선, 없으면 application_period에서 추출
                deadline_str = None
                
                # 1. deadline 필드 확인
                if 'deadline' in row and pd.notna(row['deadline']) and row['deadline']:
                    if hasattr(row['deadline'], 'strftime'):
                        deadline_str = row['deadline'].strftime('%Y-%m-%d')
                    else:
                        deadline_str = str(row['deadline'])
                
                # 2. deadline이 없으면 application_period에서 추출
                if not deadline_str:
                    application_period = row.get('application_period', '')
                    if application_period and '~' in application_period:
                        try:
                            # "20250611 ~ 20250731" 형식에서 마감일 추출
                            end_date = application_period.split('~')[1].strip()
                            if len(end_date) == 8 and end_date.isdigit():
                                year = end_date[:4]
                                month = end_date[4:6]
                                day = end_date[6:8]
                                deadline_str = f"{year}-{month}-{day}"
                        except:
                            pass
                
                if deadline_str:
                    st.markdown(f"**⏰ 마감일:** {deadline_str}")
                else:
                    # 접수기간이라도 표시
                    application_period = row.get('application_period', '')
                    if application_period:
                        st.markdown(f"**⏰ 접수기간:** {application_period}")
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
            
            # 액션 버튼
            action_col1, action_col2 = st.columns(2)
            
            with action_col1:
                contest_id = None
                possible_id_fields = ['pblancId', 'id']
                for id_field in possible_id_fields:
                    if id_field in row and pd.notna(row[id_field]) and row[id_field]:
                        contest_id = str(row[id_field])
                        break
                if not contest_id:
                    contest_id = str(idx)
                if st.button("✏️ 수정", key=f"edit_{idx}"):
                    st.session_state['editing_id'] = contest_id
                    st.rerun()
                # 수정 폼은 editing_id가 일치할 때만 렌더링
                if st.session_state.get('editing_id') == contest_id:
                    edit_announcement(contest_id, row)
            
            with action_col2:
                # 삭제 기능 개선 - 수정과 동일한 ID 로직
                delete_contest_id = None
                possible_id_fields = ['pblancId', 'id']
                
                # 가능한 ID 필드들을 순서대로 확인
                for id_field in possible_id_fields:
                    if id_field in row and pd.notna(row[id_field]) and row[id_field]:
                        delete_contest_id = str(row[id_field])
                        break
                
                # 모든 ID 필드가 없으면 인덱스 사용
                if not delete_contest_id:
                    delete_contest_id = str(idx)
                
                if st.button("🗑️ 삭제", key=f"delete_{idx}", type="secondary"):
                    if st.session_state.get(f"confirm_delete_{idx}", False):
                        # 디버깅 정보 출력
                        st.info(f"🗑️ 삭제 대상 ID: {delete_contest_id} (원본 인덱스: {idx})")
                        # 진행 상태 표시
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        try:
                            # 1단계: 삭제 준비
                            status_text.text("🗑️ 삭제 준비 중...")
                            progress_bar.progress(25)
                            
                            # 2단계: JSON 파일에서 삭제
                            status_text.text("💾 데이터베이스에서 삭제 중...")
                            progress_bar.progress(50)
                            
                            # delete_contest 함수 사용 (Pinecone 삭제 포함)
                            success = data_handler.delete_contest(delete_contest_id)
                            
                            if success:
                                # 3단계: AI 시스템에서 삭제 완료
                                status_text.text("🤖 AI 검색 시스템에서 삭제 완료!")
                                progress_bar.progress(100)
                                
                                st.success("✅ 삭제되었습니다! (JSON 파일과 AI 검색 시스템에서 모두 제거되었습니다)")
                                
                                # 로깅
                                log_user_action("delete_announcement", details={
                                    "id": delete_contest_id,
                                    "title": row.get('title', 'Unknown')
                                })
                                
                                # 캐시 초기화 및 실시간 데이터 로드 플래그 설정
                                if hasattr(st, 'cache_data'):
                                    st.cache_data.clear()
                                
                                # 다음 페이지 로드 시 실시간 데이터 사용하도록 플래그 설정
                                st.session_state['need_refresh'] = True
                                
                                # 확인 상태 초기화
                                st.session_state[f"confirm_delete_{idx}"] = False
                                
                                # 페이지 새로고침
                                time.sleep(1)
                                st.rerun()
                            else:
                                status_text.text("❌ 삭제 실패")
                                progress_bar.progress(0)
                                st.error("❌ 삭제 중 오류가 발생했습니다.")
                                st.session_state[f"confirm_delete_{idx}"] = False
                        
                        except Exception as e:
                            status_text.text("❌ 삭제 오류")
                            progress_bar.progress(0)
                            st.error(f"❌ 삭제 중 오류가 발생했습니다: {str(e)}")
                            st.session_state[f"confirm_delete_{idx}"] = False
                            logger.error(f"공고 삭제 실패 - ID: {delete_contest_id}, Error: {e}")
                        
                        finally:
                            # 진행 상태 UI 정리
                            time.sleep(1)
                            progress_bar.empty()
                            status_text.empty()
                    else:
                        st.session_state[f"confirm_delete_{idx}"] = True
                        st.warning("⚠️ 다시 클릭하면 완전히 삭제됩니다. (JSON 파일과 AI 검색 시스템에서 모두 제거)")
                        st.info("💡 삭제 후에는 복구할 수 없습니다.")
            
#             with action_col3:
#                 if st.button("📋 복사", key=f"copy_{idx}"):
#                     # 공고 정보를 텍스트로 정리
#                     copy_text = f"""
# {title}
# 주관기관: {org_name}
# 지원분야: {category}
# 마감일: {deadline_str if 'deadline_str' in locals() else 'N/A'}
# 연락처: {contact}
#                     """.strip()
#                     st.code(copy_text, language=None)
#                     st.success("공고 정보가 복사 가능한 형태로 표시되었습니다!")
            
#             with action_col4:
#                 if st.button("🔗 링크", key=f"link_{idx}"):
#                     # 외부 링크나 상세 페이지로 이동 (구현에 따라 조정)
#                     st.info("원본 페이지 링크 기능은 추후 구현 예정입니다.")
            
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
        
        deadline_status = get_deadline_status(row.get('deadline', ''), row.get('application_period', ''))
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

def main():
    """지원사업 검색 및 필터링 페이지 메인 함수"""
    try:
        # 커스텀 스타일 적용
        apply_custom_styles()
        
        # 세션 상태 초기화
        initialize_session_state()
        
        # 페이지 헤더
        st.title("🔍 지원사업 검색 및 관리")
        st.markdown("### 원하는 지원사업을 빠르게 찾고 관리하세요")
        
        # 데이터 로드 - 실시간 데이터 사용
        with st.spinner("🔍 검색 데이터를 준비하는 중..."):
            # 수정/삭제 후에는 실시간 데이터 로드
            use_fresh_data = st.session_state.get('need_refresh', False)
            
            if use_fresh_data:
                st.info("🔄 최신 데이터를 로드하는 중...")
                df_announcements = load_announcements_data_fresh()
                st.session_state['need_refresh'] = False
                clear_announcements_cache()
            else:
                df_announcements = load_announcements_data()
        
        if df_announcements.empty:
            st.warning("⚠️ 검색할 데이터가 없습니다")
            st.info("검색할 공고 데이터가 없습니다. 홈페이지(🏠 K-Startup 대시보드)에서 데이터를 수집해주세요.")
            return
        
        st.markdown("---")
        
        # 검색 및 필터 섹션 개선
        with st.expander("🔍 고급 검색 및 필터", expanded=True):
            # 검색어 입력
            col_search1, col_search2 = st.columns([3, 1])
            with col_search1:
                search_query = st.text_input(
                    "🔎 통합 검색",
                    value=st.session_state.get('search_query', ''),
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
            col2_1, col2_2 = st.columns(2)
            with col2_1:
                if st.button("🔄 필터 초기화", help="모든 검색 조건을 초기화"):
                    st.session_state.search_query = ""
                    st.rerun()
            
            with col2_2:
                if st.button("🔄 데이터 새로고침", help="최신 데이터 강제 로드"):
                    clear_announcements_cache()
                    st.session_state['need_refresh'] = True
                    st.success("캐시를 초기화했습니다!")
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
        
        # 사이드바 정보 렌더링
        render_sidebar_info()
    
    except Exception as e:
        logger.error(f"검색 페이지 오류: {e}")
        st.error("페이지 로드 중 오류가 발생했습니다.")
        st.exception(e)

if __name__ == "__main__":
    main() 