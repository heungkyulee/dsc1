import data_handler
import analysis
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.syntax import Syntax
from rich import print as rprint # Use rich print for better formatting
import pandas as pd
import os
from datetime import datetime # datetime 임포트 추가
from rich import box # box 스타일 임포트

console = Console()

# --- Display Functions (using Rich) ---

def display_organizations(organizations):
    """기관 목록을 Rich Table로 표시"""
    if not organizations:
        rprint("[yellow]표시할 기관 정보가 없습니다.[/yellow]")
        return

    table = Table(title="기관 목록", show_header=True, header_style="bold magenta", box=box.ROUNDED) # box 스타일 적용
    table.add_column("기관 ID", style="dim", width=15)
    table.add_column("기관명")
    table.add_column("기관 구분")

    for org_id, data in organizations.items():
        table.add_row(org_id, data.get('name', 'N/A'), data.get('type', 'N/A'))

    console.print(table)

def display_announcements_list(ann_ids):
    """주어진 ID 목록의 공고 요약을 Rich Table로 표시"""
    announcements = data_handler.get_all_announcements() # 전체 로드
    if not ann_ids:
        rprint("[yellow]표시할 공고 정보가 없습니다.[/yellow]")
        return

    table = Table(title="공고 목록", show_header=True, header_style="bold cyan", box=box.ROUNDED) # box 스타일 적용
    table.add_column("공고 ID (pbancSn)", style="dim", width=15)
    table.add_column("제목", style="bold")
    table.add_column("기관명")
    table.add_column("접수기간")
    table.add_column("지역")

    count = 0
    MAX_DISPLAY = 50 # 너무 많은 결과 방지
    for ann_id in ann_ids:
        if count >= MAX_DISPLAY:
            rprint(f"[yellow]결과가 너무 많아 상위 {MAX_DISPLAY}개만 표시합니다...[/yellow]")
            break
        data = announcements.get(str(ann_id))
        if data:
            table.add_row(
                str(ann_id),
                data.get('title', 'N/A'),
                data.get('org_name_ref', 'N/A'),
                data.get('application_period', 'N/A'),
                data.get('region', 'N/A')
            )
            count += 1
        else:
             rprint(f"[red]오류: 공고 ID {ann_id} 데이터를 찾을 수 없습니다.[/red]")


    if count > 0:
        console.print(table)
    elif not announcements: # ann_ids는 있었지만 announcements 자체가 비어있는 경우
         rprint("[yellow]표시할 공고 정보가 없습니다. 데이터를 먼저 처리해주세요.[/yellow]")
    # else: ann_ids에 해당하는 data가 없는 경우는 위에서 개별 오류 출력

def display_announcement_detail(pbancSn_str):
    """특정 공고의 상세 정보를 Rich Panel 등으로 표시"""
    data = data_handler.get_announcement_by_id(pbancSn_str)
    if not data:
        rprint(f"[red]공고 ID {pbancSn_str}에 해당하는 정보를 찾을 수 없습니다.[/red]")
        return

    # 기본 정보 패널
    panel_content = (
        f"[bold cyan]제목:[/bold cyan] {data.get('title', 'N/A')}\n"
        f"[bold]기관명:[/bold] {data.get('org_name_ref', 'N/A')} (ID: {data.get('org_id', 'N/A')})\n"
        f"[bold]지역:[/bold] {data.get('region', 'N/A')}\t[bold]접수기간:[/bold] {data.get('application_period', 'N/A')}\n"
        f"[bold]지원분야:[/bold] {data.get('support_field', 'N/A')}\t[bold]창업업력:[/bold] {data.get('startup_experience', 'N/A')}\n"
        f"[bold]대상연령:[/bold] {data.get('target_age', 'N/A')}\t[bold]대상:[/bold] {data.get('target_audience', 'N/A')}\n"
        f"[bold]공고일자:[/bold] {data.get('announcement_date', 'N/A')}\t[bold]공고번호:[/bold] {data.get('announcement_number', 'N/A')}\n"
        f"[bold]담당부서:[/bold] {data.get('department', 'N/A')}\t[bold]연락처:[/bold] {data.get('contact', 'N/A')}\n"
        f"\n[bold green]공고 설명:[/bold green]\n{data.get('description', 'N/A')}"
    )
    console.print(Panel(panel_content, title=f"공고 상세 정보 (ID: {pbancSn_str})", border_style="blue"))

    # 리스트 형태 정보 함수
    def print_list_section(title, items):
        if items and isinstance(items, list):
            rprint(f"\n[bold green]{title}:[/bold green]")
            for item in items:
                rprint(f" - {item}")
        else:
            rprint(f"\n[bold green]{title}:[/bold green] 정보 없음")

    print_list_section("신청방법 및 대상", data.get('application_method'))
    print_list_section("제출서류", data.get('submission_documents'))
    print_list_section("선정절차 및 평가방법", data.get('selection_procedure'))
    print_list_section("지원내용", data.get('support_content'))
    print_list_section("문의처", data.get('inquiry'))

    # 첨부파일
    attachments = data.get('attachments', [])
    if attachments:
        rprint("\n[bold green]첨부파일:[/bold green]")
        for file in attachments:
            rprint(f" - {file.get('name', 'N/A')} (URL: {file.get('url', 'N/A')})") # URL은 콘솔에서 클릭 불가
    else:
        rprint("\n[bold green]첨부파일:[/bold green] 정보 없음")

def display_timeseries_analysis(df, last_n_months=6):
    """시계열 분석 결과를 Rich Table로 개선하여 표시 (최근 N개월, 값 강조)"""
    if df is None or df.empty:
        rprint("[yellow]표시할 분석 결과가 없습니다.[/yellow]")
        return

    # 최근 N개 컬럼(날짜) 선택
    if len(df.columns) > last_n_months:
        df_display = df.iloc[:, -last_n_months:]
        title = f"기관별 공고 게시 빈도 (최근 {last_n_months}개월)"
    else:
        df_display = df
        title = "기관별 공고 게시 빈도 (전체 기간)"


    # DataFrame을 Rich Table로 변환
    table = Table(title=title, show_header=True, header_style="bold purple", box=box.ROUNDED) # box 스타일 적용

    # 첫 번째 컬럼 (기관명 - 인덱스)
    table.add_column("기관명", style="dim", width=20)

    # 나머지 컬럼 (날짜)
    for col_name in df_display.columns:
        # 컬럼 이름이 Timestamp 객체인지 확인 후 처리
        if isinstance(col_name, (pd.Timestamp, datetime)):
             col_header = col_name.strftime('%Y-%m')
        else:
             col_header = str(col_name)
        table.add_column(col_header, justify="right")

    # 데이터 행 추가 및 값 강조
    for org_name, row in df_display.iterrows():
        row_values = []
        for val in row.values:
            if val > 0:
                # 0보다 크면 녹색 굵은 글씨로 표시
                row_values.append(f"[bold green]{val}[/bold green]")
            else:
                # 0이면 흐린 회색으로 표시
                row_values.append(f"[dim white]{val}[/dim white]")
        table.add_row(str(org_name), *row_values)

    console.print(table)
    # 참고: 콘솔에서 실제 차트를 그리려면 plotext 같은 라이브러리 추가 필요
    rprint("[dim](콘솔 차트 표시는 plotext 등 추가 라이브러리 필요)[/dim]")


# --- Main Menu Logic ---

def main_menu():
    """메인 메뉴 표시 및 사용자 입력 처리"""
    while True:
        console.print(Panel(
            "[bold green]K-Startup 공고 관리 프로그램[/bold green]\n\n"
            "1. 원본 데이터 처리 (JSON 분리 및 인덱싱)\n"
            "2. 전체 기관 목록 보기\n"
            "3. 전체 공고 목록 보기\n"
            "4. 공고 검색/필터링\n"
            "5. 공고 상세 정보 보기\n"
            "6. 공고 정보 수정 (간단 구현)\n"
            "7. 공고 정보 삭제 (간단 구현)\n"
            "8. 기관별 공고 빈도 분석 (시계열)\n"
            "9. 종료",
            title="메뉴", border_style="yellow"
        ))

        choice = Prompt.ask("선택", choices=['1', '2', '3', '4', '5', '6', '7', '8', '9'], default='4')

        if choice == '1':
            rprint("\n[cyan]원본 데이터 처리 시작...[/cyan]")
            if os.path.exists(data_handler.RAW_DATA_FILE):
                success = data_handler.process_raw_data()
                if success:
                    rprint("[green]데이터 처리가 완료되었습니다.[/green]")
                else:
                    rprint("[red]데이터 처리 중 오류가 발생했습니다.[/red]")
            else:
                rprint(f"[red]원본 데이터 파일({data_handler.RAW_DATA_FILE})을 찾을 수 없습니다. 먼저 crawler.py를 실행하세요.[/red]")

        elif choice == '2':
            rprint("\n[cyan]전체 기관 목록 조회...[/cyan]")
            orgs = data_handler.get_all_organizations()
            display_organizations(orgs)

        elif choice == '3':
            rprint("\n[cyan]전체 공고 목록 조회...[/cyan]")
            anns = data_handler.get_all_announcements()
            display_announcements_list(list(anns.keys()))

        elif choice == '4':
            rprint("\n[cyan]공고 검색/필터링[/cyan]")
            keyword = Prompt.ask("검색어 (제목 키워드, 비워두려면 Enter)", default="")
            org_name = Prompt.ask("기관명 (비워두려면 Enter)", default="")
            region = Prompt.ask("지역 (비워두려면 Enter)", default="")
            support_field = Prompt.ask("지원분야 (비워두려면 Enter)", default="")

            # 입력값이 없으면 None으로 처리
            keyword = keyword if keyword else None
            org_name = org_name if org_name else None
            region = region if region else None
            support_field = support_field if support_field else None

            found_ids = data_handler.find_announcements(keyword, org_name, region, support_field)
            rprint(f"\n[green]검색 결과: 총 {len(found_ids)}개 공고[/green]")
            display_announcements_list(found_ids)

        elif choice == '5':
            rprint("\n[cyan]공고 상세 정보 보기[/cyan]")
            pbancSn_str = Prompt.ask("상세 정보를 볼 공고 ID (pbancSn) 입력")
            if pbancSn_str.isdigit():
                display_announcement_detail(pbancSn_str)
            else:
                rprint("[red]유효한 공고 ID(숫자)를 입력해주세요.[/red]")

        elif choice == '6':
            rprint("\n[cyan]공고 정보 수정 (간단 구현)[/cyan]")
            pbancSn_str = Prompt.ask("수정할 공고 ID (pbancSn) 입력")
            if not pbancSn_str.isdigit() or not data_handler.get_announcement_by_id(pbancSn_str):
                rprint(f"[red]유효하지 않거나 존재하지 않는 공고 ID입니다: {pbancSn_str}[/red]")
                continue

            # 간단하게 제목만 수정하는 예시
            current_title = data_handler.get_announcement_by_id(pbancSn_str).get('title', '')
            new_title = Prompt.ask(f"새로운 제목 입력 (현재: {current_title})", default=current_title)

            if new_title != current_title:
                if Confirm.ask(f"공고 {pbancSn_str}의 제목을 '{new_title}'(으)로 수정하시겠습니까?"):
                    success = data_handler.update_announcement(pbancSn_str, {"title": new_title})
                    if success:
                        rprint("[green]공고 정보가 수정되었습니다. (참고: 인덱스 반영을 위해 1번 메뉴 재실행 필요할 수 있음)[/green]")
                    else:
                        rprint("[red]공고 정보 수정 중 오류가 발생했습니다.[/red]")
                else:
                    rprint("[yellow]수정을 취소했습니다.[/yellow]")
            else:
                 rprint("[yellow]제목이 변경되지 않아 수정을 건너뛰었습니다.[/yellow]")

        elif choice == '7':
            rprint("\n[cyan]공고 정보 삭제 (간단 구현)[/cyan]")
            pbancSn_str = Prompt.ask("삭제할 공고 ID (pbancSn) 입력")
            if not pbancSn_str.isdigit() or not data_handler.get_announcement_by_id(pbancSn_str):
                rprint(f"[red]유효하지 않거나 존재하지 않는 공고 ID입니다: {pbancSn_str}[/red]")
                continue

            ann_title = data_handler.get_announcement_by_id(pbancSn_str).get('title', '')
            if Confirm.ask(f"정말로 공고 ID {pbancSn_str} ('{ann_title}') 을(를) 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.", default=False):
                success = data_handler.delete_announcement(pbancSn_str)
                if success:
                    rprint("[green]공고 정보가 삭제되었습니다. (참고: 인덱스 반영을 위해 1번 메뉴 재실행 필요할 수 있음)[/green]")
                else:
                    rprint("[red]공고 정보 삭제 중 오류가 발생했습니다.[/red]")
            else:
                rprint("[yellow]삭제를 취소했습니다.[/yellow]")

        elif choice == '8':
            rprint("\n[cyan]기관별 공고 빈도 분석 (월별 시계열)[/cyan]")
            # 날짜 필터링은 여기서 추가 가능 (Prompt 사용)
            ts_data = analysis.get_announcements_timeseries_by_org(freq='ME')
            display_timeseries_analysis(ts_data, last_n_months=6) # 최근 6개월 데이터 표시

        elif choice == '9':
            rprint("[bold blue]프로그램을 종료합니다.[/bold blue]")
            break

        # 메뉴 실행 후 잠시 대기 또는 Enter 키 입력 대기 추가 가능
        Prompt.ask("\n계속하려면 Enter 키를 누르세요...")
        console.clear() # 다음 메뉴 표시 전 화면 지우기 (선택 사항)

# --- 프로그램 시작점 ---

if __name__ == "__main__":
    # 프로그램 시작 시 데이터 초기화 시도
    data_handler.initialize_data()
    # 메인 메뉴 실행
    main_menu() 