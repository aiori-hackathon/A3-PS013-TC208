Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "Starting TraceLens: Incident Timeline & Evidence Platform" -ForegroundColor Cyan
Write-Host "AIORI-3 | PS-013 | Threat Tracers" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "[ERROR] Virtual environment not found." -ForegroundColor Red
    Write-Host "Please run: py -3.13 -m venv .venv; .\.venv\Scripts\pip install -r requirements.txt"
    exit 1
}

Write-Host "Starting local server on http://127.0.0.1:8000 ..." -ForegroundColor Green
Write-Host "Press CTRL+C to stop the server." -ForegroundColor Yellow
Write-Host ""

& ".\.venv\Scripts\uvicorn.exe" app.main:app --host 127.0.0.1 --port 8000 --reload
