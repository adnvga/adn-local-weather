"""Ensure the ERA5 time-series NetCDF resource is available locally."""

from pathlib import Path


DATASET = "reanalysis-era5-single-levels-timeseries"
RESOURCES_DIR = Path(__file__).resolve().parent / "resources"
ERA5_RESOURCE_PATH = RESOURCES_DIR / "era5_single_levels_timeseries.zip"
ERA5_REQUEST = {
    "variable": [
        "100m_u_component_of_wind",
        "100m_v_component_of_wind",
        "10m_u_component_of_wind",
        "10m_v_component_of_wind",
        "10m_wind_gust_since_previous_post_processing",
        "2m_dewpoint_temperature",
        "2m_temperature",
        "boundary_layer_height",
        "cloud_base_height",
        "mean_sea_level_pressure",
        "mean_wave_direction",
        "mean_wave_period",
        "sea_surface_temperature",
        "significant_height_of_combined_wind_waves_and_swell",
        "skin_temperature",
        "surface_latent_heat_flux",
        "surface_pressure",
        "surface_sensible_heat_flux",
        "surface_solar_radiation_downwards",
        "surface_thermal_radiation_downwards",
        "total_cloud_cover",
        "total_precipitation",
        "total_sky_direct_solar_radiation_at_surface",
    ],
    "location": {"longitude": -99, "latitude": 20.5},
    "date": ["1977-01-01/2026-01-15"],
    "data_format": "netcdf",
}


def has_era5_resource(resource_path: Path = ERA5_RESOURCE_PATH) -> bool:
    """Return whether the local ERA5 resource exists and is not empty."""
    return resource_path.is_file() and resource_path.stat().st_size > 0


def ensure_era5_resource(resource_path: Path = ERA5_RESOURCE_PATH) -> Path:
    """Download the ERA5 resource when it is not already stored locally."""
    if has_era5_resource(resource_path):
        print(f"Recurso ERA5 disponible: {resource_path}")
        return resource_path

    try:
        import cdsapi
    except ImportError as error:
        raise RuntimeError(
            "No se encontró cdsapi. Instala las dependencias con "
            "python -m pip install -r requirements.txt."
        ) from error

    resource_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Descargando recurso ERA5 en: {resource_path}")
    client = cdsapi.Client()
    client.retrieve(DATASET, ERA5_REQUEST, str(resource_path))
    print(f"Recurso ERA5 descargado: {resource_path}")
    return resource_path


if __name__ == "__main__":
    ensure_era5_resource()