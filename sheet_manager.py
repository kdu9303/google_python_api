from rich import print
from typing import Dict, List
from service import GoogleService
from utils import (
    transform_range_date_to_date,
    remove_non_words,
)


class GoogleSheetManager:
    def __init__(self, google_service: GoogleService, sheet_id: str):
        """Initialize Google Sheet Manager."""
        self.SCOPE = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
        self.API_SERVICE_NAME = "sheets"
        self.API_VERSION = "v4"
        self.sheet_id = sheet_id
        self.service = google_service.create_service(
            self.API_SERVICE_NAME, self.API_VERSION, self.SCOPE
        )

    def get_sheet_data(self, sheet_range: str) -> List:
        """Fetch data from Google Sheet."""
        sheet = self.service.spreadsheets()
        event_list = (
            sheet.values()
            .get(
                spreadsheetId=self.sheet_id,
                range=sheet_range,
            )
            .execute()
        )
        return event_list.get("values", [])

    @staticmethod
    def transform_sheet_data(sheet_events: List) -> List[Dict]:
        """Transform sheet data into structured format."""
        transformed_list = []

        try:
            for item in sheet_events:
                if item:
                    summary = remove_non_words(item[3])
                    due_date = item[4]
                    description = (
                        f"사이트: {item[0]}\n"
                        f"지역: {item[2]}\n"
                        f"제공내역: {item[6]}\n"
                        f"비고: {item[8] if len(item) > 8 else '없음'}"
                    )
                    transformed_list.append(
                        {
                            "summary": summary,
                            "due_date": transform_range_date_to_date(due_date),
                            "description": description,
                        }
                    )
        except IndexError as e:
            print(e)

        return transformed_list
