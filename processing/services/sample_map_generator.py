# processing/services/sample_map_generator.py

import folium
from folium.plugins import Fullscreen, MeasureControl, HeatMap
from branca.colormap import LinearColormap
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
from datetime import timedelta
import ee
from google.oauth2 import service_account
import os

# Initialize the Earth Engine API
credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')

if not credentials_path:
    raise ValueError("GOOGLE_APPLICATION_CREDENTIALS environment variable not set")

credentials = service_account.Credentials.from_service_account_file(
    credentials_path,
    scopes=['https://www.googleapis.com/auth/earthengine']
)

ee.Initialize(credentials)

class SampleMapGenerator:
    """
    Generate interactive and static maps from sample point data with predictions.
    
    This class creates visualizations for water quality predictions from point samples
    instead of raster data, using scatter plots and heatmaps.
    
    Attributes:
        sample_result (dict): Dictionary containing points with predictions
        image_date (datetime): Date of the analysis
    """

    def __init__(self, sample_result, image_date):
        """
        Initialize the sample map generator.

        Args:
            sample_result (dict): Dictionary with 'points', 'average', 'count', 'parameter'
            image_date (datetime): Date of the image/analysis
        """
        self.sample_result = sample_result
        self.image_date = image_date
        self.points = sample_result.get('points', [])
        self.parameter = sample_result.get('parameter', 'Water Quality')

    def create_interactive_map(self):
        """
        Create an interactive Folium map with point samples colored by prediction values.
        
        Returns:
            str: HTML of the interactive map
        """
        if not self.points:
            return "<p>No sample data available for map generation</p>"
        
        # Calculate center of all points
        lats = [p['lat'] for p in self.points]
        lons = [p['lon'] for p in self.points]
        center_lat = np.mean(lats)
        center_lon = np.mean(lons)
        
        # Create base map
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=12,
            control_scale=True,
        )

        # Add base layers
        self._add_base_layers(m)
        
        # Try to add Sentinel-2 imagery
        self._try_add_sentinel_layer(m, lats, lons)
        
        # Add prediction points
        self._add_prediction_points(m)
        
        # Add heatmap layer
        self._add_heatmap_layer(m)
        
        # Add controls
        self._add_map_controls(m)

        return m._repr_html_()

    def _add_base_layers(self, m):
        """Add base tile layers to the map."""
        folium.TileLayer("openstreetmap", name="OpenStreetMap").add_to(m)
        folium.TileLayer("cartodbpositron", name="CartoDB Positron").add_to(m)
        folium.TileLayer("cartodbdark_matter", name="CartoDB Dark Matter").add_to(m)

    def _try_add_sentinel_layer(self, m, lats, lons):
        """Try to add Sentinel-2 satellite imagery layer."""
        try:
            start_date = self.image_date.strftime("%Y-%m-%d")
            end_date = (self.image_date + timedelta(days=1)).strftime("%Y-%m-%d")

            # Create bounding box from points with some padding
            lat_range = max(lats) - min(lats)
            lon_range = max(lons) - min(lons)
            padding = max(lat_range, lon_range) * 0.1  # 10% padding
            
            aoi = ee.Geometry.Rectangle([
                min(lons) - padding, min(lats) - padding,
                max(lons) + padding, max(lats) + padding
            ])
            
            s2_collection = (
                ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
                .filterBounds(aoi)
                .filterDate(start_date, end_date)
            )

            s2_image = s2_collection.mosaic()

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
                    name=f"Sentinel-2 ({start_date})",
                    overlay=True,
                    opacity=0.7,
                ).add_to(m)

        except Exception as e:
            print(f"Error adding satellite imagery: {str(e)}")

    def _add_prediction_points(self, m):
        """Add colored circle markers for each prediction point."""
        # Get prediction values for color scaling
        predictions = [p['prediction'] for p in self.points]
        min_pred = min(predictions)
        max_pred = max(predictions)
        
        # Create color palette
        palette = ['#f7fbff', '#deebf7', '#4292c6', '#2171b5', '#084594']
        
        # Create colormap
        colormap = LinearColormap(
            colors=palette,
            vmin=min_pred,
            vmax=max_pred,
            caption=f'{self.parameter} Concentration'
        )
        colormap.add_to(m)
        
        # Add points as circle markers
        for point in self.points:
            color = colormap(point['prediction'])
            
            folium.CircleMarker(
                location=[point['lat'], point['lon']],
                radius=8,
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.7,
                popup=f"{self.parameter}: {point['prediction']:.3f}",
                tooltip=f"{point['prediction']:.3f}"
            ).add_to(m)

    def _add_heatmap_layer(self, m):
        """Add a heatmap layer showing prediction intensity."""
        # Prepare data for heatmap: [lat, lon, weight]
        heat_data = [
            [p['lat'], p['lon'], p['prediction']] 
            for p in self.points
        ]
        
        HeatMap(
            heat_data,
            name='Heatmap',
            min_opacity=0.3,
            radius=25,
            blur=20,
            gradient={
                '0.0': '#f7fbff',
                '0.25': '#deebf7',
                '0.5': '#4292c6',
                '0.75': '#2171b5',
                '1.0': '#084594'
            }
        ).add_to(m)

    def _add_map_controls(self, m):
        """Add navigation and measurement controls."""
        folium.LayerControl().add_to(m)
        Fullscreen().add_to(m)
        MeasureControl(
            position="topright",
            primary_length_unit="kilometers",
            primary_area_unit="square kilometers",
        ).add_to(m)

    def create_static_map(self):
        """
        Create a static matplotlib scatter plot of the predictions.
        
        Returns:
            bytes: PNG image data
        """
        if not self.points:
            # Create empty plot
            fig, ax = plt.subplots(figsize=(12, 8))
            ax.text(0.5, 0.5, 'No data available', 
                   ha='center', va='center', fontsize=16)
            ax.axis('off')
        else:
            # Extract data
            lats = [p['lat'] for p in self.points]
            lons = [p['lon'] for p in self.points]
            predictions = [p['prediction'] for p in self.points]
            
            # Create scatter plot
            fig, ax = plt.subplots(figsize=(12, 8))
            scatter = ax.scatter(lons, lats, c=predictions, 
                               cmap='YlOrRd', s=100, alpha=0.7, edgecolors='black')
            
            # Add colorbar
            cbar = plt.colorbar(scatter, ax=ax, label=f'{self.parameter} Concentration')
            
            # Labels
            ax.set_xlabel('Longitude', fontsize=12)
            ax.set_ylabel('Latitude', fontsize=12)
            ax.set_title(f'{self.parameter} Predictions - {self.image_date.strftime("%Y-%m-%d")}', 
                        fontsize=14, fontweight='bold')
            
            # Grid
            ax.grid(True, alpha=0.3)
            
            # Statistics text
            avg_pred = np.mean(predictions)
            std_pred = np.std(predictions)
            stats_text = f'Samples: {len(predictions)}\nAvg: {avg_pred:.3f}\nStd: {std_pred:.3f}'
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
                   fontsize=10, verticalalignment='top',
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

        # Save to buffer
        buffer = BytesIO()
        plt.savefig(buffer, format="png", dpi=300, bbox_inches="tight")
        plt.close()

        return buffer.getvalue()
