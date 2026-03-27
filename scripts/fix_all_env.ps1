# ---------------------------------------------------------
# PULSEAI — Nexus Environment Resurector v1.0
# ---------------------------------------------------------

$ErrorActionPreference = "Stop"

Write-Host "🚀 Checking Python environment..." -ForegroundColor Cyan

# 1. Try to find a working Python 3
$python = Get-Command python.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
if (-not $python) {
    $python = Get-Command py.exe -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source
}

if (-not $python) {
    Write-Host "❌ Python not found in Path. Please install Python 3.12 and add to path." -ForegroundColor Red
    exit 1
}

Write-Host "✅ Found Python at: $python" -ForegroundColor Green

# 2. Recreate .venv if broken
if (Test-Path ".venv") {
    Write-Host "📂 Existing .venv found. Checking if valid..." -ForegroundColor Yellow
    if (Test-Path ".venv\Scripts\python.exe") {
        try {
            & .venv\Scripts\python.exe --version
            Write-Host "✅ .venv is valid." -ForegroundColor Green
        } catch {
            Write-Host "⚠️  .venv is broken. Deleting..." -ForegroundColor Red
            Remove-Item -Recurse -Force ".venv"
            & $python -m venv .venv
        }
    } else {
        Write-Host "⚠️  .venv is incomplete. Deleting..." -ForegroundColor Red
        Remove-Item -Recurse -Force ".venv"
        & $python -m venv .venv
    }
} else {
    Write-Host "📂 Creating new .venv..." -ForegroundColor Cyan
    & $python -m venv .venv
}

# 3. Install Backend Requirements
Write-Host "📦 Installing Backend dependencies..." -ForegroundColor Cyan
& .venv\Scripts\python.exe -m pip install --upgrade pip
& .venv\Scripts\python.exe -m pip install -r backend/requirements.txt
& .venv\Scripts\python.exe -m pip install psutil paho-mqtt pyserial  # Core essentials

# 4. Frontend Requirements
if (Test-Path "frontend") {
    Write-Host "⚛️  Checking Frontend dependencies..." -ForegroundColor Cyan
    Set-Location frontend
    if (Test-Path "node_modules") {
       Write-Host "⚠️  Deleting existing node_modules (Google Drive workaround)..." -ForegroundColor Yellow
       # This is slow on G Drive, but often the only way to fix TAR errors
       Remove-Item -Recurse -Force "node_modules"
    }
    Write-Host "🚀 Running npm install..." -ForegroundColor Cyan
    try {
        npm install --no-bin-links
        Write-Host "✅ Frontend dependencies installed (No bin links mode)." -ForegroundColor Green
    } catch {
        Write-Host "❌ npm install failed. If you are on Google Drive (G:), please move the project to C: for development." -ForegroundColor Red
    }
    Set-Location ..
}

Write-Host "✨ Environment resurrection complete. Restart your IDE/Linter." -ForegroundColor White -BackgroundColor DarkGreen
