@echo off
echo.
echo  ************************************
echo  *   Ayushi Life OS - Backend       *
echo  ************************************
echo.
echo  Starting server...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  ERROR: Python not found!
    echo  Please install Python from https://python.org
    pause
    exit /b 1
)

REM Install dependencies if needed
echo  Checking dependencies...
pip install flask flask-cors --quiet

echo.
echo  Server starting at http://localhost:5000
echo.
echo  To use on iPhone:
echo   1. Make sure your phone and PC are on same WiFi
echo   2. Find your PC's IP: run 'ipconfig' in another terminal
echo   3. Open http://YOUR_PC_IP:5000 in Safari on iPhone
echo   4. Tap Share then 'Add to Home Screen'
echo.
echo  Press Ctrl+C to stop the server
echo.

python server.py
pause
