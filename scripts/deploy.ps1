# CrimeScope v4.4.0 — Production deployment script (Windows PowerShell 5.1+).
#
#  1. Validates .env exists (never overwrites secrets)
#  2. Builds images and starts the full stack
#     (API, worker, beat, frontend, Neo4j, Redis, MinIO, Postgres)
#  3. Waits for the API health endpoint
#
# Usage:  powershell -ExecutionPolicy Bypass -File scripts\deploy.ps1
#         powershell -File scripts\deploy.ps1 -SkipBuild

param(
    [switch]$SkipBuild
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

function Get-EnvOrDefault {
    param($Name, $Default)
    $value = [Environment]::GetEnvironmentVariable($Name)
    if ($value) { $value } else { $Default }
}

Write-Host ""
Write-Host "===== CrimeScope v4.4.0 Deployment =====" -ForegroundColor Cyan
Set-Location $Root

# ── 1. .env validation ──────────────────────────────────────────────────
if (-not (Test-Path ".env")) {
    Write-Host "ERROR: .env not found. Copy .env.example to .env and set secrets." -ForegroundColor Red
    exit 1
}

# ── 2. Build & start ────────────────────────────────────────────────────
if ($SkipBuild) {
    Write-Host "[1/3] Starting stack (skip build)..." -ForegroundColor Yellow
    docker compose up -d
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: 'docker compose up' failed (exit code $LASTEXITCODE)." -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[1/3] Building images..." -ForegroundColor Yellow
    docker compose build
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: 'docker compose build' failed (exit code $LASTEXITCODE)." -ForegroundColor Red
        exit 1
    }
    Write-Host "[2/3] Starting stack..." -ForegroundColor Yellow
    docker compose up -d
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: 'docker compose up' failed (exit code $LASTEXITCODE)." -ForegroundColor Red
        exit 1
    }
}

# ── 3. Health wait ──────────────────────────────────────────────────────
Write-Host "[3/3] Waiting for API health..." -ForegroundColor Yellow
$api = Get-EnvOrDefault "API_PORT" "8000"
$frontend = Get-EnvOrDefault "FRONTEND_PORT" "3000"
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

Write-Host ""
Write-Host "CrimeScope v4.4.0 deployed." -ForegroundColor Green
Write-Host "  API:       http://localhost:${api}/docs"
Write-Host "  Frontend:  http://localhost:${frontend}"
Write-Host "  Neo4j:     http://localhost:7474"
Write-Host "  MinIO:     http://localhost:9001"
Write-Host "  Logs:      docker compose logs -f api"
