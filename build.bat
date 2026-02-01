@echo off
echo Building PA-SSH-prep.exe...
pyinstaller --onefile --windowed --name PA-SSH-prep src/main.py
echo.
echo Build complete! Output: dist\PA-SSH-prep.exe
pause
