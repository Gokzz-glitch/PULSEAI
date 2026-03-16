$ErrorActionPreference = "Stop"

$dockerBin = "C:\Program Files\Docker\Docker\resources\bin"
if (Test-Path $dockerBin) {
  $env:PATH = "$dockerBin;$env:PATH"
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  Write-Error "Docker CLI not found. Install Docker Desktop and restart terminal."
}

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
  Write-Host "Created .env from .env.example"
}

Write-Host "Starting PulseAI production stack..."
docker compose -f docker-compose.prod.yml up --build -d

Write-Host "\nServices:"
docker compose -f docker-compose.prod.yml ps

Write-Host "\nBackend health:"
try {
  (Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" | ConvertTo-Json -Depth 5)
} catch {
  Write-Host $_.Exception.Message
}

Write-Host "\nFrontend health:"
try {
  (Invoke-WebRequest -Uri "http://127.0.0.1:8080" -UseBasicParsing).StatusCode
} catch {
  Write-Host $_.Exception.Message
}
