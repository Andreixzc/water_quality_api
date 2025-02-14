import ee
import os
from google.oauth2 import service_account
from dotenv import load_dotenv

# Carrega as variáveis de ambiente
load_dotenv()

# Obtém o diretório base do projeto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Caminho para o arquivo de credenciais
credentials_path = os.path.join(BASE_DIR, 'processing', 'credentials', 'water-quality-andrei-57d16a92f3ab.json')

print(f"Tentando acessar o arquivo de credenciais em: {credentials_path}")

# Verifica se o arquivo existe
if not os.path.exists(credentials_path):
    raise FileNotFoundError(f"Arquivo de credenciais não encontrado: {credentials_path}")

# Cria as credenciais a partir do arquivo
credentials = service_account.Credentials.from_service_account_file(
    credentials_path,
    scopes=['https://www.googleapis.com/auth/earthengine']
)

# Inicializa o Earth Engine com as credenciais
ee.Initialize(credentials)

# Listar todas as tarefas pendentes
tasks = ee.data.listOperations()

# Cancelar cada tarefa em execução ou pendente
for task in tasks:
    if 'done' not in task or not task['done']:
        ee.data.cancelOperation(task['name'])
        print(f"Tarefa {task['name']} foi cancelada.")