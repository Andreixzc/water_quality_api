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
        Create an interactive Folium map with smooth interpolated gradient overlay.
        
        Returns:
            str: HTML of the interactive map
        """
        if not self.points:
            return "<p>No sample data available for map generation</p>"
        
        from scipy.interpolate import griddata
        from scipy.ndimage import gaussian_filter
        from scipy.spatial import cKDTree
        import rasterio
        from rasterio.transform import from_bounds
        import tempfile
        import os
        
        # Extract data
        lats = np.array([p['lat'] for p in self.points])
        lons = np.array([p['lon'] for p in self.points])
        predictions = np.array([p['prediction'] for p in self.points])
        
        # Calculate center and bounds
        center_lat = np.mean(lats)
        center_lon = np.mean(lons)
        
        lat_min, lat_max = lats.min(), lats.max()
        lon_min, lon_max = lons.min(), lons.max()
        
        # Add 5% padding
        lat_range = lat_max - lat_min
        lon_range = lon_max - lon_min
        padding = max(lat_range, lon_range) * 0.05
        
        lat_min -= padding
        lat_max += padding
        lon_min -= padding
        lon_max += padding
        
        # Create base map
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=13,
            control_scale=True,
        )

        # Add base layers
        self._add_base_layers(m)
        
        # Try to add Sentinel-2 imagery
        self._try_add_sentinel_layer(m, lats, lons)
        
        # Generate smooth interpolated raster
        grid_resolution = 200  # Lower than static (200 vs 800) for faster web loading
        grid_lon = np.linspace(lon_min, lon_max, grid_resolution)
        grid_lat = np.linspace(lat_min, lat_max, grid_resolution)
        grid_lon_mesh, grid_lat_mesh = np.meshgrid(grid_lon, grid_lat)
        
        # Stack points for interpolation
        points_xy = np.column_stack((lons, lats))
        grid_xy = np.column_stack((grid_lon_mesh.ravel(), grid_lat_mesh.ravel()))
        
        # Cubic interpolation
        grid_cubic = griddata(
            points_xy, predictions,
            (grid_lon_mesh, grid_lat_mesh),
            method='cubic'
        )
        
        # Nearest neighbor fallback
        grid_nearest = griddata(
            points_xy, predictions,
            (grid_lon_mesh, grid_lat_mesh),
            method='nearest'
        )
        
        # Combine
        grid_combined = np.where(np.isnan(grid_cubic), grid_nearest, grid_cubic)
        
        # Distance-based masking
        tree = cKDTree(points_xy)
        distances, _ = tree.query(grid_xy)
        distances = distances.reshape(grid_lon_mesh.shape)
        
        max_distance = 0.01  # ~1km
        grid_combined[distances > max_distance] = np.nan
        
        # Gaussian smoothing
        valid_mask = ~np.isnan(grid_combined)
        if valid_mask.any():
            grid_for_blur = grid_combined.copy()
            grid_for_blur[~valid_mask] = 0
            grid_smoothed = gaussian_filter(grid_for_blur, sigma=1.5)
            grid_smoothed[~valid_mask] = np.nan
        else:
            grid_smoothed = grid_combined
        
        # Flip for correct orientation
        grid_final = np.flipud(grid_smoothed)
        
        # Create a temporary GeoTIFF for the raster
        with tempfile.NamedTemporaryFile(suffix='.tif', delete=False) as tmp_file:
            tmp_path = tmp_file.name
            
            # Write GeoTIFF
            transform = from_bounds(lon_min, lat_min, lon_max, lat_max, grid_resolution, grid_resolution)
            
            with rasterio.open(
                tmp_path, 'w',
                driver='GTiff',
                height=grid_resolution,
                width=grid_resolution,
                count=1,
                dtype='float32',
                crs='EPSG:4326',
                transform=transform,
                nodata=-9999
            ) as dst:
                data_to_write = np.nan_to_num(grid_final, nan=-9999)
                dst.write(data_to_write.astype('float32'), 1)
        
        # Read the GeoTIFF back and add to map as ImageOverlay
        # Note: Folium's raster support is limited, so we'll use the heatmap as fallback
        # but with much smoother appearance
        
        # Add smooth heatmap layer (better than raster for Folium)
        # Create denser grid points for smooth appearance
        smooth_points = []
        for i in range(grid_resolution):
            for j in range(grid_resolution):
                if not np.isnan(grid_final[i, j]):
                    lat = lat_max - (i / grid_resolution) * (lat_max - lat_min)
                    lon = lon_min + (j / grid_resolution) * (lon_max - lon_min)
                    weight = float(grid_final[i, j])
                    smooth_points.append([lat, lon, weight])
        
        if smooth_points:
            HeatMap(
                smooth_points,
                name=f'Smooth {self.parameter} Gradient',
                min_opacity=0.4,
                max_opacity=0.8,
                radius=25,
                blur=30,  # Higher blur for smoother appearance
                gradient={
                    '0.0': '#00ff00',  # Green (low)
                    '0.5': '#ffff00',  # Yellow (medium)
                    '1.0': '#ff0000'   # Red (high)
                }
            ).add_to(m)
        
        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except:
            pass
        
        # Add controls
        self._add_map_controls(m)
        
        # Add colormap legend
        from branca.colormap import LinearColormap
        colormap = LinearColormap(
            colors=['green', 'yellow', 'red'],
            vmin=predictions.min(),
            vmax=predictions.max(),
            caption=f'{self.parameter} Concentration (mg/m³)'
        )
        colormap.add_to(m)

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
        Create a static matplotlib map with smooth interpolated gradients.
        Uses cubic interpolation with distance-based masking to prevent
        false data in cloud-covered areas.
        
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
            from scipy.interpolate import griddata
            from scipy.ndimage import gaussian_filter
            from scipy.spatial import cKDTree
            
            # Extract data
            lats = np.array([p['lat'] for p in self.points])
            lons = np.array([p['lon'] for p in self.points])
            predictions = np.array([p['prediction'] for p in self.points])
            
            # Calculate bounding box
            lat_min, lat_max = lats.min(), lats.max()
            lon_min, lon_max = lons.min(), lons.max()
            
            # Add 5% padding
            lat_range = lat_max - lat_min
            lon_range = lon_max - lon_min
            padding = max(lat_range, lon_range) * 0.05
            
            lat_min -= padding
            lat_max += padding
            lon_min -= padding
            lon_max += padding
            
            # Create high-resolution grid (800x800 for smooth seamless appearance)
            grid_resolution = 800
            grid_lon = np.linspace(lon_min, lon_max, grid_resolution)
            grid_lat = np.linspace(lat_min, lat_max, grid_resolution)
            grid_lon_mesh, grid_lat_mesh = np.meshgrid(grid_lon, grid_lat)
            
            # Stack points for interpolation
            points_xy = np.column_stack((lons, lats))
            grid_xy = np.column_stack((grid_lon_mesh.ravel(), grid_lat_mesh.ravel()))
            
            # 1. Cubic interpolation for smooth gradients
            grid_cubic = griddata(
                points_xy, predictions, 
                (grid_lon_mesh, grid_lat_mesh), 
                method='cubic'
            )
            
            # 2. Nearest neighbor for filling NaNs (safer than cubic in sparse areas)
            grid_nearest = griddata(
                points_xy, predictions,
                (grid_lon_mesh, grid_lat_mesh),
                method='nearest'
            )
            
            # 3. Combine: use cubic where available, nearest for gaps
            grid_combined = np.where(np.isnan(grid_cubic), grid_nearest, grid_cubic)
            
            # 4. Distance-based masking: only show data within 0.01 degrees (~1km) of samples
            # This prevents showing interpolated data in large cloud gaps
            tree = cKDTree(points_xy)
            distances, _ = tree.query(grid_xy)
            distances = distances.reshape(grid_lon_mesh.shape)
            
            # Mask pixels too far from any sample (likely cloud-covered areas)
            max_distance = 0.01  # ~1km in degrees (adjust as needed)
            grid_combined[distances > max_distance] = np.nan
            
            # 5. Apply Gaussian blur for organic, smooth appearance
            # Only blur the valid (non-NaN) areas
            valid_mask = ~np.isnan(grid_combined)
            if valid_mask.any():
                # Create a temporary grid for blurring
                grid_for_blur = grid_combined.copy()
                grid_for_blur[~valid_mask] = 0  # Fill NaNs with 0 for blurring
                
                # Apply Gaussian filter
                grid_smoothed = gaussian_filter(grid_for_blur, sigma=2)
                
                # Restore NaNs
                grid_smoothed[~valid_mask] = np.nan
            else:
                grid_smoothed = grid_combined
            
            # Flip vertically for correct orientation
            grid_final = np.flipud(grid_smoothed)
            
            # Create the plot
            fig, ax = plt.subplots(figsize=(14, 10))
            
            # Plot the interpolated surface (ONLY - no scatter overlay)
            extent = [lon_min, lon_max, lat_min, lat_max]
            im = ax.imshow(
                grid_final,
                extent=extent,
                origin='upper',
                cmap='RdYlGn_r',  # Red-Yellow-Green reversed (high values = red)
                alpha=1.0,  # Fully opaque for seamless appearance
                interpolation='bilinear'
            )
            
            # Add colorbar
            cbar = plt.colorbar(im, ax=ax, label=f'{self.parameter} Concentration (mg/m³)', fraction=0.046)
            
            # Labels and title
            ax.set_xlabel('Longitude', fontsize=12, fontweight='bold')
            ax.set_ylabel('Latitude', fontsize=12, fontweight='bold')
            ax.set_title(
                f'{self.parameter} - Smooth Interpolated Map\n{self.image_date.strftime("%Y-%m-%d")}',
                fontsize=14, fontweight='bold', pad=15
            )
            
            # Grid
            ax.grid(True, alpha=0.2, linestyle='--', linewidth=0.5)
            
            # Statistics text box
            avg_pred = np.mean(predictions)
            std_pred = np.std(predictions)
            min_pred = np.min(predictions)
            max_pred = np.max(predictions)
            
            stats_text = (
                f'Samples: {len(predictions)}\n'
                f'Avg: {avg_pred:.3f}\n'
                f'Std: {std_pred:.3f}\n'
                f'Min: {min_pred:.3f}\n'
                f'Max: {max_pred:.3f}'
            )
            ax.text(
                0.02, 0.98, stats_text,
                transform=ax.transAxes,
                fontsize=10,
                verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.9, edgecolor='black')
            )
            
            # Add note about interpolation
            interp_note = 'Note: Smooth gradient via cubic interpolation.\nBlank areas = clouds or no data.'
            ax.text(
                0.98, 0.02, interp_note,
                transform=ax.transAxes,
                fontsize=8,
                verticalalignment='bottom',
                horizontalalignment='right',
                style='italic',
                bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8)
            )
            
            plt.tight_layout()

        # Save to buffer
        buffer = BytesIO()
        plt.savefig(buffer, format="png", dpi=300, bbox_inches="tight")
        plt.close()

        return buffer.getvalue()
