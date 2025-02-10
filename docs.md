# API de Análise de Qualidade da Água - Documentação Detalhada

## Sumário
1. [Visão Geral](#visão-geral)
2. [Arquitetura do Sistema](#arquitetura-do-sistema)
3. [Modelos de Dados](#modelos-de-dados)
4. [Pipeline de Processamento](#pipeline-de-processamento)
5. [Serviços Principais](#serviços-principais)
6. [Processamento de Imagens](#processamento-de-imagens)
7. [Integração com Google Earth Engine](#integração-com-google-earth-engine)
8. [Visualização de Dados](#visualização-de-dados)
9. [Considerações Técnicas](#considerações-técnicas)

## Visão Geral

Sistema integrado para monitoramento e análise da qualidade da água em reservatórios utilizando:
- Imagens de satélite Sentinel-2
- Modelos de machine learning
- Processamento geoespacial
- Visualização interativa de dados

### Objetivos Principais
- Automatizar a coleta de imagens de satélite
- Processar e analisar parâmetros de qualidade da água
- Gerar visualizações e relatórios
- Manter histórico de análises

## Arquitetura do Sistema

### Componentes Principais
1. **API Core (Django)**
   - Gerenciamento de usuários e autenticação
   - Controle de acesso baseado em reservatórios
   - Endpoints RESTful para todas as operações

2. **Processamento de Imagens**
   - Integração com Google Earth Engine
   - Pipeline de processamento assíncrono
   - Cache de imagens processadas

3. **Machine Learning**
   - Múltiplos modelos por reservatório
   - Processamento em lotes
   - Normalização de dados

4. **Visualização**
   - Mapas interativos
   - Séries temporais
   - Exportação de dados

## Modelos de Dados

### User
```python
class User(AbstractUser):
    email = models.EmailField(unique=True)
    company = models.CharField(max_length=255)
    phone = models.CharField(max_length=15)
    cpf = models.CharField(max_length=11, unique=True)
    
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "cpf"]
```
- Sistema customizado de autenticação
- Login via email
- Validação de CPF
- Associação com empresa

### Reservoir
```python
class Reservoir(models.Model):
    name = models.CharField(max_length=255, unique=True)
    coordinates = models.JSONField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
```
- Coordenadas em formato GeoJSON
- Validação de geometria
- Controle de acesso por usuário

### MachineLearningModel
```python
class MachineLearningModel(models.Model):
    reservoir = models.ForeignKey(Reservoir, on_delete=models.CASCADE)
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE)
    model_file = models.BinaryField()
    scaler_file = models.BinaryField()
    model_file_hash = models.CharField(max_length=64)
    scaler_file_hash = models.CharField(max_length=64)
```
- Armazenamento binário de modelos
- Hash para validação de integridade
- Vinculação com parâmetros específicos

### Analysis
```python
class Analysis(models.Model):
    analysis_group = models.ForeignKey(AnalysisGroup, on_delete=models.CASCADE)
    identifier_code = models.UUIDField(unique=True)
    cloud_percentage = models.DecimalField(max_digits=8, decimal_places=5)
    analysis_date = models.DateField()
```
- Agrupamento de análises
- Rastreamento por UUID
- Metadados de qualidade (cobertura de nuvens)

## Pipeline de Processamento

### 1. Inicialização da Análise
```python
def process_request(request_id):
    request = AnalysisRequest.objects.get(id=request_id)
    
    # Validação de modelos
    models = MachineLearningModel.objects.filter(id__in=model_ids)
    validate_models_compatibility(models)
    
    # Criação do grupo de análise
    analysis_group = create_analysis_group(request, models)
```

### 2. Download de Imagens
```python
def download_satellite_images(reservoir, start_date, end_date):
    extractor = SatelliteImageExtractor()
    tasks_info = extractor.create_export_tasks(
        coordinates=reservoir.coordinates,
        start_date=start_date,
        end_date=end_date,
        folder_name=folder_name
    )
```

### 3. Processamento de Imagens
```python
class WaterQualityPredictor:
    def process_image(self, image_data, output_file):
        # Processamento em chunks para eficiência de memória
        chunk_size = 500
        for chunk in self.get_chunks(image_data, chunk_size):
            processed_chunk = self.process_chunk(chunk)
            self.write_chunk(processed_chunk, output_file)
```

## Serviços Principais

### DriveService
Gerencia interações com Google Drive:
```python
class DriveService:
    def __init__(self):
        self.SCOPES = [
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/drive.file',
            'https://www.googleapis.com/auth/drive.metadata.readonly'
        ]
```
- Autenticação OAuth2
- Download automático de imagens
- Gestão de credenciais

### MapGenerator
Geração de visualizações:
```python
class MapGenerator:
    def create_interactive_map(self):
        # Configuração base do mapa
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=12,
            control_scale=True
        )
        
        # Adição de camadas
        self._add_base_layers(m)
        self._add_satellite_layer(m)
        self._add_analysis_layer(m)
```

## Processamento de Imagens

### Bandas Utilizadas
- B2: Blue (490nm)
- B3: Green (560nm)
- B4: Red (665nm)
- B5: Red Edge (705nm)
- B8: NIR (842nm)
- B11: SWIR (1610nm)

### Índices Calculados
1. **NDCI (Normalized Difference Chlorophyll Index)**
   ```python
   ndci = (B5 - B4) / (B5 + B4)
   ```

2. **NDVI (Normalized Difference Vegetation Index)**
   ```python
   ndvi = (B8 - B4) / (B8 + B4)
   ```

3. **FAI (Floating Algae Index)**
   ```python
   fai = NIR - (RED + (SWIR - RED) * (NIR_wl - RED_wl) / (SWIR_wl - RED_wl))
   ```

4. **MNDWI (Modified Normalized Difference Water Index)**
   ```python
   mndwi = (B3 - B11) / (B3 + B11)
   ```

### Máscaras
1. **Máscara de Água**
   ```python
   water_mask = mndwi > 0.3
   ```

2. **Máscara de Nuvens**
   ```python
   cloud_mask = (qa60.bitwiseAnd(cloudBitMask).eq(0)
                .And(qa60.bitwiseAnd(cirrusBitMask).eq(0)))
   ```

## Integração com Google Earth Engine

### Configuração de Exportação
```python
def create_export_tasks(self, coordinates, start_date, end_date, folder_name):
    aoi = ee.Geometry.Polygon([coordinates])
    s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(aoi)
        .filterDate(start_date, end_date)
```

### Mosaico de Imagens
```python
def mosaicBy(self, imageCollection):
    # Agrupa imagens por data, órbita e spacecraft
    mosaic = imageCollection.filterDate(date1, date1.advance(1, "day"))
        .filterMetadata("SPACECRAFT_NAME", "equals", spName)
        .filterMetadata("SENSING_ORBIT_NUMBER", "equals", orbit)
        .mosaic()
```

## Visualização de Dados

### Mapas Interativos
1. **Camadas Base**
   - OpenStreetMap
   - CartoDB Positron
   - CartoDB Dark Matter

2. **Camada de Satélite**
   - Imagem Sentinel-2 do dia
   - Composição RGB natural

3. **Camada de Análise**
   - Mapa de calor do parâmetro
   - Escala de cores personalizada
   - Controles de opacidade

### Controles
1. **Medição**
   - Distâncias
   - Áreas
   - Unidades configuráveis

2. **Camadas**
   - Alternância de visibilidade
   - Ajuste de opacidade
   - Ordem de sobreposição

## Considerações Técnicas

### Performance
1. **Processamento em Chunks**
   - Tamanho padrão: 500x500 pixels
   - Gerenciamento de memória
   - Processamento paralelo

2. **Cache**
   - Imagens processadas
   - Resultados intermediários
   - Mapas gerados

### Segurança
1. **Autenticação**
   - JWT Tokens
   - Refresh tokens
   - Validação de sessão

2. **Autorização**
   - Permissões por reservatório
   - Registro de atividades
   - Validação de dados

### Armazenamento
1. **Dados Binários**
   - Modelos ML
   - Imagens de satélite
   - Mapas estáticos






# Rotas:

## Postman:
https://documenter.getpostman.com/view/23869635/2sAYX9o1RJ#44e4723d-efc4-4bc7-9223-d2072317ed1b

## Swagger:
http://localhost:8000/api/docs