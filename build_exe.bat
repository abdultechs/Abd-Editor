@echo off
echo ========================================================
echo   Building Abd Editor V1.0 Standalone Executable (.exe)
echo ========================================================
echo.

echo Installing / Verifying PyInstaller...
py -3 -m pip install pyinstaller

echo.
echo Cleaning previous build artifacts...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

echo.
echo Building executable with PyInstaller...
py -3 -m PyInstaller --noconsole --onefile --name="Abd Editor V1.0" --add-data "resources;resources" --add-data "music;music" --hidden-import=PIL --hidden-import=PyQt5.QtCore --hidden-import=PyQt5.QtWidgets --hidden-import=PyQt5.QtGui main.py

echo.
echo ========================================================
echo   BUILD COMPLETE!
echo   Your standalone .exe is located in the "dist" folder:
echo   dist\Abd Editor V1.0.exe
echo ========================================================
pause
