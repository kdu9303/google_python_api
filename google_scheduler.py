import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from typing import Dict, List
from google.oauth2 import service_account
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from utils import (
    transform_datetime_to_date,
    transform_range_date_to_date,
    remove_non_words,
    find_non_matched_items,
)

load_dotenv(dotenv_path="./venv/.env")

CLIENT_SECRET_FILE = os.getenv("CLIENT_SECRET_FILE")

# google sheet
SHEET_SCOPE = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
SHEET_API_SERVICE_NAME = "sheets"
SHEET_API_VERSION = "v4"
SHEET_ID = os.getenv("SHEET_ID")
SHEET_RANGE = "2023년!C5:M"


# google calander
CALENDAR_SCOPE = ["https://www.googleapis.com/auth/calendar"]
CALENDAR_API_SERVICE_NAME = "calendar"
CALENDAR_API_VERSION = "v3"
CALENDAR_ID = os.getenv("CALENDAR_ID")


def create_service(
    client_secret_file: Dict[str, str],
    api_name: str,
    api_version: str,
    scope,
):

    CLIENT_SECRET_FILE = client_secret_file
    API_SERVICE_NAME = api_name
    API_VERSION = api_version
    SCOPES = scope

    # IAM 및 관리자 -> 서비스 계정 -> JSON 키 새로 발급
    credentials = service_account.Credentials.from_service_account_file(
        CLIENT_SECRET_FILE, scopes=SCOPES
    )

    service = build(
        API_SERVICE_NAME, API_VERSION, credentials=credentials, cache_discovery=False
    )

    return service


def get_sheet_data(sheet_id: str, sheet_range: str) -> List:

    sheet_service = create_service(
        CLIENT_SECRET_FILE, SHEET_API_SERVICE_NAME, SHEET_API_VERSION, SHEET_SCOPE
    )
    sheet = sheet_service.spreadsheets()
    event_list: Dict[str, str] = (
        sheet.values()
        .get(
            spreadsheetId=sheet_id,
            range=sheet_range,
        )
        .execute()
    )
    events: List = event_list.get("values", [])
    return events


def transform_sheet_data(sheet_events):
    transformed_list = []

    try:
        for item in sheet_events:
            if item:
                summary = remove_non_words(item[3])
                due_date = item[4]
                description = f"사이트: {item[0]}\n지역: {item[2]}\n제공내역: {item[6]}\n비고: {item[9] if len(item) > 9 else '없음'}"  # noqa
                transformed_list.append(
                    {
                        "summary": summary,
                        "due_date": transform_range_date_to_date(due_date),
                        "description": description,
                    }
                )
    except IndexError as e:
        print(e)
        pass
    return transformed_list


def get_calendar_data(calendar_id) -> List[Dict]:

    calender_service = create_service(
        CLIENT_SECRET_FILE,
        CALENDAR_API_SERVICE_NAME,
        CALENDAR_API_VERSION,
        CALENDAR_SCOPE,
    )

    now = datetime.now()
    time_min = (now - timedelta(weeks=26)).isoformat() + "Z"
    time_max = (now + timedelta(weeks=52)).isoformat() + "Z"

    events_result = (
        calender_service.events()
        .list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            timeZone="Asia/Seoul",
            maxResults=250,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    events = events_result.get("items", [])
    next_page_token = events_result.get("nextPageToken")

    while next_page_token:
        events_result = (
            calender_service.events()
            .list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                timeZone="Asia/Seoul",
                maxResults=250,
                singleEvents=True,
                orderBy="startTime",
                pageToken=next_page_token,
            )
            .execute()
        )
    events.extend(events_result.get("items", []))
    next_page_token = events_result.get("nextPageToken")

    return events


def transform_calendar_data(calender_events) -> List[Dict]:
    transformed_list = []
    for item in calender_events:
        if "end" in item:
            summary = item.get("summary")
            summary_trimmed = remove_non_words(summary)
            date_time = item["end"].get("dateTime", item["end"].get("date"))
            transformed_list.append(
                {
                    "summary": summary_trimmed,
                    "dataTime": transform_datetime_to_date(date_time),
                }
            )
    return transformed_list


def check_new_events(sheet_new_events: List[Dict], calendar_events: List[Dict]) -> List:

    new_events = [event.get("summary") for event in sheet_new_events]
    existing_events = [event.get("summary") for event in calendar_events]

    new_event_list = find_non_matched_items(new_events, existing_events)
    new_event_list = list(filter(None, new_event_list))

    return new_event_list


def insert_events(calander_id, new_events: List, sheet_extracted_data: List[Dict]):
    calender_service = create_service(
        CLIENT_SECRET_FILE,
        CALENDAR_API_SERVICE_NAME,
        CALENDAR_API_VERSION,
        CALENDAR_SCOPE,
    )

    for event in new_events:
        for sheet_data in sheet_extracted_data:
            try:
                if event == sheet_data.get("summary"):
                    request_body = {
                        "summary": sheet_data.get("summary"),
                        "start": {
                            "date": sheet_data.get("due_date"),
                            "timeZone": "Asia/Seoul",
                        },
                        "end": {
                            "date": transform_datetime_to_date(
                                sheet_data.get("due_date"), 1
                            ),
                            "timeZone": "Asia/Seoul",
                        },
                        "description": sheet_data.get("description"),
                    }

                    calender_service.events().insert(
                        calendarId=calander_id, body=request_body
                    ).execute()

                    print(f"이벤트 {event}가 생성되었습니다.")
            except HttpError as error:
                print("An error occurred: %s" % (error))

    print("모든 이벤트가 성공적으로 입력되었습니다.")


def main():
    # GoogleSheet 이벤트 목록 가져오기
    sheet_event_list = get_sheet_data(SHEET_ID, SHEET_RANGE)
    sheet_extracted_data = transform_sheet_data(sheet_event_list)

    # 달력 이벤트 목록 가져오기
    calendar_event_list = get_calendar_data(CALENDAR_ID)
    calendar_extracted_data = transform_calendar_data(calendar_event_list)

    # GoogleSheet 이벤트 목록과 달력 이벤트 목록을 비교해서 새로운 이벤트만 가져온다
    new_event_list = check_new_events(sheet_extracted_data, calendar_extracted_data)

    # 이벤트 달력에 삽입
    if new_event_list:
        insert_events(CALENDAR_ID, new_event_list, sheet_extracted_data)


if __name__ == "__main__":
    main()
