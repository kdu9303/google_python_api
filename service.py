import os
import json
from typing import List, Optional
from google.oauth2 import service_account
from googleapiclient.discovery import build


class GoogleService:
    def __init__(self, client_secret_file: Optional[str] = None):
        """구글 서비스 초기화

        Args:
            client_secret_file: 서비스 계정 인증 파일 경로 (선택 사항)
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

    def create_service_json(
        self,
        api_name: str,
        api_version: str,
        scope: List[str],
        json_env_var: str = "CLIENT_SECRET_JSON",
    ):
        """구글 API 서비스 인스턴스를 JSON 환경변수로부터 생성합니다.

        Args:
            api_name: API 서비스 이름
            api_version: API 버전
            scope: API 권한 범위 목록
            json_env_var: JSON 데이터가 저장된 환경변수 키 (기본값: CLIENT_SECRET_JSON)

        Returns:
            구글 API 서비스 인스턴스
        """
        json_string = os.getenv(json_env_var)
        if not json_string:
            raise ValueError(f"{json_env_var} 환경변수가 설정되지 않았습니다.")

        try:
            service_account_info = json.loads(json_string)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON 파싱 오류: {e}")

        credentials = service_account.Credentials.from_service_account_info(
            service_account_info, scopes=scope
        )

        service = build(
            api_name, api_version, credentials=credentials, cache_discovery=False
        )
        return service


if __name__ == "__main__":
    client_secret = GoogleService()
    print(client_secret)
