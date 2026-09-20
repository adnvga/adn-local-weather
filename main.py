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
CONAGUA_UTC_OFFSET_HOURS = 6
ERA5_TIME_COLUMN = "era5_utc_minus_6"
ERA5_COORDINATE_COLUMNS = {"latitude", "longitude"}


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
    """Load non-wave extracted ERA5 NetCDF files into pandas DataFrames."""
    dataframes = {}
    for netcdf_path in netcdf_paths:
        if "timeseries-wav" in netcdf_path.name.lower():
            continue

        with xr.open_dataset(netcdf_path) as dataset:
            dataframes[netcdf_path.name] = add_conagua_time_columns(
                dataset.to_dataframe()
            )
    return dataframes


def add_conagua_time_columns(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Add fixed UTC-6 timestamps and daily dates aligned with CONAGUA data."""
    if not isinstance(dataframe.index, pd.DatetimeIndex):
        raise ValueError("El DataFrame ERA5 debe tener un índice de fecha y hora.")

    dataframe = dataframe.copy()
    utc_minus_6 = dataframe.index - pd.Timedelta(hours=CONAGUA_UTC_OFFSET_HOURS)
    dataframe["era5_utc_minus_6"] = utc_minus_6
    dataframe["fecha_conagua"] = utc_minus_6.normalize()
    return dataframe


def aggregate_era5_daily(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Summarize every ERA5 parameter by local UTC-6 calendar day."""
    if ERA5_TIME_COLUMN not in dataframe:
        raise ValueError(f"Falta la columna de tiempo ERA5: {ERA5_TIME_COLUMN}")

    parameter_columns = [
        column
        for column in dataframe.select_dtypes(include="number").columns
        if column not in ERA5_COORDINATE_COLUMNS
    ]
    if not parameter_columns:
        raise ValueError("El DataFrame ERA5 no contiene parámetros numéricos.")

    daily_dataframe = (
        dataframe.assign(
            fecha_conagua=pd.to_datetime(dataframe[ERA5_TIME_COLUMN]).dt.normalize()
        )
        .groupby("fecha_conagua")[parameter_columns]
        .agg(["mean", "min", "max"])
    )
    daily_dataframe.columns = [
        f"{parameter}_{aggregation}"
        for parameter, aggregation in daily_dataframe.columns.to_flat_index()
    ]
    return daily_dataframe


def aggregate_era5_daily_dataframes(
    dataframes: dict[str, pd.DataFrame],
) -> dict[str, pd.DataFrame]:
    """Create one local UTC-6 daily ERA5 dataset for each source DataFrame."""
    return {
        filename: aggregate_era5_daily(dataframe)
        for filename, dataframe in dataframes.items()
    }


def create_master_dataframe(
    station_dataframe: pd.DataFrame,
    era5_daily_dataframes: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """Join central CONAGUA targets with daily ERA5 predictor variables."""
    if len(era5_daily_dataframes) != 1:
        raise ValueError(
            "Se requiere exactamente un DataFrame diario de ERA5 para crear el "
            "DataFrame maestro."
        )
    if "date" not in station_dataframe:
        raise ValueError("El DataFrame de CONAGUA debe contener la columna date.")

    era5_daily_dataframe = next(iter(era5_daily_dataframes.values()))
    conagua_columns = {
        column: f"conagua_{column}"
        for column in station_dataframe.columns
        if column != "date"
    }
    conagua_dataframe = station_dataframe.rename(columns=conagua_columns)

    return conagua_dataframe.merge(
        era5_daily_dataframe.reset_index(),
        how="left",
        left_on="date",
        right_on="fecha_conagua",
        validate="one_to_one",
    )


def print_era5_dataframes(dataframes: dict[str, pd.DataFrame]) -> None:
    """Print the first 15 rows of every local ERA5 DataFrame."""
    for filename, dataframe in dataframes.items():
        print(f"\nERA5: {filename}")
        print(dataframe.head(15))


def main() -> None:
    """Download resources and print the stations nearest to the central station."""
    era5_daily_dataframes: dict[str, pd.DataFrame] = {}
    if has_era5_resource():
        era5_netcdf_paths = extract_era5_netcdf_files(ERA5_RESOURCE_PATH)
        era5_dataframes = load_era5_dataframes(era5_netcdf_paths)
        era5_daily_dataframes = aggregate_era5_daily_dataframes(era5_dataframes)
        print_era5_dataframes(era5_daily_dataframes)
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

    print(station_dataframes[central_station.station_id].head(15))
    if era5_daily_dataframes:
        master_df = create_master_dataframe(
            station_dataframes[central_station.station_id], era5_daily_dataframes
        )
        print("\nPrimeras 15 filas del DataFrame maestro CONAGUA-ERA5:")
        print(master_df.head(15))

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