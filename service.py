from typing import List
from google.oauth2 import service_account
from googleapiclient.discovery import build


class GoogleService:
    def __init__(self, client_secret_file: str):
        """구글 서비스 초기화
        
        Args:
            client_secret_file: 서비스 계정 인증 파일 경로
        """
        self.client_secret_file = client_secret_file

    def create_service(self, api_name: str, api_version: str, scope: List[str]):
        """구글 API 서비스 인스턴스를 생성합니다.
        
        Args:
            api_name: API 서비스 이름 (예: "sheets", "calendar")
            api_version: API 버전
            scope: API 권한 범위 목록
            
        Returns:
            구글 API 서비스 인스턴스
        """

        credentials = service_account.Credentials.from_service_account_file(
            self.client_secret_file, scopes=scope
        )

        service = build(
            api_name, api_version, credentials=credentials, cache_discovery=False
        )
        return service
