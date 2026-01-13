import os
from dotenv import load_dotenv
from rich import print
from service import GoogleService
from sheet_manager import GoogleSheetManager
from calendar_manager import GoogleCalendarManager
from event_handler import EventSynchronizer


def main():
    year: int = 2026
    sheet_range: str = "E5:M"

    load_dotenv()

    client_secret = os.getenv("CLIENT_SECRET_FILE")
    sheet_id = os.getenv("SHEET_ID")
    if not sheet_id:
        raise ValueError("SHEET_ID 환경 변수가 설정되지 않았습니다.")
    calendar_id = os.getenv("CALENDAR_ID")
    if not calendar_id:
        raise ValueError("CALENDAR_ID 환경 변수가 설정되지 않았습니다.")

    # Initialize services
    if not client_secret:
        # create_service_json()사용
        google_service = GoogleService()
    google_service = GoogleService(client_secret)

    sheet_manager = GoogleSheetManager(google_service, sheet_id)
    calendar_manager = GoogleCalendarManager(google_service, calendar_id)
    synchronizer = EventSynchronizer(sheet_manager, calendar_manager)

    # 구글 시트 데이터 변환
    sheet_events = sheet_manager.get_sheet_data(f"{year}년!{sheet_range}")
    sheet_data = sheet_manager.transform_sheet_data(sheet_events)
    filtered_sheet_data = synchronizer.limit_calendar_data_by_datetime(sheet_data, 25)

    # 캘린더 데이터 json형태로 변환
    calendar_events = calendar_manager.get_calendar_data(min_week=26)
    calendar_data = calendar_manager.transform_calendar_data(calendar_events)

    # Check for new events and update/insert as needed
    new_events, existing_events, existing_ids = synchronizer.check_new_events(
        filtered_sheet_data, calendar_data
    )

    # 기존 이벤트의 정보 업데이트 필요시
    # if existing_events:
    #     calendar_manager.update_event_description(
    #         existing_events, existing_ids, sheet_data
    #     )

    if new_events:
        # print(new_events)  # 새로운 이벤트 list목록 확인용
        calendar_manager.insert_events(new_events, sheet_data)


if __name__ == "__main__":
    main()
