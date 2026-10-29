@echo off
rem Double-click to start the MBTA LED map simulator and open it in Chrome.
rem Close this window (or press Ctrl+C) to stop the simulator.
title MBTA LED Simulator
cd /d "%~dp0"

set URL=http://127.0.0.1:8000

rem Already running? Just open the page.
curl -s -o nul %URL%/api/layout && (
    start "" chrome %URL%
    exit /b
)

if not exist ".venv\Scripts\python.exe" (
    echo Setting up the Python environment for the first time...
    python -m venv .venv || goto :fail
    ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt || goto :fail
)

rem Open Chrome a couple of seconds after the server starts.
start "" /b cmd /c "timeout /t 2 >nul & start "" chrome %URL%"
".venv\Scripts\python.exe" server.py
if errorlevel 1 pause
goto :eof

:fail
echo.
echo Setup failed. See the message above.
pause
