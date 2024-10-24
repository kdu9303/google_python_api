from typing import List
from google.oauth2 import service_account
from googleapiclient.discovery import build


class GoogleService:
    def __init__(self, client_secret_file: str):
        self.client_secret_file = client_secret_file

    def create_service(self, api_name: str, api_version: str, scope: List[str]):

        credentials = service_account.Credentials.from_service_account_file(
            self.client_secret_file, scopes=scope
        )

        service = build(
            api_name, api_version, credentials=credentials, cache_discovery=False
        )
        return service
