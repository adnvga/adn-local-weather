"""Utilities for managing local climatological resources."""

from dataclasses import dataclass
from pathlib import Path
from time import sleep
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


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