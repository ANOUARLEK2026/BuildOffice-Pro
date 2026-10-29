@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================================
echo BuildOffice Pro - Document Generation Dependencies
echo ============================================================
echo.

set "PYTHON_EXE="
if exist "%~dp0.venv\Scripts\python.exe" set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"

if not defined PYTHON_EXE (
    for /f "delims=" %%P in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do if not defined PYTHON_EXE set "PYTHON_EXE=%%P"
)

if not defined PYTHON_EXE (
    for /f "delims=" %%P in ('where python 2^>nul') do if not defined PYTHON_EXE set "PYTHON_EXE=%%P"
)

if not defined PYTHON_EXE (
    echo ERROR: Python was not found.
    echo Install Python 3.13/3.14 and run this file again.
    pause
    exit /b 1
)

echo Python interpreter:
echo %PYTHON_EXE%
echo.

where uv >nul 2>nul
if not errorlevel 1 (
    echo Installing with uv into the active Python environment...
    uv pip install --python "%PYTHON_EXE%" python-docx openpyxl
    if not errorlevel 1 goto VERIFY
    echo uv installation failed. Trying pip...
)

echo Installing with pip...
"%PYTHON_EXE%" -m pip install python-docx openpyxl
if errorlevel 1 (
    echo.
    echo Installation failed. If this Python environment is externally managed,
    echo create a project virtual environment and run this installer again.
    pause
    exit /b 1
)

:VERIFY
"%PYTHON_EXE%" -c "import docx, openpyxl; print('python-docx:', docx.__version__ if hasattr(docx,'__version__') else 'installed'); print('openpyxl:', openpyxl.__version__)"
if errorlevel 1 (
    echo Verification failed.
    pause
    exit /b 1
)

echo.
echo SUCCESS: Word/Excel generation dependencies are ready.
echo Restart BuildOffice Pro before generating Word/Excel files.
pause
exit /b 0
