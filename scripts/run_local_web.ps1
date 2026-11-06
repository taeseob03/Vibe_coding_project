param([int]$Port = 8001)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectRoot
try {
    $pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $pythonPath)) {
        throw 'Python environment missing. Run python -m venv .venv, then install requirements-dev.lock.'
    }
    $env:APP_ENV = 'development'
    $env:DEV_AUTH_ENABLED = 'false'
    $env:LOCAL_WEB_PREVIEW_ENABLED = 'true'
    & $pythonPath scripts/init_env.py
    if ($LASTEXITCODE -ne 0) { throw 'Environment initialization failed.' }
    & $pythonPath -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) { throw 'Migration failed.' }
    Write-Host "Open http://127.0.0.1:$Port (Ctrl+C to stop)"
    & $pythonPath -m uvicorn app.main:app --host 127.0.0.1 --port $Port
} finally {
    Pop-Location
}
