import ee
import os
from google.oauth2 import service_account
from dotenv import load_dotenv

# Carrega as variáveis de ambiente
load_dotenv()

# Get credentials path from environment variable
credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')

if not credentials_path:
    raise ValueError("GOOGLE_APPLICATION_CREDENTIALS environment variable not set")

print(f"Tentando acessar o arquivo de credenciais em: {credentials_path}")

# Verifica se o arquivo existe
if not os.path.exists(credentials_path):
    raise FileNotFoundError(f"Arquivo de credenciais não encontrado: {credentials_path}")

# Get the delegated user email from environment variable
delegated_user = os.environ.get('GOOGLE_DELEGATED_USER')

# Create service account credentials with delegation
scopes = [
    'https://www.googleapis.com/auth/earthengine',
    'https://www.googleapis.com/auth/drive'
]

credentials = service_account.Credentials.from_service_account_file(
    credentials_path,
    scopes=scopes
)

# If delegated user is specified, use delegation
if delegated_user:
    credentials = credentials.with_subject(delegated_user)
    print(f"Using delegated user: {delegated_user}")
else:
    print("Warning: No delegated user specified.")

# Inicializa o Earth Engine com as credenciais
ee.Initialize(credentials)

# Listar todas as tarefas pendentes
tasks = ee.data.listOperations()

# Cancelar cada tarefa em execução ou pendente
for task in tasks:
    if 'done' not in task or not task['done']:
        ee.data.cancelOperation(task['name'])
        print(f"Tarefa {task['name']} foi cancelada.")