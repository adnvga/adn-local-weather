"""Utilities for managing local climatological resources."""

from dataclasses import dataclass
from collections.abc import Iterable
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
from time import sleep
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd


BASE_URL = (
    "https://smn.conagua.gob.mx/tools/RESOURCES/Normales_Climatologicas/"
    "Diarios/hgo"
)
FIRST_FILE = 13001
LAST_FILE = 13169
RESOURCES_DIR = Path(__file__).resolve().parent / "resources"
DOWNLOAD_ATTEMPTS = 4
RETRYABLE_STATUS_CODES = { 502, 503, 504}
REQUEST_INTERVAL_SECONDS = 0.4
EARTH_RADIUS_KM = 6_371.0088
KNOWN_MISSING_FILES = frozenset(
    {
        "dia13023.txt",
        "dia13054.txt",
        "dia13058.txt",
        "dia13102.txt",
        "dia13103.txt",
        "dia13107.txt",
        "dia13110.txt",
        "dia13114.txt",
        "dia13119.txt",
        "dia13126.txt",
        "dia13134.txt",
        "dia13136.txt",
        "dia13142.txt",
        "dia13143.txt",
        "dia13146.txt",
        "dia13153.txt",
        "dia13163.txt",
    }
)
STATION_FIELDS = {
    "ESTACIÓN": "station_id",
    "NOMBRE": "name",
    "ESTADO": "state",
    "MUNICIPIO": "municipality",
    "SITUACIÓN": "status",
    "U. ADMNVA.": "administrative_unit",
    "CVE-OMM": "omm_code",
    "LATITUD": "latitude",
    "LONGITUD": "longitude",
    "ALTITUD": "altitude_meters",
}
DAILY_DATA_COLUMNS = [
    "date",
    "precipitation_mm",
    "evaporation_mm",
    "maximum_temperature_c",
    "minimum_temperature_c",
]


@dataclass(frozen=True, slots=True)
class Station:
    """Station metadata extracted from a daily climatology resource."""

    filename: str
    station_id: str
    name: str
    state: str
    municipality: str
    status: str
    administrative_unit: str
    omm_code: str
    latitude: float
    longitude: float
    altitude_meters: float


def download_file(url: str, destination: Path) -> None:
    """Download one file, retrying transient server and network errors."""
    request = Request(url, headers={"User-Agent": "adn-local-weather/1.0"})

    for attempt in range(1, DOWNLOAD_ATTEMPTS + 1):
        try:
            with urlopen(request, timeout=30) as response:
                destination.write_bytes(response.read())
            return
        except HTTPError as error:
            if error.code not in RETRYABLE_STATUS_CODES or attempt == DOWNLOAD_ATTEMPTS:
                raise
        except URLError:
            if attempt == DOWNLOAD_ATTEMPTS:
                raise

        if attempt < DOWNLOAD_ATTEMPTS:
            sleep(attempt * 2)


def download_files() -> None:
    """Download all daily climatology files into the resources directory."""
    RESOURCES_DIR.mkdir(parents=True, exist_ok=True)
    failed_files: list[str] = []

    for file_number in range(FIRST_FILE, LAST_FILE + 1):
        file_name = f"dia{file_number}.txt"
        destination = RESOURCES_DIR / file_name

        if file_name in KNOWN_MISSING_FILES:
            continue

        if destination.is_file() and destination.stat().st_size > 0:
            continue

        url = f"{BASE_URL}/{file_name}"

        try:
            download_file(url, destination)
        except (HTTPError, URLError) as error:
            error_code = (
                error.code
                if isinstance(error, HTTPError)
                else getattr(error.reason, "errno", "N/D")
            )
            error_details = (
                f"{file_name} | codigo: {error_code} | error: {error.reason}"
            )
            failed_files.append(error_details)
            print(f"No se pudo descargar: {error_details}")
        else:
            print(f"Descargado: {file_name}")
        finally:
            sleep(REQUEST_INTERVAL_SECONDS)


def load_stations(resources_dir: Path = RESOURCES_DIR) -> list[Station]:
    """Load station metadata from every local daily climatology resource."""
    return [
        parse_station(resource_path)
        for resource_path in sorted(resources_dir.glob("dia*.txt"))
    ]


def find_station(stations: Iterable[Station], station_id: str) -> Station:
    """Return the station identified by its climatological station code."""
    for station in stations:
        if station.station_id == station_id:
            return station

    raise ValueError(f"No se encontró la estación: {station_id}")


def find_stations_within_radius(
    central_station: Station,
    stations: Iterable[Station],
    radius_km: float,
) -> list[tuple[Station, float]]:
    """Return other stations in a radius, sorted from nearest to farthest."""
    if radius_km < 0:
        raise ValueError("El radio no puede ser negativo.")

    nearby_stations = []
    for station in stations:
        if station.station_id == central_station.station_id:
            continue

        distance_km = distance_between_stations(central_station, station)
        if distance_km <= radius_km:
            nearby_stations.append((station, distance_km))

    return sorted(nearby_stations, key=lambda station_with_distance: station_with_distance[1])


def distance_between_stations(first_station: Station, second_station: Station) -> float:
    """Calculate the great-circle distance between two stations in kilometers."""
    latitude_delta = radians(second_station.latitude - first_station.latitude)
    longitude_delta = radians(second_station.longitude - first_station.longitude)
    first_latitude = radians(first_station.latitude)
    second_latitude = radians(second_station.latitude)

    haversine = (
        sin(latitude_delta / 2) ** 2
        + cos(first_latitude) * cos(second_latitude) * sin(longitude_delta / 2) ** 2
    )
    return 2 * EARTH_RADIUS_KM * asin(sqrt(haversine))


def load_station_dataframes(
    stations: Iterable[Station], resources_dir: Path = RESOURCES_DIR
) -> dict[str, pd.DataFrame]:
    """Load one daily-measurement DataFrame for each supplied station."""
    return {
        station.station_id: load_station_dataframe(station, resources_dir)
        for station in stations
    }


def load_station_dataframe(
    station: Station, resources_dir: Path = RESOURCES_DIR
) -> pd.DataFrame:
    """Load the daily measurements for one station into a DataFrame."""
    resource_path = resources_dir / station.filename
    data_start_line = _find_daily_data_start_line(resource_path)
    dataframe = pd.read_csv(
        resource_path,
        sep="\t",
        skiprows=data_start_line,
        header=None,
        names=DAILY_DATA_COLUMNS,
        na_values=["NULO"],
    ).dropna(how="all")

    dataframe["date"] = pd.to_datetime(
        dataframe["date"], format="%Y-%m-%d", errors="coerce"
    )
    for column in DAILY_DATA_COLUMNS[1:]:
        dataframe[column] = pd.to_numeric(dataframe[column], errors="coerce")

    dataframe["station"] = station.station_id
    return dataframe


def combine_station_dataframes(
    station_dataframes: Iterable[pd.DataFrame],
) -> pd.DataFrame:
    """Combine individual station DataFrames into one indexed table."""
    return pd.concat(station_dataframes, ignore_index=True)


def parse_station(resource_path: Path) -> Station:
    """Extract station metadata from the header of one climatology resource."""
    metadata: dict[str, str] = {}

    for line in resource_path.read_text(encoding="utf-8").splitlines():
        if ":" not in line:
            continue

        label, value = line.split(":", maxsplit=1)
        label = " ".join(label.split())
        if label in STATION_FIELDS:
            metadata[STATION_FIELDS[label]] = value.strip()

    missing_fields = set(STATION_FIELDS.values()) - metadata.keys()
    if missing_fields:
        missing_fields_text = ", ".join(sorted(missing_fields))
        raise ValueError(
            f"{resource_path.name} no contiene los campos: {missing_fields_text}"
        )

    return Station(
        filename=resource_path.name,
        station_id=metadata["station_id"],
        name=metadata["name"],
        state=metadata["state"],
        municipality=metadata["municipality"],
        status=metadata["status"],
        administrative_unit=metadata["administrative_unit"],
        omm_code=metadata["omm_code"],
        latitude=_parse_number(metadata["latitude"], resource_path),
        longitude=_parse_number(metadata["longitude"], resource_path),
        altitude_meters=_parse_number(metadata["altitude_meters"], resource_path),
    )


def _parse_number(value: str, resource_path: Path) -> float:
    """Parse the leading numeric value from a metadata field with units."""
    try:
        return float(value.split(maxsplit=1)[0].replace(",", "."))
    except (IndexError, ValueError) as error:
        raise ValueError(
            f"{resource_path.name} contiene un valor numérico inválido: {value!r}"
        ) from error


def _find_daily_data_start_line(resource_path: Path) -> int:
    """Return the first daily record line, after headers and measurement units."""
    for line_number, line in enumerate(
        resource_path.read_text(encoding="utf-8").splitlines()
    ):
        if line.strip().startswith("FECHA"):
            return line_number + 2

    raise ValueError(f"{resource_path.name} no contiene el encabezado de mediciones.")