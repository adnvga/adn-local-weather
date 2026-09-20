@echo off

REM switch to script directory
cd /d "%~dp0"

call ".venv\Scripts\activate.bat"

python download_era5.py

deactivate