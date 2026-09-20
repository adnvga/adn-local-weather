"""Download and load the climatological daily files for Hidalgo stations."""

from utils import Station, download_files, load_stations


def main() -> list[Station]:
    """Download the available climatological files and load their stations."""
    download_files()
    stations = load_stations()
    print(stations)


if __name__ == "__main__":
    main()