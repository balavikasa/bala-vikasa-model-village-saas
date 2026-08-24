$ErrorActionPreference = "Stop"

Write-Host "Bala Vikasa Model Village SaaS 2026.27.9 - local verification" -ForegroundColor Cyan

if (-not (Test-Path ".\wsgi.py")) {
    throw "Run this script from the application root."
}

python -m flask --app wsgi db upgrade
if ($LASTEXITCODE -ne 0) { throw "Database migration failed." }

python -m ruff check .
if ($LASTEXITCODE -ne 0) { throw "Ruff checks failed." }

python -m pytest
if ($LASTEXITCODE -ne 0) { throw "Tests failed." }

Write-Host ""
Write-Host "Verification passed. Start the application with:" -ForegroundColor Green
Write-Host "  python -m flask --app wsgi run --debug --host 127.0.0.1 --port 5000"
