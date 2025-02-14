import os
from google.oauth2 import service_account
import googleapiclient.discovery
import ee

class AuthService:
    def __init__(self):
        self.SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/earthengine']
        self.credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        if not self.credentials_path:
            raise ValueError("GOOGLE_APPLICATION_CREDENTIALS environment variable not set")
        self.credentials = self._get_credentials()

    def _get_credentials(self):
        if not os.path.exists(self.credentials_path):
            raise FileNotFoundError(f"Credentials file not found at {self.credentials_path}")
        return service_account.Credentials.from_service_account_file(
            self.credentials_path, scopes=self.SCOPES)

    def initialize_services(self):
        # Initialize Google Drive
        drive_service = googleapiclient.discovery.build('drive', 'v3', credentials=self.credentials)

        # Initialize Earth Engine
        ee.Initialize(credentials=self.credentials)

        return drive_service

# Usage
auth_service = AuthService()
drive_service = auth_service.initialize_services()