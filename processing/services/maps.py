# processing/services/maps.py

import folium
import rasterio
import numpy as np
from folium.plugins import Fullscreen, MeasureControl
from branca.colormap import LinearColormap
from rasterio.warp import transform_bounds
import matplotlib

# Set the backend to 'Agg' before importing pyplot
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import base64
from io import BytesIO
from datetime import timedelta
import matplotlib.colors as mcolors
from PIL import Image
import ee


# Initialize the Earth Engine API
ee.Initialize()


class MapGenerator:
    """
    Classe responsável por gerar visualizações de dados raster em formatos interativos e estáticos.
    
    Esta classe processa dados raster de análises de qualidade da água e gera mapas
    utilizando Folium para visualizações interativas e Matplotlib para mapas estáticos.
    
    Attributes:
        raster_data (bytes): Dados raster em formato binário
        image_date (datetime): Data da imagem sendo processada
    
    Example:
        >>> generator = MapGenerator(raster_data, datetime.now())
        >>> html_map = generator.create_interactive_map()
        >>> static_map = generator.create_static_map()
    """

    def __init__(self, raster_data, image_date):
        """
        Inicializa o gerador de mapas.

        Args:
            raster_data (bytes): Dados raster em formato binário
            image_date (datetime): Data da imagem a ser processada
        """
        self.raster_data = raster_data
        self.image_date = image_date

    def mosaicBy(self, imageCollection):
        """
        Cria um mosaico de imagens do Earth Engine agrupadas por data, órbita e satélite.
        
        Este método agrupa imagens do mesmo dia, mesma órbita e mesmo satélite para
        criar um mosaico consistente, evitando artefatos de diferentes passagens.

        Args:
            imageCollection (ee.ImageCollection): Coleção de imagens do Earth Engine

        Returns:
            ee.ImageCollection: Coleção de mosaicos de imagens

        Example:
            >>> s2_collection = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
            >>> daily_mosaic = generator.mosaicBy(s2_collection)
        """
        def map_dates(image):
            """Mapeia datas para formato YYYY-MM-dd."""
            return image.set("date", image.date().format("YYYY-MM-dd"))

        def create_mosaic(date_orbit_spacecraft):
            """
            Cria um mosaico para uma combinação específica de data, órbita e satélite.
            
            Args:
                date_orbit_spacecraft (str): String combinada com data, órbita e nome do satélite
            
            Returns:
                ee.Image: Mosaico de imagens
            """
            parts = ee.String(date_orbit_spacecraft).split(" ")
            date1 = ee.Date(parts.get(0))
            orbit = ee.Number.parse(parts.get(1))
            spName = parts.get(2)

            mosaic = (
                imageCollection.filterDate(date1, date1.advance(1, "day"))
                .filterMetadata("SPACECRAFT_NAME", "equals", spName)
                .filterMetadata("SENSING_ORBIT_NUMBER", "equals", orbit)
                .mosaic()
            )

            return mosaic.set({
                "system:time_start": date1.millis(),
                "system:date": date1.format("YYYY-MM-dd"),
                "system:id": date_orbit_spacecraft,
            })

        imgList = imageCollection.map(map_dates).toList(imageCollection.size())

        all_dates = imgList.map(
            lambda img: ee.Image(img).date().format("YYYY-MM-dd")
        )
        all_orbits = imgList.map(
            lambda img: ee.Image(img).get("SENSING_ORBIT_NUMBER")
        )
        all_spacecraft = imgList.map(
            lambda img: ee.Image(img).get("SPACECRAFT_NAME")
        )

        combined = all_dates.zip(all_orbits).zip(all_spacecraft)
        combined = combined.map(lambda x: ee.List(x).flatten().join(" "))
        unique_combinations = combined.distinct()

        mosaic_collection = ee.ImageCollection(
            unique_combinations.map(create_mosaic)
        )

        return mosaic_collection

    def create_interactive_map(self):
        """
        Cria um mapa interativo usando Folium com múltiplas camadas.
        
        Gera um mapa HTML interativo que inclui:
        - Mapas base (OpenStreetMap, CartoDB)
        - Imagem do Sentinel-2 do dia
        - Camada de análise com escala de cores
        - Controles de medição e tela cheia
        
        Returns:
            str: HTML do mapa interativo ou mensagem de erro se não houver dados válidos
        
        Raises:
            Exception: Erros durante a adição de imagens do Sentinel-2
            
        Example:
            >>> html_map = generator.create_interactive_map()
            >>> with open('map.html', 'w') as f:
            ...     f.write(html_map)
        """
        with rasterio.MemoryFile(self.raster_data) as memfile:
            with memfile.open() as src:
                data = src.read(1)
                valid_data = data[data != -9999]
                if len(valid_data) == 0:
                    print("No valid data for interactive map generation")
                    return "<p>No data available (100% cloud coverage or invalid data)</p>"
                bounds = transform_bounds(src.crs, "EPSG:4326", *src.bounds)

                center_lat = (bounds[1] + bounds[3]) / 2
                center_lon = (bounds[0] + bounds[2]) / 2
                m = folium.Map(
                    location=[center_lat, center_lon],
                    zoom_start=12,
                    control_scale=True,
                )

                # Adiciona mapas base e camadas
                self._add_base_layers(m)
                self._try_add_sentinel_layer(m, bounds)
                self._add_analysis_layer(m, bounds, data, valid_data)
                self._add_map_controls(m)

                return m._repr_html_()

    def _add_base_layers(self, m):
        """
        Adiciona camadas base ao mapa Folium.
        
        Args:
            m (folium.Map): Instância do mapa Folium
        """
        folium.TileLayer("openstreetmap", name="OpenStreetMap").add_to(m)
        folium.TileLayer("cartodbpositron", name="CartoDB Positron").add_to(m)
        folium.TileLayer("cartodbdark_matter", name="CartoDB Dark Matter").add_to(m)

    def _try_add_sentinel_layer(self, m, bounds):
        """
        Tenta adicionar a camada do Sentinel-2 ao mapa.
        
        Args:
            m (folium.Map): Instância do mapa Folium
            bounds (tuple): Limites geográficos da área
        """
        try:
            start_date = self.image_date.strftime("%Y-%m-%d")
            end_date = (self.image_date + timedelta(days=1)).strftime("%Y-%m-%d")

            aoi = ee.Geometry.Rectangle([bounds[0], bounds[1], bounds[2], bounds[3]])
            s2_collection = (
                ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                .filterBounds(aoi)
                .filterDate(start_date, end_date)
            )

            daily_mosaic = self.mosaicBy(s2_collection)
            s2_image = daily_mosaic.first()

            if s2_image:
                viz_params = {
                    "bands": ["B4", "B3", "B2"],
                    "min": 0,
                    "max": 3000,
                    "gamma": 1.4,
                }
                map_id_dict = s2_image.getMapId(viz_params)
                folium.TileLayer(
                    tiles=map_id_dict["tile_fetcher"].url_format,
                    attr="Sentinel-2 Imagery",
                    name=f"Sentinel-2 Mosaic ({start_date})",
                    overlay=True,
                    opacity=0.7,
                ).add_to(m)

        except Exception as e:
            print(f"Error adding satellite imagery: {str(e)}")

    def _add_analysis_layer(self, m, bounds, data, valid_data):
        """
        Adiciona a camada de análise com escala de cores personalizada ao mapa.
        
        Args:
            m (folium.Map): Instância do mapa Folium
            bounds (tuple): Limites geográficos da área
            data (numpy.ndarray): Dados raster originais
            valid_data (numpy.ndarray): Dados válidos para definir escala
        """
        palette = [
            "#f7fbff",
            "#deebf7",
            "#4292c6",
            "#2171b5",
            "#084594",
        ]

        norm = mcolors.Normalize(vmin=np.min(valid_data), vmax=np.max(valid_data))
        custom_colors = [mcolors.hex2color(color) for color in palette]
        custom_cmap = mcolors.LinearSegmentedColormap.from_list(
            "custom", custom_colors, N=256
        )

        masked_data = np.ma.masked_equal(data, -9999)
        colored_data = custom_cmap(norm(masked_data.filled(np.nan)))
        colored_data[masked_data.mask] = [0, 0, 0, 0]

        img = Image.fromarray((colored_data * 255).astype(np.uint8))
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()

        folium.raster_layers.ImageOverlay(
            image=f"data:image/png;base64,{img_str}",
            bounds=[[bounds[1], bounds[0]], [bounds[3], bounds[2]]],
            opacity=0.7,
            name="Parameter Map",
        ).add_to(m)

        colormap = LinearColormap(
            colors=palette,
            vmin=float(np.min(valid_data)),
            vmax=float(np.max(valid_data)),
            caption="Parameter Concentration",
        )
        colormap.add_to(m)

    def _add_map_controls(self, m):
        """
        Adiciona controles de navegação e medição ao mapa.
        
        Args:
            m (folium.Map): Instância do mapa Folium
        """
        folium.LayerControl().add_to(m)
        Fullscreen().add_to(m)
        MeasureControl(
            position="topright",
            primary_length_unit="kilometers",
            primary_area_unit="square kilometers",
        ).add_to(m)

    def create_static_map(self):
        """
        Cria um mapa estático em formato PNG.
        
        Returns:
            bytes: Dados binários da imagem PNG do mapa
            
        Example:
            >>> static_map = generator.create_static_map()
            >>> with open('map.png', 'wb') as f:
            ...     f.write(static_map)
        """
        with rasterio.MemoryFile(self.raster_data) as memfile:
            with memfile.open() as src:
                data = src.read(1)
                masked_data = np.ma.masked_equal(data, -9999)
                
                if masked_data.count() == 0:
                    print("No valid data for static map generation")
                    return self.create_no_data_map()

                plt.figure(figsize=(12, 8))
                im = plt.imshow(masked_data, cmap="YlOrRd")
                plt.colorbar(im, label="Parameter Concentration")

                buffer = BytesIO()
                plt.savefig(buffer, format="png", dpi=300, bbox_inches="tight")
                plt.close()

                return buffer.getvalue()
    
    def create_no_data_map(self):
        """
        Cria um mapa estático com mensagem de ausência de dados.
        
        Returns:
            bytes: Dados binários da imagem PNG com mensagem de erro
        """
        plt.figure(figsize=(12, 8))
        plt.text(0.5, 0.5, "No data available (100% cloud coverage or invalid data)",
                ha='center', va='center', fontsize=16, wrap=True)
        plt.axis('off')
        
        buffer = BytesIO()
        plt.savefig(buffer, format="png", dpi=300, bbox_inches="tight")
        plt.close()
        
        return buffer.getvalue()