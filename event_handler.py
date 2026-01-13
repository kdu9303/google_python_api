from rich import print
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from sheet_manager import GoogleSheetManager
from calendar_manager import GoogleCalendarManager
from utils import (
    find_non_matched_items,
)


class EventSynchronizer:
    def __init__(
        self, sheet_manager: GoogleSheetManager, calendar_manager: GoogleCalendarManager
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
        sheet_events: List[Dict], calendar_events: List[Dict]
    ) -> Tuple[List, List, List]:
        """시트와 캘린더의 이벤트를 비교하여 새로운 이벤트를 찾습니다.

        Args:
            sheet_events: 시트에서 가져온 이벤트 목록
            calendar_events: 캘린더에서 가져온 이벤트 목록

        Returns:
            새로운 이벤트 목록, 기존 이벤트 목록, 기존 이벤트 ID 목록을 반환
        """

        # summary: 이벤트 이름
        new_events = [event.get("summary") for event in sheet_events]
        existing_events = [event.get("summary") for event in calendar_events]
        existing_event_id = [event.get("event_id") for event in calendar_events]

        new_event_list = find_non_matched_items(new_events, existing_events)
        new_event_list = list(filter(None, new_event_list))

        return new_event_list, existing_events, existing_event_id

    @staticmethod
    def limit_calendar_data_by_datetime(
        transformed_list: List[Dict], min_week: int
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
                    item.get("due_date"), "%Y-%m-%d"  # type: ignore
                ).date()

                if due_date >= time_min:
                    limited_list.append(item)
            except ValueError as e:
                print(f"날짜형식 오류 in {item}: {e}")
                continue

        return limited_list
