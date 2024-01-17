import os
from dotenv import load_dotenv
from rich import print
from datetime import datetime, timedelta
from typing import Union, Dict, List
from google.oauth2 import service_account
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from utils import (
    transform_datetime_to_date,
    transform_range_date_to_date,
    remove_non_words,
    find_non_matched_items,
)


# load_dotenv(dotenv_path="./venv/.env")
load_dotenv()

CLIENT_SECRET_FILE = os.getenv("CLIENT_SECRET_FILE")

# google sheet
SHEET_SCOPE = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
SHEET_API_SERVICE_NAME = "sheets"
SHEET_API_VERSION = "v4"
SHEET_ID = os.getenv("SHEET_ID")
SHEET_RANGE = "2024년!C5:K"


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
                description = f"사이트: {item[0]}\n지역: {item[2]}\n제공내역: {item[6]}\n비고: {item[8] if len(item) > 8 else '없음'}"  # noqa
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


def get_calendar_data(calendar_id, min_week) -> List[Dict]:
    calender_service = create_service(
        CLIENT_SECRET_FILE,
        CALENDAR_API_SERVICE_NAME,
        CALENDAR_API_VERSION,
        CALENDAR_SCOPE,
    )

    now = datetime.now()
    time_min = (now - timedelta(weeks=min_week)).isoformat() + "Z"
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
            event_id = item.get("id")
            summary = item.get("summary")
            summary_trimmed = remove_non_words(summary)
            date_time = item["end"].get("dateTime", item["end"].get("date"))
            transformed_list.append(
                {
                    "event_id": event_id,
                    "summary": summary_trimmed,
                    "dataTime": transform_datetime_to_date(date_time),
                }
            )
    return transformed_list


def limit_calendar_data_by_datetime(
    transformed_list: List[Dict], min_week: str
) -> List[Dict]:
    limited_list = []

    # 현재 시간을 ISO 형식으로 변환하고, Z 를 제거합니다.
    now = datetime.now()
    time_min = (now - timedelta(weeks=min_week)).isoformat()
    time_min = datetime.fromisoformat(time_min).date()
    # print(time_min)

    for item in transformed_list:
        try:
            due_date = datetime.strptime(item.get("due_date"), "%Y-%m-%d").date()
            if due_date >= time_min:
                limited_list.append(item)
        except ValueError as e:
            print(f"Invalid date format in {item}: {e}")
            continue  # Skip this item
    return limited_list


def check_new_events(
    sheet_new_events: List[Dict], calendar_events: List[Dict]
) -> Union[List, List]:
    new_events = [event.get("summary") for event in sheet_new_events]
    existing_events = [event.get("summary") for event in calendar_events]
    existing_event_id = [event.get("event_id") for event in calendar_events]

    new_event_list = find_non_matched_items(new_events, existing_events)
    new_event_list = list(filter(None, new_event_list))

    return new_event_list, existing_events, existing_event_id


def update_event_description(
    calander_id,
    existing_events: List,
    existing_event_id: List,
    sheet_extracted_data: List[Dict],
):
    calender_service = create_service(
        CLIENT_SECRET_FILE,
        CALENDAR_API_SERVICE_NAME,
        CALENDAR_API_VERSION,
        CALENDAR_SCOPE,
    )

    for event in zip(existing_events, existing_event_id):
        for sheet_data in sheet_extracted_data:
            try:
                if event[0] == sheet_data.get("summary"):
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

                    calender_service.events().update(
                        calendarId=calander_id, eventId=event[1], body=request_body
                    ).execute()

                    print(f"이벤트 {event}의 description이 업데이트되었습니다.")
            except HttpError as error:
                print("An error occurred: %s" % (error))

    print("모든 이벤트의 description이 성공적으로 업데이트되었습니다.")


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


def remove_duplicate_events(calendar_id, min_week):
    calender_service = create_service(
        CLIENT_SECRET_FILE,
        CALENDAR_API_SERVICE_NAME,
        CALENDAR_API_VERSION,
        CALENDAR_SCOPE,
    )

    # get raw calendar data
    calendar_extracted_data = get_calendar_data(calendar_id, min_week)

    # filter out events with missing or invalid start date
    calendar_extracted_data = [
        event for event in calendar_extracted_data if event.get("start", {}).get("date")
    ]

    calendar_extracted_data.sort(key=lambda x: (x.get("id"), x.get("created")))

    # create a dictionary to hold unique events
    unique_events = {}

    for item in calendar_extracted_data:
        start_date = item.get("start", {}).get("date")
        summary = item.get("summary")


        if summary not in unique_events:
            # 첫 이벤트만 캐시에 저장
            unique_events[summary] = {
                "start_date": start_date,
                "created": item["created"],
            }

        else:
            if (item["created"] != unique_events[summary]["created"]) and (
                start_date == unique_events[summary]["start_date"]
            ):
                try:
                # print(item.get('id') + " "+ item.get('summary') + ", 시작일:" + item.get("start").get("date") + ", 종료일:" + item.get("end").get("date") + ", 생성일:" + item.get('created') )

                    calender_service.events().delete(
                        calendarId=calendar_id, eventId=item["id"]
                    ).execute()
                except HttpError:
                    continue


def main():
    # GoogleSheet 이벤트 목록 가져오기
    sheet_event_list = get_sheet_data(SHEET_ID, SHEET_RANGE)
    sheet_extracted_data = transform_sheet_data(sheet_event_list)
    # print(sheet_extracted_data)

    time_filtered_sheet_data = limit_calendar_data_by_datetime(
        transformed_list=sheet_extracted_data, min_week=26
    )
    # print(time_filtered_sheet_data)

    # 달력 이벤트 목록 가져오기
    calendar_event_list = get_calendar_data(calendar_id=CALENDAR_ID, min_week=26)
    calendar_extracted_data = transform_calendar_data(calendar_event_list)
    # print(calendar_extracted_data)

    # GoogleSheet 이벤트 목록과 달력 이벤트 목록을 비교해서 새로운 이벤트과 기존 이미지를 가져온다
    new_event_list, existing_list, existing_event_id = check_new_events(
        time_filtered_sheet_data, calendar_extracted_data
    )
    # print(set(new_event_list))
    # 기존 이벤트 업데이트
    # if existing_list:
        # update_event_description(CALENDAR_ID, existing_list, existing_event_id, sheet_extracted_data)
    # print(existing_list, existing_event_id)
    # 이벤트 달력에 삽입
    if new_event_list:
        insert_events(CALENDAR_ID, new_event_list, sheet_extracted_data)


if __name__ == "__main__":
    main()
    # remove_duplicate_events(CALENDAR_ID, 52)
