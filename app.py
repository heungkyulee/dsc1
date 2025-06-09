import streamlit as st
import pandas as pd
from datetime import datetime

# data_handler.py 와 crawler.py 에서 필요한 함수들을 가져옵니다.
# 프로젝트 구조에 따라 경로를 맞춰주어야 합니다. (예: from dsc1 import data_handler)
# 현재 dsc1 폴더 내에 app.py가 있고, data_handler.py, crawler.py도 같은 위치에 있다고 가정합니다.
import data_handler
import crawler 

# 페이지 설정
st.set_page_config(layout="wide", page_title="K-Startup 공고 관리")

# --- 세션 상태 초기화 ---
if 'current_view' not in st.session_state:
    st.session_state.current_view = "목록 조회" # 기본 화면
if 'editing_contest' not in st.session_state:
    st.session_state.editing_contest = None 
if 'selected_contest_id' not in st.session_state: # 상세 조회할 공고 ID
    st.session_state.selected_contest_id = None
if 'search_keyword' not in st.session_state:
    st.session_state.search_keyword = ""
if 'search_field' not in st.session_state:
    st.session_state.search_field = "전체"

# --- 데이터 로드 ---
def load_app_data():
    contests = data_handler.get_all_contests() # data_handler는 이제 항상 list[dict] 반환
    if contests:
        df = pd.DataFrame(contests)
        # 날짜 필드 형식 변환 (예시, 실제 사용하는 필드에 맞게 조정 필요)
        date_cols = ['reqstBeginDt', 'reqstEndDt', 'pblancBeginDe', 'pblancEndDe', '공고일자'] 
        for col in date_cols:
            if col in df.columns:
                try:
                    # YYYYMMDD 또는 YYYY-MM-DD 형식의 문자열을 datetime으로 변환 후 다시 YYYY-MM-DD 형식의 문자열로
                    df[col] = pd.to_datetime(df[col].astype(str).str.replace('-', ''), format='%Y%m%d', errors='coerce').dt.strftime('%Y-%m-%d')
                except Exception as e:
                    # st.warning(f"날짜 필드 '{col}' 변환 중 오류: {e}")
                    pass # 오류 발생 시 원본 유지 또는 다른 처리
        return df
    return pd.DataFrame()

# --- UI 콜백 함수 ---
def go_to_view(view_name):
    st.session_state.current_view = view_name
    st.session_state.editing_contest = None # 다른 뷰로 이동 시 수정 상태 초기화
    st.session_state.selected_contest_id = None # 다른 뷰로 이동 시 상세 조회 ID 초기화

def start_editing_contest(contest_id):
    contest = data_handler.find_contest_by_id(contest_id)
    if contest:
        st.session_state.editing_contest = contest
        st.session_state.current_view = "수정" # 뷰를 직접 변경하고 rerun
        # go_to_view("수정") # 이렇게 하면 selected_contest_id 등이 None으로 초기화될 수 있음
        st.rerun()
    else:
        st.error(f"ID {contest_id} 공고를 찾을 수 없습니다.")

def view_contest_detail(contest_id):
    st.session_state.selected_contest_id = contest_id
    st.session_state.current_view = "상세 조회"
    st.rerun()

def run_crawler():
    with st.spinner("데이터를 수집 중입니다... 시간이 다소 소요될 수 있습니다."):
        try:
            if hasattr(crawler, 'collect_data'):
                crawler.collect_data() 
                st.success("데이터 수집이 완료되었습니다!")
                data_handler.load_all_data() # data_handler 내부 데이터 리로드
                go_to_view("목록 조회") # 수집 후 목록으로
                st.rerun()
            else:
                st.warning("crawler 모듈에 'collect_data' 함수가 정의되어 있지 않습니다.")
        except Exception as e:
            st.error(f"크롤링 중 오류 발생: {e}")

# --- UI 섹션 함수 ---

def display_sidebar():
    st.sidebar.title("메뉴")
    
    if st.sidebar.button("📢 공고 목록 조회", key="btn_view_list"):
        go_to_view("목록 조회")
    
    st.sidebar.subheader("데이터 관리")
    if st.sidebar.button("🔄 데이터 새로고침 (크롤러)", key="btn_crawl"):
        run_crawler() 
        
    if st.sidebar.button("➕ 새 공고 추가", key="btn_add_new"):
        st.session_state.editing_contest = None 
        go_to_view("추가")

def display_contest_list_view(df):
    st.header("K-Startup 사업 공고 현황")

    # --- 검색 섹션 ---
    st.subheader("공고 검색")
    search_col1, search_col2 = st.columns([2,2])
    with search_col1:
        st.session_state.search_keyword = st.text_input(
            "검색어 입력", 
            value=st.session_state.search_keyword, 
            key="search_keyword_input_list" # 키 중복 방지
        )
    with search_col2:
        search_field_options = ['전체'] + (df.columns.tolist() if not df.empty else [])
        current_search_field = st.session_state.search_field
        if current_search_field not in search_field_options:
            current_search_field = '전체'
        
        st.session_state.search_field = st.selectbox(
            "검색 대상 필드", 
            options=search_field_options, 
            index=search_field_options.index(current_search_field),
            key="search_field_select_list" # 키 중복 방지
        )
    
    st.subheader("공고 목록")
    if df.empty:
        st.info("표시할 공고 데이터가 없습니다. 사이드바에서 '데이터 새로고침'을 실행해주세요.")
        return

    df_display = df.copy()
    if st.session_state.search_keyword:
        kw = st.session_state.search_keyword.lower()
        if st.session_state.search_field == '전체':
            mask = df_display.apply(lambda row: any(kw in str(val).lower() for val in row.astype(str)), axis=1)
            df_display = df_display[mask]
        elif st.session_state.search_field in df_display.columns:
            df_display = df_display[df_display[st.session_state.search_field].astype(str).str.lower().str.contains(kw, na=False)]
    
    # CSV 내보내기 버튼
    if not df_display.empty:
        csv_data = df_display.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📜 현재 목록 CSV로 내보내기",
            data=csv_data,
            file_name=f"kstartup_contests_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            key="download_csv_list"
        )

    # 컬럼 순서 및 표시할 컬럼 선택
    display_columns = [
        'pblancId', 'title', '기관명', '지원분야', '접수기간', '지역', 
    ]
    existing_display_columns = [col for col in display_columns if col in df_display.columns]
    if not existing_display_columns and not df_display.empty: 
        existing_display_columns = df_display.columns.tolist()

    st.dataframe(df_display[existing_display_columns] if existing_display_columns else df_display, use_container_width=True, hide_index=True)

    if not df_display.empty and 'pblancId' in df_display.columns:
        st.subheader("개별 공고 관리")
        for idx, row in df_display.iterrows():
            item_id = row['pblancId']
            item_title = row.get('title', row.get('pblancNm', "제목 없음"))
            
            cols = st.columns([3, 1, 1, 1]) # 상세, 수정, 삭제 버튼용
            cols[0].write(f"**{item_title}** (ID: {item_id})")
            
            if cols[1].button("🔍 상세", key=f"detail_{item_id}_{idx}"):
                view_contest_detail(item_id)
            
            if cols[2].button("✏️ 수정", key=f"edit_{item_id}_{idx}"):
                start_editing_contest(item_id)
            
            if cols[3].button("🗑️ 삭제", key=f"delete_{item_id}_{idx}"):
                if data_handler.delete_contest(item_id):
                    st.success(f"공고 ID '{item_id}'가 삭제되었습니다.")
                    st.rerun() 
                else:
                    st.error(f"공고 ID '{item_id}' 삭제 중 오류 발생.")
            st.divider()

def display_contest_detail_view():
    st.header("📜 공고 상세 정보")
    contest_id = st.session_state.selected_contest_id

    if not contest_id:
        st.warning("조회할 공고가 선택되지 않았습니다. 목록에서 선택해주세요.")
        if st.button("목록으로 돌아가기", key="detail_to_list_no_id"):
            go_to_view("목록 조회")
            st.rerun()
        return

    contest = data_handler.find_contest_by_id(contest_id)

    if not contest:
        st.error(f"공고 ID '{contest_id}'를 찾을 수 없습니다.")
        if st.button("목록으로 돌아가기", key="detail_to_list_not_found"):
            go_to_view("목록 조회")
            st.rerun()
        return

    # 상세 정보 표시 (모든 키-값을 보기 좋게)
    # field_definitions 를 재활용하거나, 간단하게 모든 항목 표시
    st.subheader(f"[{contest.get('pblancId', 'ID 없음')}] {contest.get('title', '제목 없음')}")
    
    # 주요 필드 순서대로 표시 (data_handler.py의 field_definitions 참고 또는 모든 필드)
    ordered_keys = [
        "pblancId", "title", "기관명", "지원분야", "접수기간", "지역", "대상연령", 
        "기관구분", "연락처", "창업업력", "대상", "담당부서", "공고번호", "공고일자",
        "공고기관", "pblancUrl", "공고설명" 
    ]
    
    # 모든 필드를 표시하되, 정의된 순서로 먼저 보여주고 나머지는 그 뒤에
    displayed_keys = set()
    for key in ordered_keys:
        if key in contest and contest[key]: # 값이 있는 경우만
            st.markdown(f"**{key}:** {contest[key]}")
            displayed_keys.add(key)
    
    st.markdown("---") 
    st.markdown("**기타 정보:**")
    for key, value in contest.items():
        if key not in displayed_keys and value: # 아직 표시되지 않았고 값이 있는 경우
             st.markdown(f"**{key}:** {value}")


    # 버튼 영역
    st.divider()
    col1, col2, col3, col4 = st.columns([1.5, 1, 1, 1.5]) # 버튼 배치용
    with col1:
        if st.button("✏️ 이 공고 수정하기", key="detail_edit_btn"):
            start_editing_contest(contest_id) # 수정 화면으로
    with col2:
        if st.button("🗑️ 이 공고 삭제하기", key="detail_delete_btn"):
            if data_handler.delete_contest(contest_id):
                st.success(f"공고 ID '{contest_id}'가 삭제되었습니다.")
                go_to_view("목록 조회")
                st.rerun()
            else:
                st.error(f"공고 ID '{contest_id}' 삭제 중 오류 발생.")
    with col3:
        if st.button("⏪ 목록으로 돌아가기", key="detail_to_list_btn"):
            go_to_view("목록 조회")
            st.rerun()

def display_add_edit_form_view():
    is_editing = st.session_state.editing_contest is not None
    form_title = "✏️ 공고 수정" if is_editing else "➕ 새 공고 추가"
    st.header(form_title)

    initial_data = st.session_state.editing_contest if is_editing else {}
    
    field_definitions = {
        "pblancId": {"label": "공고 ID (pblancId/pbancSn)", "type": "text", "required": True, "disabled_on_edit": True},
        "title": {"label": "공고명 (title/biz_pbanc_nm)", "type": "text", "required": True},
        "지원분야": {"label": "지원분야 (supt_biz_clsfc)", "type": "text"},
        "대상연령": {"label": "대상연령 (biz_trgt_age)", "type": "text"},
        "기관명": {"label": "기관명 (pbanc_ntrp_nm)", "type": "text"},
        "기관구분": {"label": "기관구분 (sprv_inst)", "type": "text"},
        "연락처": {"label": "연락처 (prch_cnpl_no)", "type": "text"},
        "지역": {"label": "지역 (supt_regin)", "type": "text"},
        "접수기간": {"label": "접수기간 (application_period)", "type": "text", "help": "YYYYMMDD ~ YYYYMMDD 또는 YYYY-MM-DD ~ YYYY-MM-DD"},
        "창업업력": {"label": "창업업력 (biz_enyy)", "type": "text"},
        "대상": {"label": "신청 대상 (aply_trgt)", "type": "text"},
        "담당부서": {"label": "담당부서 (biz_prch_dprt_nm)", "type": "text"},
        "공고번호": {"label": "공고번호 (pbanc_sn)", "type": "text", "help":"실제 API의 pbanc_sn과 동일하게 사용 권장"},
        "공고설명": {"label": "공고설명 (pbanc_ctnt)", "type": "textarea"},
        "공고일자": {"label": "공고일자 (pblancBeginDe)", "type": "text", "help": "YYYYMMDD 또는 YYYY-MM-DD"},
        "공고기관": {"label": "공고기관 (pbanc_ntrp_nm)", "type": "text"},
        "pblancUrl": {"label": "공고 URL (pblancUrl)", "type":"text"}
    }
    
    with st.form(key="contest_form"):
        form_data = {}
        for field_key, props in field_definitions.items():
            label = props["label"]
            # initial_value는 문자열로 변환하여 사용 (NoneType 오류 방지)
            initial_value = str(initial_data.get(field_key, ""))
            
            if props["type"] == "textarea":
                form_data[field_key] = st.text_area(label, value=initial_value, height=100, help=props.get("help"))
            else: 
                disabled = props.get("disabled_on_edit", False) and is_editing
                form_data[field_key] = st.text_input(label, value=initial_value, disabled=disabled, help=props.get("help"))

        submitted = st.form_submit_button("저장")
        if submitted:
            if not form_data.get("pblancId") and not is_editing:
                 st.error("공고 ID (pblancId/pbancSn)는 필수 입력 항목입니다.")
                 return
            if not form_data.get("title"):
                 st.error("공고명 (title/biz_pbanc_nm)은 필수 입력 항목입니다.")
                 return

            if is_editing and 'pblancId' not in form_data: # 수정 시 ID가 disabled면 form_data에 없을 수 있음
                 form_data['pblancId'] = st.session_state.editing_contest['pblancId']
            
            # 빈 문자열을 None으로 변환하거나, data_handler에서 처리하도록 할 수 있음
            # 여기서는 입력된 그대로 전달
            contest_to_save = {k: (form_data.get(k) if form_data.get(k) else None) for k in field_definitions.keys()}
            # None인 값은 제외하고 저장 (data_handler.py의 update/add 로직에 따라)
            contest_to_save = {k: v for k, v in contest_to_save.items() if v is not None and v != ""}


            if is_editing:
                if data_handler.update_contest(st.session_state.editing_contest["pblancId"], contest_to_save):
                    st.success("공고가 성공적으로 수정되었습니다.")
                    go_to_view("목록 조회") # 수정 후 목록으로
                    st.rerun()
                else:
                    st.error("공고 수정 중 오류가 발생했습니다.")
            else: 
                if data_handler.add_contest(contest_to_save):
                    st.success("새 공고가 성공적으로 추가되었습니다.")
                    go_to_view("목록 조회") # 추가 후 목록으로
                    st.rerun()
                else:
                    st.error("공고 추가 중 오류가 발생했습니다. (ID 중복 등)")
    
    if st.button("취소", key="cancel_form"):
        go_to_view("목록 조회")
        st.rerun()

# --- 메인 앱 로직 ---
def main():
    data_df = load_app_data()
    display_sidebar()

    current_view = st.session_state.current_view
    if current_view == "목록 조회":
        display_contest_list_view(data_df)
    elif current_view == "추가" or current_view == "수정":
        display_add_edit_form_view()
    elif current_view == "상세 조회":
        display_contest_detail_view()
    # elif current_view == "분석":
        # display_analysis_view(data_df) # 추후 구현

if __name__ == "__main__":
    main() 