@echo off
rem Starts the portal on Windows: website, scraper and digest mailer in one process.
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo No virtual environment yet - running setup first.
  python setup.py
  if errorlevel 1 (
    echo.
    echo Setup failed. Is Python 3.10+ installed and on your PATH?
    echo Check with:  python --version
    pause
    exit /b 1
  )
)

echo Starting InternRadar on http://127.0.0.1:8700
start "" http://127.0.0.1:8700
".venv\Scripts\python.exe" app.py
pause
