import joblib
import rasterio
import numpy as np
import os
from datetime import datetime
from pathlib import Path
import pandas as pd
from io import BytesIO

class WaterQualityPredictor:
    """
    Classe para predição de parâmetros de qualidade da água usando modelos de machine learning.
    
    Esta classe carrega um modelo pré-treinado e seu scaler associado para fazer predições
    sobre parâmetros de qualidade da água a partir de imagens de satélite multiespectrais.
    
    Attributes:
        model: Modelo de machine learning carregado
        scaler: Scaler para normalização dos dados
        band_columns (list): Nomes das bandas espectrais utilizadas
        index_columns (list): Nomes dos índices calculados
        temporal_columns (list): Colunas temporais (mês e estação)
        feature_columns (list): Lista completa de features utilizadas
        
    Example:
        >>> predictor = WaterQualityPredictor(model_file, scaler_file)
        >>> with open('image.tif', 'rb') as img, BytesIO() as output:
        ...     result = predictor.process_image(img.read(), output)
    """

    def __init__(self, model_file, scaler_file):
        """
        Inicializa o preditor de qualidade da água.

        Args:
            model_file (bytes/memoryview): Arquivo do modelo serializado
            scaler_file (bytes/memoryview): Arquivo do scaler serializado

        Raises:
            Exception: Se houver erro ao carregar o modelo ou scaler
        """
        # Converte memoryview para bytes se necessário
        if isinstance(model_file, memoryview):
            model_file = model_file.tobytes()
        if isinstance(scaler_file, memoryview):
            scaler_file = scaler_file.tobytes()

        # Carrega modelo e scaler usando BytesIO
        model_buffer = BytesIO(model_file)
        scaler_buffer = BytesIO(scaler_file)
        
        self.model = joblib.load(model_buffer)
        self.scaler = joblib.load(scaler_buffer)
        
        # Define grupos de features exatos do treinamento
        self.band_columns = ['B2', 'B3', 'B4', 'B5', 'B8', 'B11']  # Bandas Sentinel-2
        self.index_columns = [
            'NDCI',        # Normalized Difference Chlorophyll Index
            'NDVI',        # Normalized Difference Vegetation Index
            'FAI',         # Floating Algae Index
            'MNDWI',       # Modified Normalized Difference Water Index
            'B3_B2_ratio', # Razão Verde/Azul
            'B4_B3_ratio', # Razão Vermelho/Verde
            'B5_B4_ratio'  # Razão Red Edge/Vermelho
        ]
        self.temporal_columns = ['Month', 'Season']
        self.feature_columns = self.band_columns + self.index_columns + self.temporal_columns

    def process_chunk(self, bands_chunk, month, season):
        """
        Processa um chunk da imagem, calculando índices e fazendo predições.
        
        Este método:
        1. Extrai as bandas do chunk
        2. Calcula índices espectrais (NDCI, NDVI, FAI, MNDWI)
        3. Calcula razões entre bandas
        4. Aplica máscara de água
        5. Faz predições para pixels de água
        
        Args:
            bands_chunk (numpy.ndarray): Array 3D com as bandas do chunk
            month (int): Mês da imagem (1-12)
            season (int): Estação do ano (1-4)
            
        Returns:
            numpy.ndarray: Array 2D com as predições (-9999 para pixels não-água)
            
        Notes:
            Os índices calculados são:
            - MNDWI: (B3 - B11)/(B3 + B11) para detecção de água
            - NDCI: (B5 - B4)/(B5 + B4) para clorofila
            - NDVI: (B8 - B4)/(B8 + B4) para vegetação
            - FAI: B8 - [B4 + (B11 - B4) * (842 - 665)/(1610 - 665)] para algas
        """
        # Extrai bandas
        b2, b3, b4, b5, b8, b11 = bands_chunk[0:6]
        
        # Calcula índices com tratamento de divisão por zero
        with np.errstate(divide='ignore', invalid='ignore'):
            mndwi = np.where((b3 + b11) != 0, (b3 - b11) / (b3 + b11), 0)
            ndci = np.where((b5 + b4) != 0, (b5 - b4) / (b5 + b4), 0)
            ndvi = np.where((b8 + b4) != 0, (b8 - b4) / (b8 + b4), 0)
        
        # Calcula FAI (Floating Algae Index)
        nir_wl, red_wl, swir_wl = 842, 665, 1610  # Comprimentos de onda em nm
        fai = b8 - (b4 + (b11 - b4) * (nir_wl - red_wl) / (swir_wl - red_wl))
        
        # Calcula razões entre bandas com tratamento de divisão por zero
        with np.errstate(divide='ignore', invalid='ignore'):
            b3_b2_ratio = np.where((b2 != 0) & (b3 != 0), b3 / b2, 0)
            b4_b3_ratio = np.where((b3 != 0) & (b4 != 0), b4 / b3, 0)
            b5_b4_ratio = np.where((b4 != 0) & (b5 != 0), b5 / b4, 0)

        # Substitui NaN e inf por 0
        for arr in [mndwi, ndci, ndvi, fai, b3_b2_ratio, b4_b3_ratio, b5_b4_ratio]:
            np.nan_to_num(arr, copy=False)
        
        # Cria máscara de água (MNDWI > 0.3 indica água)
        water_mask = mndwi > 0.3
        
        # Cria dicionário de features
        feature_dict = {
            'B2': b2.ravel(),
            'B3': b3.ravel(),
            'B4': b4.ravel(),
            'B5': b5.ravel(),
            'B8': b8.ravel(),
            'B11': b11.ravel(),
            'NDCI': ndci.ravel(),
            'NDVI': ndvi.ravel(),
            'FAI': fai.ravel(),
            'MNDWI': mndwi.ravel(),
            'B3_B2_ratio': b3_b2_ratio.ravel(),
            'B4_B3_ratio': b4_b3_ratio.ravel(),
            'B5_B4_ratio': b5_b4_ratio.ravel(),
            'Month': np.full_like(b2.ravel(), month),
            'Season': np.full_like(b2.ravel(), season)
        }
        
        # Cria DataFrame e seleciona pixels de água
        features_df = pd.DataFrame(feature_dict)[self.feature_columns]
        valid_features = features_df[water_mask.ravel()]
        
        if len(valid_features) > 0:
            # Aplica scaling e faz predições
            scaled_features = self.scaler.transform(valid_features)
            predictions = self.model.predict(scaled_features)
            
            # Prepara resultado
            chunk_result = np.full(water_mask.shape, -9999, dtype=np.float32)
            chunk_result[water_mask] = predictions
            return chunk_result
        else:
            return np.full(water_mask.shape, -9999, dtype=np.float32)

    def process_image(self, image_data, output_file):
        """
        Processa uma imagem completa, dividindo em chunks para eficiência de memória.
        
        Args:
            image_data (bytes): Dados binários da imagem GeoTIFF
            output_file (BytesIO): Buffer para salvar o resultado
            
        Returns:
            BytesIO: Buffer com a imagem GeoTIFF resultante
            
        Notes:
            - Processa a imagem em chunks de 500x500 pixels
            - Mantém os metadados geoespaciais da imagem original
            - Usa -9999 como valor nodata
            - Retorna resultado como float32
        """
        with rasterio.MemoryFile(image_data) as memfile:
            with memfile.open() as src:
                # Obtém informações da imagem
                height = src.height
                width = src.width
                
                # Obtém data da imagem dos metadados ou usa data atual
                image_date = src.tags().get('DATE_ACQUIRED', datetime.now().strftime('%Y-%m-%d'))
                month = datetime.strptime(image_date, '%Y-%m-%d').month
                season = ((month + 2) // 3) % 4 + 1  # Converte mês para estação (1-4)
                
                # Prepara array de saída
                output_data = np.full((height, width), -9999, dtype=np.float32)
                
                # Processa em chunks
                chunk_size = 500
                total_chunks = ((height + chunk_size - 1) // chunk_size) * \
                             ((width + chunk_size - 1) // chunk_size)
                
                # Itera sobre chunks
                for y in range(0, height, chunk_size):
                    y_end = min(y + chunk_size, height)
                    for x in range(0, width, chunk_size):
                        x_end = min(x + chunk_size, width)
                        
                        # Lê e processa chunk
                        window = rasterio.windows.Window(x, y, x_end - x, y_end - y)
                        chunk_data = src.read(window=window)
                        
                        try:
                            chunk_result = self.process_chunk(chunk_data, month, season)
                            output_data[y:y_end, x:x_end] = chunk_result
                        except Exception as e:
                            continue
                
                # Salva resultado mantendo metadados geoespaciais
                with rasterio.MemoryFile() as memfile:
                    kwargs = src.meta.copy()
                    kwargs.update({
                        'driver': 'GTiff',
                        'count': 1,
                        'dtype': 'float32',
                        'nodata': -9999
                    })

                    with memfile.open(**kwargs) as dst:
                        dst.write(output_data.astype(np.float32), 1)

                    output_file.write(memfile.read())
                
                return output_file