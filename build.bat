@echo off
setlocal
cd /d "%~dp0"

echo.
echo ==============================
echo       Building 3Dropia
echo ==============================
echo.

python -m pip install --upgrade pip
python -m pip install PySide6 pyinstaller

rem Try to generate an EXE icon from the app itself.
python 3dropia.py --export-icon >nul 2>&1

if exist 3dropia.ico (
    python -m PyInstaller --noconfirm --clean --onefile --windowed ^
        --name "3Dropia" ^
        --icon "3dropia.ico" ^
        3dropia.py
) else (
    echo Icon export failed, building with the default executable icon.
    python -m PyInstaller --noconfirm --clean --onefile --windowed ^
        --name "3Dropia" ^
        3dropia.py
)

echo.
echo Build complete: dist\3Dropia.exe
echo.
pause
