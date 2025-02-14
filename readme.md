
---

# Requisitos  
- **Docker** instalado  
- Configuração do arquivo `.env`  

# Como rodar  
Execute no terminal:  
```sh
docker-compose up --build
```

# Documentação  
- **Swagger (automática)**: [http://localhost:8000/api/docs](http://localhost:8000/api/docs)  
- **Postman (manual)**: [Documentação no Postman](https://documenter.getpostman.com/view/23869635/2sAYX9o1RJ#44e4723d-efc4-4bc7-9223-d2072317ed1b)  

# Autenticação  
No arquivo `.env`, defina:  
1. O **caminho da chave JSON** das credenciais da API do Google.  
2. As **informações do banco de dados**.  

**Exemplo**:  
Após baixar a chave JSON, crie uma pasta `credentials` dentro de `processing` e referencie-a no `.env`:  
```sh
GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/water-quality-andrei-57d16a92f3ab.json
```
> ⚠️ O prefixo `/app/` é necessário, pois faz parte da estrutura da imagem Docker.  

# Gerando a chave de autenticação  
1. Acesse o [Google Cloud Console](https://console.cloud.google.com/)  
2. **Crie um projeto** ou selecione um existente.  
3. Vá para **APIs e Serviços** → **Biblioteca**  
   - **Ative**:  
     - Google Drive API  
     - Google Earth Engine API  
4. Após ativar, vá para **Credenciais** → **Criar credenciais** → **Conta de serviço**  
5. Selecione a conta criada e vá para **Chaves** → **Adicionar chave** → **Criar nova chave**  
6. Escolha o formato **JSON** e faça o download.  

# Arquivos adicionais  
- **`templateEnv.txt`**: Exemplo de configuração do arquivo `.env`.  
- **`Exemplo.html`**: Página simples de login e interface para seleção de imagens para análise.  

---

# Testando a API  
Para testar via **Postman**, siga este fluxo:  
(Tenho que te mandar um exemplo de um modelo/scaler para caso você queira testar, posso te adicionar no postman também dai os arquivos ficam em núvem)

1. **Criar um usuário**  
2. **Fazer login**  
3. **Cadastrar um parâmetro**  
4. **Cadastrar um reservatório**  
5. **Cadastrar um modelo**  
6. **Gerar uma análise**  

# Considerações  
- Ainda **não há** uma rota para cancelar uma análise, pois a implementação é mais complexa.  
- Caso precise cancelar uma análise longa no **Google Earth Engine**, use o script `cancel.py`, que finaliza todas as tasks pendentes.  

### Como rodar o script de cancelamento:  
Pode ser necessário executar de uma destas formas:  
```sh
docker-compose exec web python cancel.py
```
ou  
```sh
python cancel.py
```
Dependendo do ambiente, um dos comandos funcionará.  

---
