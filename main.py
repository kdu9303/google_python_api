import os
from dotenv import load_dotenv
from rich import print
from datetime import datetime, timedelta
from typing import Union, Dict, List, Optional, Tuple
from service import GoogleService
from sheet_manager import GoogleSheetManager
from calendar_manager import GoogleCalendarManager
from utils import (
    transform_datetime_to_date,
    transform_range_date_to_date,
    remove_non_words,
    find_non_matched_items,
)


class EventSynchronizer:
    def __init__(
        self,
        sheet_manager: GoogleSheetManager,
        calendar_manager: GoogleCalendarManager
    ):
        """Initialize Event Synchronizer."""
        self.sheet_manager = sheet_manager
        self.calendar_manager = calendar_manager
    
    @staticmethod
    def check_new_events(
        sheet_events: List[Dict],
        calendar_events: List[Dict]
    ) -> Tuple[List, List, List]:
        """Compare sheet and calendar events to find new events."""
        new_events = [event.get("summary") for event in sheet_events]
        existing_events = [event.get("summary") for event in calendar_events]
        existing_event_id = [event.get("event_id") for event in calendar_events]
        
        new_event_list = find_non_matched_items(new_events, existing_events)
        new_event_list = list(filter(None, new_event_list))
        
        return new_event_list, existing_events, existing_event_id
    
    @staticmethod
    def limit_calendar_data_by_datetime(
        transformed_list: List[Dict],
        min_week: int
    ) -> List[Dict]:
        """Filter events by date range."""
        limited_list = []
        now = datetime.now()
        time_min = (now - timedelta(weeks=min_week)).isoformat()
        time_min = datetime.fromisoformat(time_min).date()
        
        for item in transformed_list:
            try:
                due_date = datetime.strptime(
                    item.get("due_date"), "%Y-%m-%d"
                ).date()
                if due_date >= time_min:
                    limited_list.append(item)
            except ValueError as e:
                print(f"날짜형식 오류 in {item}: {e}")
                continue
        
        return limited_list

def main():
    load_dotenv()
    
    # Initialize services
    google_service = GoogleService(os.getenv("CLIENT_SECRET_FILE"))
    sheet_manager = GoogleSheetManager(google_service, os.getenv("SHEET_ID"))
    calendar_manager = GoogleCalendarManager(google_service, os.getenv("CALENDAR_ID"))
    synchronizer = EventSynchronizer(sheet_manager, calendar_manager)
    
    # Get and transform sheet data
    sheet_events = sheet_manager.get_sheet_data("2024년!C5:K")
    sheet_data = sheet_manager.transform_sheet_data(sheet_events)
    filtered_sheet_data = synchronizer.limit_calendar_data_by_datetime(
        sheet_data, 25
    )
    
    # Get and transform calendar data
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
        print(new_events)
        calendar_manager.insert_events(new_events, sheet_data)

if __name__ == "__main__":
    main()