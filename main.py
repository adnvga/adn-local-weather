"""Download and load the climatological daily files for Hidalgo stations."""

from pathlib import Path
from shutil import copyfileobj
from zipfile import BadZipFile, ZipFile

import pandas as pd
import xarray as xr

from download_era5 import ERA5_RESOURCE_PATH, has_era5_resource
from utils import (
    combine_station_dataframes,
    download_files,
    find_station,
    find_stations_within_radius,
    load_station_dataframes,
    load_stations,
)
from visualization import create_weather_chart

CENTRAL_STATION_ID = "13105"
SEARCH_RADIUS_KM = 15.0
DEFAULT_CHART_YEAR = 2025
MILLIMETERS_AXIS_UPPER_LIMIT = 70.0
TEMPERATURE_AXIS_UPPER_LIMIT_C = 100.0


def extract_era5_netcdf_files(archive_path: Path) -> list[Path]:
    """Extract each NetCDF file in an ERA5 archive and return local paths."""
    extraction_dir = archive_path.with_suffix("")
    extraction_dir.mkdir(parents=True, exist_ok=True)

    try:
        with ZipFile(archive_path) as archive:
            netcdf_entries = [
                entry
                for entry in archive.infolist()
                if not entry.is_dir() and entry.filename.lower().endswith(".nc")
            ]
            if not netcdf_entries:
                raise ValueError(f"El archivo no contiene archivos NetCDF: {archive_path}")

            extracted_paths: list[Path] = []
            for entry in netcdf_entries:
                destination = extraction_dir / Path(entry.filename).name
                if (
                    not destination.is_file()
                    or destination.stat().st_size != entry.file_size
                ):
                    with archive.open(entry) as source, destination.open("wb") as target:
                        copyfileobj(source, target)
                extracted_paths.append(destination)
    except BadZipFile as error:
        raise ValueError(f"El recurso ERA5 no es un archivo ZIP válido: {archive_path}") from error

    return extracted_paths


def load_era5_dataframes(netcdf_paths: list[Path]) -> dict[str, pd.DataFrame]:
    """Load every extracted ERA5 NetCDF file into a pandas DataFrame."""
    dataframes = {}
    for netcdf_path in netcdf_paths:
        with xr.open_dataset(netcdf_path) as dataset:
            dataframes[netcdf_path.name] = dataset.to_dataframe()
    return dataframes


def print_era5_dataframes(dataframes: dict[str, pd.DataFrame]) -> None:
    """Print the first 15 rows of every local ERA5 DataFrame."""
    for filename, dataframe in dataframes.items():
        print(f"\nERA5: {filename}")
        print(dataframe.head(15))


def main() -> None:
    """Download resources and print the stations nearest to the central station."""
    if has_era5_resource():
        era5_netcdf_paths = extract_era5_netcdf_files(ERA5_RESOURCE_PATH)
        era5_dataframes = load_era5_dataframes(era5_netcdf_paths)
        print_era5_dataframes(era5_dataframes)
    else:
        print(
            "No se encontró el recurso ERA5: "
            f"{ERA5_RESOURCE_PATH}. Ejecuta download_era5.py para descargarlo."
        )

    download_files()
    stations = load_stations()
    central_station = find_station(stations, CENTRAL_STATION_ID)
    nearby_stations = find_stations_within_radius(
        central_station, stations, SEARCH_RADIUS_KM
    )
    selected_stations = [
        central_station,
        *(station for station, _ in nearby_stations),
    ]
    station_dataframes = load_station_dataframes(selected_stations)
    combined_dataframe = combine_station_dataframes(station_dataframes.values())
    chart_path = create_weather_chart(
        combined_dataframe,
        default_station_id=central_station.station_id,
        default_year=DEFAULT_CHART_YEAR,
        millimeters_axis_upper_limit=MILLIMETERS_AXIS_UPPER_LIMIT,
        temperature_axis_upper_limit_c=TEMPERATURE_AXIS_UPPER_LIMIT_C,
    )

    print(
        "Estación central: "
        f"{central_station.station_id} - {central_station.name} "
        f"({central_station.municipality}, {central_station.state})"
    )
    print(f"Estaciones dentro de {SEARCH_RADIUS_KM:g} km:")
    for station, distance_km in nearby_stations:
        print(
            f"{station.station_id} - {station.name} "
            f"({station.municipality}, {station.state}) | {distance_km:.2f} km"
        )
    print(
        f"DataFrames creados: {len(station_dataframes)} | "
        f"Registros combinados: {len(combined_dataframe)}"
    )
    print(f"Gráfica interactiva creada: {chart_path}")


if __name__ == "__main__":
    main()