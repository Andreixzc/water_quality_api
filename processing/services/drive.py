import os
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import pickle
import io
from typing import List, Dict
from typing import List, Dict

class DriveService:
    def __init__(self):
        self.SCOPES = [
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/drive.file',
            'https://www.googleapis.com/auth/drive.metadata.readonly'
        ]
        self.credentials = self._get_credentials()
        self.service = build('drive', 'v3', credentials=self.credentials)

    def _get_credentials(self):
        credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        if not credentials_path:
            raise ValueError("GOOGLE_APPLICATION_CREDENTIALS environment variable not set")
        
        return service_account.Credentials.from_service_account_file(
            credentials_path, scopes=self.SCOPES)

    def download_folder_contents(self, folder_name: str, tasks_info: List[Dict]) -> list:
        """Downloads all files from a Google Drive folder and returns their content."""
        print(f"Downloading contents from folder: {folder_name}")
        print("Received tasks_info:", tasks_info)  # Debug print
        # Search for the folder
        print(f"Searching for folder: {folder_name}")
        folder_results = self.service.files().list(
            q=f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'",
            fields="files(id, name)"
        ).execute()
        
        if not folder_results['files']:
            raise ValueError(f"Folder {folder_name} not found")
        
        folder_id = folder_results['files'][0]['id']
        print(f"Found folder with ID: {folder_id}")
        
        # Search for files in the folder
        print("Searching for files in folder")
        file_results = self.service.files().list(
            q=f"'{folder_id}' in parents and mimeType='image/tiff'",
            fields="files(id, name)"
        ).execute()
        
        downloaded_files = []
        for file in file_results.get('files', []):
            task_info = next((task for task in tasks_info if task['filename'] == file['name'].rstrip('.tif')), None)
            cloud_percentage = task_info['cloud_percentage'] if task_info else None
            print(f"File: {file['name']}, Found task_info: {task_info is not None}, Cloud percentage: {cloud_percentage}")

            print(f"Downloading file: {file['name']}")
            request = self.service.files().get_media(fileId=file['id'])
            
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            
            file_content.seek(0)
            
            downloaded_files.append((file_content.getvalue(), file['name'], cloud_percentage))
            print(f"Successfully downloaded: {file['name']} with cloud percentage: {cloud_percentage}")
            
            # Optionally delete the file from Drive after downloading
            self.service.files().delete(fileId=file['id']).execute()
            print(f"Deleted file from Drive: {file['name']}")
        
        return downloaded_files