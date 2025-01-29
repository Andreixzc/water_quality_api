# processing/services/drive.py

import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import pickle
import io

class DriveService:
    def __init__(self):
        self.SCOPES = [
        'https://www.googleapis.com/auth/drive',  # Full Drive access
        'https://www.googleapis.com/auth/drive.file',  # Access to files created by the app
        'https://www.googleapis.com/auth/drive.metadata.readonly'  # Read metadata
    ]
        # Define paths relative to the project root
        self.base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.credentials_dir = os.path.join(self.base_path, 'processing', 'credentials')
        self.credentials_path = os.path.join(self.credentials_dir, 'client_secrets.json')
        self.token_path = os.path.join(self.credentials_dir, 'token.pickle')
        
        # Create credentials directory if it doesn't exist
        if not os.path.exists(self.credentials_dir):
            os.makedirs(self.credentials_dir)
            
        self.credentials = self._get_credentials()
        self.service = build('drive', 'v3', credentials=self.credentials)
    
    def _get_credentials(self):
        """Gets valid user credentials from storage or initiates OAuth2 flow."""
        credentials = None
        
        # Check for existing token
        if os.path.exists(self.token_path):
            print(f"Loading credentials from {self.token_path}")
            with open(self.token_path, 'rb') as token:
                credentials = pickle.load(token)
        
        # If credentials don't exist or are invalid
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                print("Refreshing expired credentials")
                credentials.refresh(Request())
            else:
                print(f"Getting new credentials using client secrets from {self.credentials_path}")
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"Client secrets file not found at {self.credentials_path}. "
                        "Please download it from Google Cloud Console and place it in the credentials directory."
                    )
                    
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path,
                    self.SCOPES
                )
                credentials = flow.run_local_server(port=0)
            
            # Save credentials for future use
            print(f"Saving credentials to {self.token_path}")
            with open(self.token_path, 'wb') as token:
                pickle.dump(credentials, token)
        
        return credentials

    def download_folder_contents(self, folder_name: str, local_path: str) -> list:
        """Downloads all files from a Google Drive folder to a local directory."""
        print(f"Downloading contents from folder: {folder_name} to {local_path}")
        
        # Create local directory if it doesn't exist
        os.makedirs(local_path, exist_ok=True)
        
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
        
        print(f"Found {len(file_results.get('files', []))} files to download")
        for file in file_results.get('files', []):
            print(f"Downloading file: {file['name']}")
            request = self.service.files().get_media(fileId=file['id'])
            file_path = os.path.join(local_path, file['name'])
            
            with io.FileIO(file_path, 'wb') as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    _, done = downloader.next_chunk()
            
            downloaded_files.append(file_path)
            print(f"Successfully downloaded: {file_path}")
            
            # Optionally delete the file from Drive after downloading
            self.service.files().delete(fileId=file['id']).execute()
            print(f"Deleted file from Drive: {file['name']}")
        
        return downloaded_files