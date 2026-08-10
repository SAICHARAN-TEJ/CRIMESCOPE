# CrimeScope — Production deployment script (Windows PowerShell).
#
#  1. Validates/generates .env (never overwrites existing secrets)
#  2. Builds images and starts the full stack (API, worker, beat, frontend,
#     Neo4j, Qdrant, Redis, MinIO, Postgres)
#  3. Waits for the API health endpoint
#
# Usage:  powershell -ExecutionPolicy Bypass -File scripts\deploy.ps1
#         powershell -File scripts\deploy.ps1 -SkipBuild

param(
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Write-Host "`n===== CrimeScope Deployment =====" -ForegroundColor Cyan
Set-Location $Root

# ── 1. .env validation ────────────────────────────────────────────────
if (-not (Test-Path ".env")) {
    Write-Host "ERROR: .env not found. Copy .env.example to .env and set secrets." -ForegroundColor Red
    exit 1
}

# ── 2. Build & start ───────────────────────────────────────────────────
if ($SkipBuild) {
    Write-Host "[1/3] Starting stack (skip build)..." -ForegroundColor Yellow
    docker compose up -d
} else {
    Write-Host "[1/3] Building images..." -ForegroundColor Yellow
    docker compose build
    Write-Host "[2/3] Starting stack..." -ForegroundColor Yellow
    docker compose up -d
}

# ── 3. Health wait ─────────────────────────────────────────────────────
Write-Host "[3/3] Waiting for API health..." -ForegroundColor Yellow
$api = ($env:API_PORT ?? "8000")
$deadline = (Get-Date).AddMinutes(5)
$ok = $false
while ((Get-Date) -lt $deadline) {
    try {
        $resp = Invoke-RestMethod -Uri "http://localhost:${api}/api/v1/healthz" -TimeoutSec 5
        if ($resp.status -eq "healthy") { $ok = $true; break }
    } catch { }
    Start-Sleep -Seconds 5
}

if (-not $ok) {
    Write-Host "ERROR: API did not become healthy in 5 minutes." -ForegroundColor Red
    docker compose ps
    exit 1
}

Write-Host "`n✓ CrimeScope deployed." -ForegroundColor Green
Write-Host "  API:       http://localhost:${api}/docs"
Write-Host "  Frontend:  http://localhost:$($env:FRONTEND_PORT ?? "3000")"
Write-Host "  Neo4j:     http://localhost:7474"
Write-Host "  MinIO:     http://localhost:9001"
Write-Host "  Logs:      docker compose logs -f api"
