<h1 align="center">Water Quality API</h1>

## Projeto
Este projeto é uma API para análise da qualidade da água baseada em imagens de satélite. Ele utiliza o Google Earth Engine para aquisição de dados e modelos de Machine Learning para estimativas dos parâmetros de qualidade da água. O sistema processa imagens e gera mapas de intensidade a partir das previsões do modelo.

---

## Instruções de Configuração

### Requisitos
- Python 3.10.16
- Google Earth Engine configurado
- Google Drive API ativada
- Banco de dados configurado (se aplicável)

### Criando o Ambiente Virtual
```bash
python -m venv venv
```

### Ativando o Ambiente Virtual
```bash
# Linux/MacOS:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

### Instalando Dependências
```bash
pip install -r requirements.txt
```

---

## Configuração do Google Earth Engine
### Autenticação
1. Crie um projeto no Earth Engine: [Earth Engine Register](https://code.earthengine.google.com/register)
2. No terminal, execute:
   ```bash
   earthengine authenticate
   ```
3. Prossiga com a autenticação no navegador e faça login na sua conta do Google.
4. Após a autenticação, defina o projeto manualmente:
   ```bash
   earthengine set_project 'nome-do-projeto'
   ```

---

## Configuração da Google Drive API
### Ativação da API
1. Acesse o [Google Cloud Console](https://console.cloud.google.com)
2. Crie um novo projeto ou selecione um existente.
3. No menu lateral, vá para "APIs e Serviços" > "Biblioteca".
4. Pesquise por "Google Drive API" e clique em "Ativar".

### Configuração das Credenciais
1. Vá para "APIs e Serviços" > "Credenciais".
2. Clique em "Criar Credenciais" > "ID do Cliente OAuth".
3. Selecione "Aplicativo para Desktop" como tipo de aplicação.
4. Defina um nome para o cliente OAuth e clique em "Criar".

### Download das Credenciais
1. Após a criação, faça o download do arquivo JSON.
2. Renomeie o arquivo para `client_secrets.json`.
3. Mova o arquivo para a pasta `processing/credentials/` do seu projeto.

---

## Configuração do Banco de Dados
Crie um banco de dados no PostgreSQL e ajuste as configurações no arquivo `settings.py`.

Exemplo:
```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "water-quality-db",
        "USER": "postgres",
        "PASSWORD": "admin",
        "HOST": "localhost",
        "PORT": "5432",
    }
}
```

### Criando Migrations
```bash
python manage.py makemigrations
```

### Aplicando Migrations
```bash
python manage.py migrate
```

---

## Executando o Servidor
```bash
python manage.py runserver
```

---

## Documentação das Rotas
A documentação das rotas pode ser encontrada em breve neste repositório.

