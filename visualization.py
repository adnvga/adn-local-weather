"""Interactive visualizations for daily climatological measurements."""

import json
from pathlib import Path

import pandas as pd
from plotly.offline import get_plotlyjs


CHART_OUTPUT_PATH = Path(__file__).resolve().parent / "weather_chart.html"
MEASUREMENT_COLUMNS = [
    "precipitation_mm",
    "evaporation_mm",
    "maximum_temperature_c",
    "minimum_temperature_c",
]


def create_weather_chart(
    combined_dataframe: pd.DataFrame,
    default_station_id: str,
    default_year: int,
    output_path: Path = CHART_OUTPUT_PATH,
) -> Path:
    """Create an interactive dual-axis chart from daily station measurements."""
    required_columns = {"date", "station", *MEASUREMENT_COLUMNS}
    missing_columns = required_columns - set(combined_dataframe.columns)
    if missing_columns:
        missing_columns_text = ", ".join(sorted(missing_columns))
        raise ValueError(
            f"Faltan columnas requeridas para crear la gráfica: {missing_columns_text}"
        )

    chart_dataframe = combined_dataframe[
        ["date", "station", *MEASUREMENT_COLUMNS]
    ].copy()
    chart_dataframe["date"] = pd.to_datetime(chart_dataframe["date"], errors="coerce")
    chart_dataframe = chart_dataframe.dropna(subset=["date"])
    chart_dataframe["station"] = chart_dataframe["station"].astype(str)
    chart_dataframe["year"] = chart_dataframe["date"].dt.year
    chart_dataframe["date"] = chart_dataframe["date"].dt.strftime("%Y-%m-%d")

    station_ids = sorted(chart_dataframe["station"].unique())
    if default_station_id not in station_ids:
        raise ValueError(f"La estación predeterminada no existe: {default_station_id}")

    default_station_years = sorted(
        chart_dataframe.loc[
            chart_dataframe["station"] == default_station_id, "year"
        ].unique()
    )
    if not default_station_years:
        raise ValueError(
            f"La estación predeterminada no contiene mediciones: {default_station_id}"
        )
    resolved_default_year = (
        default_year if default_year in default_station_years else default_station_years[0]
    )

    measurements_json = chart_dataframe.to_json(orient="records")
    safe_measurements_json = measurements_json.replace("</", "<\\/")
    html = _build_chart_html(
      measurements_json=safe_measurements_json,
        station_ids=station_ids,
        default_station_id=default_station_id,
        default_year=resolved_default_year,
    )
    output_path.write_text(html, encoding="utf-8")
    return output_path


def _build_chart_html(
    measurements_json: str,
    station_ids: list[str],
    default_station_id: str,
    default_year: int,
) -> str:
    """Build a standalone HTML document for the weather chart."""
    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Datos climatológicos diarios</title>
  <style>
    :root {{
      color: #1f2933;
      background: #f5f7f6;
      font-family: "Segoe UI", sans-serif;
    }}
    body {{ margin: 0; padding: 24px; }}
    main {{ max-width: 1280px; margin: 0 auto; }}
    h1 {{ margin: 0 0 20px; font-size: 1.5rem; font-weight: 650; }}
    .controls {{
      display: flex;
      flex-wrap: wrap;
      gap: 16px 24px;
      align-items: end;
      padding: 16px;
      border: 1px solid #cbd5d1;
      border-radius: 8px;
      background: #ffffff;
    }}
    label {{ display: grid; gap: 6px; font-size: 0.875rem; font-weight: 600; }}
    select {{
      min-width: 132px;
      border: 1px solid #82928b;
      border-radius: 4px;
      background: #ffffff;
      padding: 6px 8px;
      font: inherit;
    }}
    fieldset {{ border: 0; margin: 0; padding: 0; }}
    legend {{ margin-bottom: 6px; font-size: 0.875rem; font-weight: 600; }}
    .series-controls {{ display: flex; flex-wrap: wrap; gap: 8px 14px; }}
    .series-controls label {{ display: flex; align-items: center; gap: 5px; font-weight: 400; }}
    input[type="checkbox"] {{ accent-color: #1f77b4; }}
    #weather-chart {{ min-height: 620px; margin-top: 18px; }}
    @media (max-width: 600px) {{ body {{ padding: 12px; }} #weather-chart {{ min-height: 480px; }} }}
  </style>
</head>
<body>
  <main>
    <h1>Datos climatológicos diarios</h1>
    <section class="controls" aria-label="Controles de la gráfica">
      <label>Estación
        <select id="station-select"></select>
      </label>
      <label>Año
        <select id="year-select"></select>
      </label>
      <fieldset>
        <legend>Series</legend>
        <div class="series-controls">
          <label><input type="checkbox" data-series="precipitation_mm" checked>Precipitación</label>
          <label><input type="checkbox" data-series="evaporation_mm" checked>Evaporación</label>
          <label><input type="checkbox" data-series="maximum_temperature_c" checked>Temperatura máxima</label>
          <label><input type="checkbox" data-series="minimum_temperature_c" checked>Temperatura mínima</label>
        </div>
      </fieldset>
    </section>
    <div id="weather-chart" aria-label="Gráfica climatológica interactiva"></div>
  </main>
  <script>{get_plotlyjs()}</script>
  <script>
    const measurements = {measurements_json};
    const stationIds = {json.dumps(station_ids)};
    const defaultStationId = {json.dumps(default_station_id)};
    const defaultYear = {default_year};
    const stationSelect = document.getElementById("station-select");
    const yearSelect = document.getElementById("year-select");
    const seriesControls = document.querySelectorAll("[data-series]");

    const series = [
      {{ key: "precipitation_mm", name: "Precipitación", color: "#1f77b4", axis: "y", unit: "mm" }},
      {{ key: "evaporation_mm", name: "Evaporación", color: "#ff7f0e", axis: "y", unit: "mm" }},
      {{ key: "maximum_temperature_c", name: "Temperatura máxima", color: "#d62728", axis: "y2", unit: "°C" }},
      {{ key: "minimum_temperature_c", name: "Temperatura mínima", color: "#2ca02c", axis: "y2", unit: "°C" }},
    ];

    function fillStationOptions() {{
      stationIds.forEach((stationId) => {{
        const option = new Option(stationId, stationId, false, stationId === defaultStationId);
        stationSelect.add(option);
      }});
    }}

    function availableYears(stationId) {{
      return [...new Set(measurements
        .filter((record) => record.station === stationId)
        .map((record) => record.year))].sort((first, second) => first - second);
    }}

    function fillYearOptions() {{
      const years = availableYears(stationSelect.value);
      const currentYear = Number(yearSelect.value);
      const preferredYear = stationSelect.value === defaultStationId && years.includes(defaultYear)
        ? defaultYear
        : years.includes(currentYear) ? currentYear : years[0];

      yearSelect.replaceChildren();
      years.forEach((year) => {{
        yearSelect.add(new Option(String(year), String(year), false, year === preferredYear));
      }});
    }}

    function renderChart() {{
      const stationId = stationSelect.value;
      const year = Number(yearSelect.value);
      const records = measurements.filter(
        (record) => record.station === stationId && record.year === year
      );
      const visibleSeries = new Set(
        [...seriesControls].filter((control) => control.checked).map((control) => control.dataset.series)
      );
      const traces = series.map((definition) => ({{
        x: records.map((record) => record.date),
        y: records.map((record) => record[definition.key]),
        type: "scatter",
        mode: "lines",
        name: definition.name,
        yaxis: definition.axis,
        visible: visibleSeries.has(definition.key),
        line: {{ color: definition.color, width: 1.8 }},
        hovertemplate: `%{{x}}<br>${{definition.name}}: %{{y:.2f}} ${{definition.unit}}<extra></extra>`,
      }}));

      Plotly.react("weather-chart", traces, {{
        title: `Estación ${{stationId}} | ${{year}}`,
        paper_bgcolor: "#ffffff",
        plot_bgcolor: "#ffffff",
        margin: {{ l: 70, r: 70, t: 60, b: 65 }},
        hovermode: "x unified",
        xaxis: {{ title: "Fecha", showgrid: true, gridcolor: "#e5e9e7" }},
        yaxis: {{ title: "Milímetros (mm)", showgrid: true, gridcolor: "#e5e9e7", zeroline: true }},
        yaxis2: {{ title: "Temperatura (°C)", overlaying: "y", side: "right", showgrid: false, zeroline: false }},
        legend: {{ orientation: "h", y: 1.12 }},
      }}, {{ responsive: true, displaylogo: false }});
    }}

    fillStationOptions();
    fillYearOptions();
    renderChart();
    stationSelect.addEventListener("change", () => {{ fillYearOptions(); renderChart(); }});
    yearSelect.addEventListener("change", renderChart);
    seriesControls.forEach((control) => control.addEventListener("change", renderChart));
  </script>
</body>
</html>
"""