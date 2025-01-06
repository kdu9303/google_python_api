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
        """이벤트 동기화 관리자를 초기화합니다.
        
        Args:
            sheet_manager: 구글 시트 관리자 인스턴스
            calendar_manager: 구글 캘린더 관리자 인스턴스
        """
        self.sheet_manager = sheet_manager
        self.calendar_manager = calendar_manager
    
    @staticmethod
    def check_new_events(
        sheet_events: List[Dict],
        calendar_events: List[Dict]
    ) -> Tuple[List, List, List]:
        """시트와 캘린더의 이벤트를 비교하여 새로운 이벤트를 찾습니다.
        
        Args:
            sheet_events: 시트에서 가져온 이벤트 목록
            calendar_events: 캘린더에서 가져온 이벤트 목록
            
        Returns:
            새로운 이벤트 목록, 기존 이벤트 목록, 기존 이벤트 ID 목록을 반환
        """
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
        """특정 기간 내의 이벤트만 필터링합니다.
        
        Args:
            transformed_list: 변환된 이벤트 목록
            min_week: 현재 시점에서 과거로 몇 주 전까지의 데이터를 가져올지 지정
            
        Returns:
            필터링된 이벤트 목록
        """
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
    year: int = 2025
    sheet_range: str = "C5:K"
    
    load_dotenv()
    
    # Initialize services
    google_service = GoogleService(os.getenv("CLIENT_SECRET_FILE"))
    sheet_manager = GoogleSheetManager(google_service, os.getenv("SHEET_ID"))
    calendar_manager = GoogleCalendarManager(google_service, os.getenv("CALENDAR_ID"))
    synchronizer = EventSynchronizer(sheet_manager, calendar_manager)
    
    # Get and transform sheet data
    sheet_events = sheet_manager.get_sheet_data(f"{year}년!{sheet_range}")
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
        # print(new_events)  # 새로운 이벤트 list목록 확인용
        calendar_manager.insert_events(new_events, sheet_data)

if __name__ == "__main__":
    main()