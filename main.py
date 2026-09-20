"""Download and load the climatological daily files for Hidalgo stations."""

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


def main() -> None:
    """Download resources and print the stations nearest to the central station."""
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