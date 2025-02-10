import ee
from datetime import datetime
from typing import List, Dict

class SatelliteImageExtractor:
    """
    Classe para extração e pré-processamento de imagens do Sentinel-2 usando Google Earth Engine.
    
    Esta classe gerencia o download de imagens do Sentinel-2, incluindo:
    - Filtragem por área e período
    - Criação de mosaicos diários
    - Mascaramento de nuvens e água
    - Cálculo de índices espectrais
    - Exportação para Google Drive
    
    Attributes:
        coordinates: Coordenadas do polígono de interesse (definido no create_export_tasks)
    
    Example:
        >>> extractor = SatelliteImageExtractor()
        >>> tasks = extractor.create_export_tasks(
        ...     coordinates=[[lon1, lat1], [lon2, lat2], ...],
        ...     start_date="2024-01-01",
        ...     end_date="2024-01-31",
        ...     folder_name="reservoir_images"
        ... )
    """

    def __init__(self):
        """
        Inicializa o extrator de imagens e o Earth Engine.
        """
        ee.Initialize()
        
    def create_export_tasks(self, coordinates: List[List[float]], start_date: str, 
                          end_date: str, folder_name: str) -> List[Dict]:
        """
        Cria tarefas de exportação para imagens de satélite e retorna informações das tarefas.
        
        Este método realiza:
        1. Define a área de interesse
        2. Filtra a coleção de imagens Sentinel-2
        3. Cria mosaicos diários
        4. Prepara as imagens para exportação
        5. Inicia as tarefas de exportação
        
        Args:
            coordinates: Lista de pares [longitude, latitude] definindo o polígono
            start_date: Data inicial no formato 'YYYY-MM-DD'
            end_date: Data final no formato 'YYYY-MM-DD'
            folder_name: Nome da pasta no Google Drive para armazenar as imagens
            
        Returns:
            Lista de dicionários contendo informações das tarefas:
            - task_id: ID único da tarefa
            - date: Data da imagem
            - folder: Nome da pasta
            - filename: Nome do arquivo
            - status: Estado da tarefa
            - cloud_percentage: Porcentagem de nuvens
            
        Example:
            >>> tasks = extractor.create_export_tasks(
            ...     coordinates=[[0, 0], [0, 1], [1, 1], [1, 0]],
            ...     start_date="2024-01-01",
            ...     end_date="2024-01-31",
            ...     folder_name="reservoir_1"
            ... )
            >>> for task in tasks:
            ...     print(f"Task {task['task_id']}: {task['date']}")
        """
        self.coordinates = coordinates
        aoi = ee.Geometry.Polygon([coordinates])
        
        # Filtra coleção de imagens
        s2 = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            .filterBounds(aoi)
            .filterDate(start_date, end_date)
            .map(lambda image: image.set("date", image.date().format("yyyy-MM-dd"))))
        
        # Cria mosaicos diários agrupando por data, spacecraft e órbita
        daily = ee.ImageCollection(
            ee.Join.saveAll("images").apply(
                primary=s2,
                secondary=s2,
                condition=ee.Filter.And(
                    ee.Filter.equals(leftField="date", rightField="date"),
                    ee.Filter.equals(leftField="SPACECRAFT_NAME", rightField="SPACECRAFT_NAME"),
                    ee.Filter.equals(leftField="SENSING_ORBIT_NUMBER", rightField="SENSING_ORBIT_NUMBER"),
                ),
            )
        ).map(
            lambda image: ee.ImageCollection(ee.List(image.get("images")))
            .mosaic()
            .set("system:time_start", ee.Date(image.get("date")).millis())
        )
        
        # Prepara coleção para exportação
        collection_to_export = daily.map(self._prepare_for_export)
        size = collection_to_export.size().getInfo()
        if size == 0:
            print(f"No images found between {start_date} and {end_date}")
            return []
            
        image_list = collection_to_export.toList(size)
        
        # Inicia exportações e coleta informações
        tasks_info = []
        for i in range(size):
            image = image_list.get(i)
            task_info = self._create_export_task(image, aoi, folder_name)
            tasks_info.append(task_info)
        
        return tasks_info

    def _prepare_for_export(self, image):
        """
        Prepara a imagem para exportação com mascaramento de nuvens e água.
        
        Este método:
        1. Converte bandas para float32
        2. Aplica máscara de nuvens usando QA60
        3. Identifica água usando MNDWI
        4. Calcula índices espectrais
        5. Combina todas as bandas e máscaras
        
        Args:
            image (ee.Image): Imagem Sentinel-2 original
            
        Returns:
            ee.Image: Imagem processada com bandas adicionais e máscaras aplicadas
            
        Notes:
            Índices calculados:
            - NDCI: (B5 - B4)/(B5 + B4) para clorofila
            - NDVI: (B8 - B4)/(B8 + B4) para vegetação
            - FAI: B8 - [B4 + (B11 - B4) * (842 - 665)/(1610 - 665)] para algas
            - MNDWI: (B3 - B11)/(B3 + B11) para água
        """
        # Seleciona e converte bandas
        bands = ["B2", "B3", "B4", "B5", "B8", "B11"]
        base_image = image.select(bands).toFloat()
        
        # Cria máscara de nuvens
        qa60 = image.select("QA60").toInt()
        cloudBitMask = ee.Number(1 << 10)  # Nuvem densa
        cirrusBitMask = ee.Number(1 << 11)  # Cirrus
        cloud_mask = (qa60.bitwiseAnd(cloudBitMask).eq(0)
                     .And(qa60.bitwiseAnd(cirrusBitMask).eq(0)))
        
        # Cria máscara de água
        mndwi = base_image.normalizedDifference(["B3", "B11"])
        water_mask = mndwi.gt(0.3)
        
        # Combina máscaras
        valid_mask = water_mask.And(cloud_mask)
        
        # Normaliza bandas para 0-1
        base_image = base_image.divide(10000)
        
        # Calcula índices espectrais
        ndci = base_image.normalizedDifference(["B5", "B4"]).rename("NDCI")
        ndvi = base_image.normalizedDifference(["B8", "B4"]).rename("NDVI")
        
        # Calcula FAI (Floating Algae Index)
        fai = base_image.expression(
            "NIR - (RED + (SWIR - RED) * (NIR_wl - RED_wl) / (SWIR_wl - RED_wl))",
            {
                "NIR": base_image.select("B8"),
                "RED": base_image.select("B4"),
                "SWIR": base_image.select("B11"),
                "NIR_wl": 842,
                "RED_wl": 665,
                "SWIR_wl": 1610,
            }
        ).rename("FAI")
        
        # Calcula razões entre bandas
        b3_b2_ratio = base_image.select("B3").divide(base_image.select("B2")).rename("B3_B2_ratio")
        b4_b3_ratio = base_image.select("B4").divide(base_image.select("B3")).rename("B4_B3_ratio")
        b5_b4_ratio = base_image.select("B5").divide(base_image.select("B4")).rename("B5_B4_ratio")
        
        # Combina todas as bandas
        final_image = base_image.addBands([ndci, ndvi, fai, mndwi.rename("MNDWI"),
                                         b3_b2_ratio, b4_b3_ratio, b5_b4_ratio])
        
        # Aplica máscara final
        final_image = final_image.updateMask(valid_mask)
        
        # Calcula porcentagem de nuvens
        aoi = ee.Geometry.Polygon(self.coordinates)
        cloud_percentage = calculate_cloud_percentage(image, aoi)
        
        return final_image.set("cloud_percentage", cloud_percentage)\
                         .set("system:time_start", image.get("system:time_start"))
        
    def _create_export_task(self, image, aoi, folder_name):
        """
        Cria e inicia uma tarefa de exportação para o Google Drive.
        
        Args:
            image (ee.Image): Imagem processada para exportar
            aoi (ee.Geometry): Área de interesse
            folder_name (str): Nome da pasta no Drive
            
        Returns:
            dict: Informações da tarefa criada
        """
        image = ee.Image(image)
        date = ee.Date(image.get("system:time_start")).format("yyyy-MM-dd").getInfo()
        cloud_percentage = image.get("cloud_percentage").getInfo()
        
        filename = f"{folder_name}_{date}"
        
        export_params = {
            "image": image, 
            "description": filename,
            "scale": 10,  # Resolução em metros
            "region": aoi,
            "fileFormat": "GeoTIFF",
            "maxPixels": 1e13,
            "folder": folder_name
        }
        
        task = ee.batch.Export.image.toDrive(**export_params)
        task.start()
        
        return {
            "task_id": task.id,
            "date": date,
            "folder": folder_name,
            "filename": filename,
            "status": "STARTED",
            "cloud_percentage": cloud_percentage
        }

def calculate_cloud_percentage(image, aoi):
    """
    Calcula a porcentagem de cobertura de nuvens na imagem.
    
    Args:
        image (ee.Image): Imagem Sentinel-2
        aoi (ee.Geometry): Área de interesse
        
    Returns:
        ee.Number: Porcentagem de pixels cobertos por nuvens
        
    Notes:
        Usa a banda SCL (Scene Classification Layer) do Sentinel-2:
        - 3: Sombras de nuvens
        - 8: Nuvens (média probabilidade)
        - 9: Nuvens (alta probabilidade)
    """
    scl = image.select('SCL')
    cloud_mask = scl.eq(8).Or(scl.eq(9)).Or(scl.eq(3))
    
    total_pixels = ee.Number(scl.reduceRegion(
        reducer=ee.Reducer.count(),
        geometry=aoi,
        scale=10,
        maxPixels=1e13
    ).get('SCL'))
    
    cloud_pixels = ee.Number(cloud_mask.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=aoi,
        scale=10,
        maxPixels=1e13
    ).get('SCL'))
    
    cloud_percentage = cloud_pixels.divide(total_pixels).multiply(100)
    
    return cloud_percentage