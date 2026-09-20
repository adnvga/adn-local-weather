Region analysis
Data from:
 - CANAGUA local data
 - era5 atmospheric data
 - noaa ocean data

## ERA5

`download_era5.py` verifica la existencia de
`resources/era5_single_levels_timeseries.nc`. Si el archivo no existe o está
vacío, descarga la solicitud ERA5 de Hidalgo definida en el script.

Antes de ejecutarlo, instala las dependencias y configura las credenciales de
CDS API en tu perfil de Copernicus, incluido el acceso al dataset solicitado.
Luego ejecuta:

```bash
python download_era5.py
```

Las ejecuciones posteriores reutilizan el archivo local y no vuelven a
descargarlo.
