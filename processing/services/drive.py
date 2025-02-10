import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import pickle
import io
from typing import List, Dict

class DriveService:
    """
    Serviço para gerenciar interações com o Google Drive, incluindo autenticação e 
    operações com arquivos.

    Esta classe gerencia todo o ciclo de autenticação OAuth2 com o Google Drive e
    fornece métodos para baixar arquivos de pastas específicas.

    Attributes:
        SCOPES (List[str]): Escopos de autorização necessários para acessar o Google Drive
        base_path (str): Caminho base do projeto
        credentials_dir (str): Diretório onde as credenciais são armazenadas
        credentials_path (str): Caminho para o arquivo de segredos do cliente
        token_path (str): Caminho para o arquivo de token salvo
        credentials (Credentials): Objeto de credenciais do Google
        service: Instância do serviço Google Drive

    Example:
        >>> drive_service = DriveService()
        >>> files = drive_service.download_folder_contents("my_folder", tasks_info)
    """

    def __init__(self):
        """
        Inicializa o serviço do Google Drive, configurando caminhos e autenticação.
        
        O construtor configura os caminhos necessários para os arquivos de credenciais,
        cria o diretório de credenciais se não existir e inicializa a conexão com o
        serviço do Google Drive.
        """
        self.SCOPES = [
            'https://www.googleapis.com/auth/drive',  # Acesso total ao Drive
            'https://www.googleapis.com/auth/drive.file',  # Acesso aos arquivos criados pelo app
            'https://www.googleapis.com/auth/drive.metadata.readonly'  # Leitura de metadados
        ]
        # Define caminhos relativos à raiz do projeto
        self.base_path = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.credentials_dir = os.path.join(self.base_path, 'processing', 'credentials')
        self.credentials_path = os.path.join(self.credentials_dir, 'client_secrets.json')
        self.token_path = os.path.join(self.credentials_dir, 'token.pickle')
        
        # Cria diretório de credenciais se não existir
        if not os.path.exists(self.credentials_dir):
            os.makedirs(self.credentials_dir)
            
        self.credentials = self._get_credentials()
        self.service = build('drive', 'v3', credentials=self.credentials)
    
    def _get_credentials(self):
        """
        Obtém ou atualiza as credenciais de autenticação do Google Drive.

        Este método verifica se existem credenciais válidas salvas. Se não existirem
        ou estiverem expiradas, inicia o fluxo OAuth2 para obter novas credenciais.

        Returns:
            google.oauth2.credentials.Credentials: Objeto de credenciais válido

        Raises:
            FileNotFoundError: Se o arquivo client_secrets.json não for encontrado
        """
        credentials = None
        
        # Verifica token existente
        if os.path.exists(self.token_path):
            print(f"Loading credentials from {self.token_path}")
            with open(self.token_path, 'rb') as token:
                credentials = pickle.load(token)
        
        # Se as credenciais não existem ou são inválidas
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
            
            # Salva credenciais para uso futuro
            print(f"Saving credentials to {self.token_path}")
            with open(self.token_path, 'wb') as token:
                pickle.dump(credentials, token)
        
        return credentials

    def download_folder_contents(self, folder_name: str, tasks_info: List[Dict]) -> list:
        """
        Baixa todos os arquivos de uma pasta específica do Google Drive.

        Este método busca uma pasta pelo nome, lista todos os arquivos TIFF dentro dela,
        baixa cada arquivo e opcionalmente os deleta após o download. Também associa
        informações de nuvem de cada imagem baseado nas tasks_info fornecidas.

        Args:
            folder_name (str): Nome da pasta no Google Drive
            tasks_info (List[Dict]): Lista de dicionários contendo informações das tasks,
                                   incluindo filename e cloud_percentage

        Returns:
            list: Lista de tuplas contendo (conteúdo_arquivo, nome_arquivo, porcentagem_nuvem)
                 para cada arquivo baixado

        Raises:
            ValueError: Se a pasta especificada não for encontrada no Drive

        Example:
            >>> tasks_info = [{'filename': 'img1', 'cloud_percentage': 20.5}]
            >>> files = drive_service.download_folder_contents("satellite_images", tasks_info)
            >>> for content, name, cloud_pct in files:
            ...     print(f"{name}: {cloud_pct}% cloud coverage")
        """
        print(f"Downloading contents from folder: {folder_name}")
        print("Received tasks_info:", tasks_info)
        
        # Busca a pasta
        folder_results = self.service.files().list(
            q=f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder'",
            fields="files(id, name)"
        ).execute()
        
        if not folder_results['files']:
            raise ValueError(f"Folder {folder_name} not found")
        
        folder_id = folder_results['files'][0]['id']
        print(f"Found folder with ID: {folder_id}")
        
        # Busca arquivos na pasta
        file_results = self.service.files().list(
            q=f"'{folder_id}' in parents and mimeType='image/tiff'",
            fields="files(id, name)"
        ).execute()
        
        downloaded_files = []
        for file in file_results.get('files', []):
            # Associa informações da task com o arquivo
            task_info = next(
                (task for task in tasks_info if task['filename'] == file['name'].rstrip('.tif')), 
                None
            )
            cloud_percentage = task_info['cloud_percentage'] if task_info else None
            
            print(f"File: {file['name']}, Found task_info: {task_info is not None}, "
                  f"Cloud percentage: {cloud_percentage}")

            # Download do arquivo
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
            
            # Delete o arquivo do Drive após o download
            self.service.files().delete(fileId=file['id']).execute()
            print(f"Deleted file from Drive: {file['name']}")
        
        return downloaded_files