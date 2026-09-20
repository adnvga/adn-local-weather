"""Download and load the climatological daily files for Hidalgo stations."""

from utils import (
    download_files,
    find_station,
    find_stations_within_radius,
    load_stations,
)

CENTRAL_STATION_ID = "13105"
SEARCH_RADIUS_KM = 15.0


def main() -> None:
    """Download resources and print the stations nearest to the central station."""
    download_files()
    stations = load_stations()
    central_station = find_station(stations, CENTRAL_STATION_ID)
    nearby_stations = find_stations_within_radius(
        central_station, stations, SEARCH_RADIUS_KM
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


if __name__ == "__main__":
    main()