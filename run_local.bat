@echo off
echo ========================================================
echo Starting TraceLens: Incident Timeline & Evidence Platform
echo AIORI-3 | PS-013 | Threat Tracers
echo ========================================================
echo.

IF NOT EXIST ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found.
    echo Please run: py -3.13 -m venv .venv ^&^& .\.venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

echo Starting local server on http://127.0.0.1:8000 ...
echo Press CTRL+C to stop the server.
echo.

.\.venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000 --reload
pause
