import os
from dotenv import load_dotenv
from rich import print
from datetime import datetime, timedelta
from typing import Union, Dict, List, Optional, Tuple
from google.oauth2 import service_account
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build
from service import GoogleService
from utils import (
    transform_datetime_to_date,
    remove_non_words,
)

class GoogleCalendarManager:
    def __init__(self, google_service: GoogleService, calendar_id: str):
        """Initialize Google Calendar Manager."""
        self.SCOPE = ["https://www.googleapis.com/auth/calendar"]
        self.API_SERVICE_NAME = "calendar"
        self.API_VERSION = "v3"
        self.calendar_id = calendar_id
        self.service = google_service.create_service(
            self.API_SERVICE_NAME, self.API_VERSION, self.SCOPE
        )
    
    def get_calendar_data(self, min_week: int) -> List[Dict]:
        """Fetch calendar events."""
        now = datetime.now()
        time_min = (now - timedelta(weeks=min_week)).isoformat() + "Z"
        time_max = (now + timedelta(weeks=52)).isoformat() + "Z"
        
        events = []
        page_token = None
        
        while True:
            events_result = self.service.events().list(
                calendarId=self.calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                timeZone="Asia/Seoul",
                maxResults=250,
                singleEvents=True,
                orderBy="startTime",
                pageToken=page_token,
            ).execute()
            
            events.extend(events_result.get("items", []))
            page_token = events_result.get("nextPageToken")
            
            if not page_token:
                break
        
        return events
    
    @staticmethod
    def transform_calendar_data(calendar_events: List[Dict]) -> List[Dict]:
        """Transform calendar events into structured format."""
        transformed_list = []
        for item in calendar_events:
            if "end" in item:
                event_id = item.get("id")
                summary = item.get("summary")
                summary_trimmed = remove_non_words(summary)
                date_time = item["end"].get("dateTime", item["end"].get("date"))
                transformed_list.append({
                    "event_id": event_id,
                    "summary": summary_trimmed,
                    "dataTime": transform_datetime_to_date(date_time),
                })
        return transformed_list
    
    def update_event_description(
        self, existing_events: List, existing_event_id: List, sheet_data: List[Dict]
    ) -> None:
        """Update existing calendar events with new descriptions."""
        for event in zip(existing_events, existing_event_id):
            for sheet_item in sheet_data:
                try:
                    if event[0] == sheet_item.get("summary"):
                        request_body = self._create_event_body(sheet_item)
                        self.service.events().update(
                            calendarId=self.calendar_id,
                            eventId=event[1],
                            body=request_body
                        ).execute()
                        print(f"이벤트 {event}의 description이 업데이트되었습니다.")
                except HttpError as error:
                    print(f"An error occurred: {error}")
    
    def insert_events(self, new_events: List, sheet_data: List[Dict]) -> None:
        """Insert new events into calendar."""
        for event in new_events:
            for sheet_item in sheet_data:
                try:
                    if event == sheet_item.get("summary"):
                        request_body = self._create_event_body(sheet_item)
                        self.service.events().insert(
                            calendarId=self.calendar_id,
                            body=request_body
                        ).execute()
                        print(f"이벤트 {event}가 생성되었습니다.")
                except HttpError as error:
                    print(f"An error occurred: {error}")
    
    def remove_duplicate_events(self, min_week: int) -> None:
        """Remove duplicate events from calendar."""
        calendar_data = self.get_calendar_data(min_week)
        calendar_data = [
            event for event in calendar_data 
            if event.get("start", {}).get("date")
        ]
        calendar_data.sort(key=lambda x: (x.get("id"), x.get("created")))
        
        unique_events = {}
        for item in calendar_data:
            start_date = item.get("start", {}).get("date")
            summary = item.get("summary")
            
            if summary not in unique_events:
                unique_events[summary] = {
                    "start_date": start_date,
                    "created": item["created"],
                }
            else:
                if (item["created"] != unique_events[summary]["created"] and
                    start_date == unique_events[summary]["start_date"]):
                    try:
                        self.service.events().delete(
                            calendarId=self.calendar_id,
                            eventId=item["id"]
                        ).execute()
                    except HttpError:
                        continue
    
    @staticmethod
    def _create_event_body(event_data: Dict) -> Dict:
        """Create event body for calendar API requests."""
        return {
            "summary": event_data.get("summary"),
            "start": {
                "date": event_data.get("due_date"),
                "timeZone": "Asia/Seoul",
            },
            "end": {
                "date": transform_datetime_to_date(
                    event_data.get("due_date"), 1
                ),
                "timeZone": "Asia/Seoul",
            },
            "description": event_data.get("description"),
        }