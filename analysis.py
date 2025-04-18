import pandas as pd
from datetime import datetime
import data_handler
import re # 정규 표현식 모듈 임포트

def parse_announcement_date(date_str):
    """공고일자 문자열을 datetime 객체로 변환 시도 (다양한 형식 지원)"""
    if not date_str or not isinstance(date_str, str):
        return None

    # 1. "YYYY년 MM월 DD일" 형식 시도 (정규 표현식 사용)
    match_kor = re.search(r'(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일', date_str)
    if match_kor:
        try:
            year, month, day = map(int, match_kor.groups())
            return datetime(year, month, day)
        except ValueError:
            pass # 잘못된 날짜 형식 (예: 2월 30일)이면 다음으로

    # 2. "YYYY-MM-DD" 또는 "YYYY.MM.DD" 형식 시도 (기존 로직 개선)
    # 문자열에서 날짜로 보이는 부분을 좀 더 명확하게 추출 시도
    match_std = re.search(r'(\d{4}[-.]\d{1,2}[-.]\d{1,2})', date_str)
    if match_std:
        date_part = match_std.group(1)
        formats_to_try = ["%Y-%m-%d", "%Y.%m.%d"]
        for fmt in formats_to_try:
            try:
                return datetime.strptime(date_part, fmt)
            except ValueError:
                continue

    # 모든 형식 변환 실패 시 경고 출력
    # print(f"[경고] 날짜 형식 변환 실패: {date_str}") # 너무 많은 경고가 나올 수 있어 주석 처리
    return None

def get_announcements_timeseries_by_org(start_date=None, end_date=None, freq='ME'):
    """
    기관별 공고 게시 빈도를 시계열 데이터로 반환합니다.

    Args:
        start_date (datetime, optional): 분석 시작일. Defaults to None.
        end_date (datetime, optional): 분석 종료일. Defaults to None.
        freq (str, optional): 리샘플링 주기 ('ME': 월말 기준, 'W': 주별, 'D': 일별 등). Defaults to 'ME'.

    Returns:
        pandas.DataFrame: 기관명을 인덱스로, 날짜(주기 시작일)를 컬럼으로, 공고 수를 값으로 갖는 DataFrame.
                       오류 발생 시 None 반환.
    """
    try:
        announcements = data_handler.get_all_announcements()
        organizations = data_handler.get_all_organizations()

        if not announcements or not organizations:
            print("[정보] 분석할 공고 또는 기관 데이터가 없습니다.")
            return None

        org_id_to_name = {org_id: data['name'] for org_id, data in organizations.items()}

        data = []
        for pbancSn, ann_data in announcements.items():
            parsed_date = parse_announcement_date(ann_data.get("announcement_date"))
            org_id = ann_data.get("org_id")
            org_name = org_id_to_name.get(org_id)

            if parsed_date and org_name:
                # 날짜 필터링
                if start_date and parsed_date < start_date:
                    continue
                if end_date and parsed_date > end_date:
                    continue
                data.append({"date": parsed_date, "org_name": org_name})

        if not data:
            print("[정보] 분석할 기간 내의 유효한 공고 데이터가 없습니다.")
            return None

        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'])

        # 기관별, 주기별 공고 수 계산
        # 결과는 MultiIndex (org_name, date)를 가진 Series가 됨
        timeseries = df.groupby('org_name').resample(freq, on='date').size()

        # 결과를 기관명을 행으로, 날짜를 열로 변환 (unstack)
        # level=0 (org_name)이 아닌 level=1 (date) 또는 기본값(마지막 레벨)을 컬럼으로 보내야 함
        analysis_result = timeseries.unstack(fill_value=0)

        return analysis_result

    except Exception as e:
        print(f"[에러] 시계열 분석 중 오류 발생: {e}")
        import traceback
        traceback.print_exc() # 상세 에러 출력
        return None

if __name__ == '__main__':
    print("분석 모듈 테스트...")

    # 데이터 핸들러 초기화 (필요시)
    # data_handler.initialize_data()

    # 시계열 분석 테스트 (월별)
    ts_data = get_announcements_timeseries_by_org(freq='ME')

    if ts_data is not None:
        print("\n=== 기관별 월별 공고 게시 빈도 ===")
        print(ts_data)

        # 특정 기간 필터링 테스트
        # start = datetime(2024, 1, 1)
        # end = datetime(2024, 12, 31)
        # ts_data_filtered = get_announcements_timeseries_by_org(start_date=start, end_date=end, freq='ME')
        # if ts_data_filtered is not None:
        #     print(f"\n=== {start.year}년 기관별 월별 공고 게시 빈도 ===")
        #     print(ts_data_filtered) 