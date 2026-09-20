"""Utilities for managing local climatological resources."""

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
RETRYABLE_STATUS_CODES = {500, 502, 503, 504}
REQUEST_INTERVAL_SECONDS = 0.4


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
        url = f"{BASE_URL}/{file_name}"

        if destination.is_file() and destination.stat().st_size > 0:
            continue

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

    if failed_files:
        failed_files_text = ", ".join(failed_files)
        raise RuntimeError(f"Archivos pendientes: {failed_files_text}")