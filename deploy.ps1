# SchemaShift - Production Deployment (PowerShell)
$ErrorActionPreference = "Continue"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " SchemaShift - Production Deployment" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Check Docker CLI
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Error: Docker CLI is not installed or not found in PATH." -ForegroundColor Red
    exit 1
}

# Check if Docker daemon / Desktop is running and accessible
$dockerCheck = docker info 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    if ($dockerCheck -match "Access is denied|elevated privileges") {
        Write-Host "[!] Docker Desktop is running, but Windows blocked access (Access is denied)." -ForegroundColor Red
        Write-Host "    FIX: Please run PowerShell as administrator, then run .\deploy.ps1 again." -ForegroundColor Yellow
    } else {
        Write-Host "[!] Docker Desktop is not currently running or engine is still starting." -ForegroundColor Yellow
        Write-Host "    Please ensure Docker Desktop is open and the engine icon is green, then try again." -ForegroundColor Yellow
    }
    Write-Host ""
    exit 1
}

# Create .env if missing
if (-not (Test-Path ".env")) {
    Write-Host "[*] .env file not found. Copying from .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
}

Write-Host "[+] Docker connected successfully!" -ForegroundColor Green
Write-Host "[+] Building and starting containers..." -ForegroundColor Green
docker compose -f docker-compose.prod.yml up -d --build
if ($LASTEXITCODE -ne 0) {
    Write-Host "[!] Docker Compose failed to start the production stack. Check port availability and the logs." -ForegroundColor Red
    exit $LASTEXITCODE
}

$healthUrl = "http://localhost:8080/health"
$healthy = $false
for ($attempt = 0; $attempt -lt 30; $attempt++) {
    try {
        $health = Invoke-WebRequest -Uri $healthUrl -TimeoutSec 3 -UseBasicParsing
        if ($health.StatusCode -eq 200) {
            $healthy = $true
            break
        }
    } catch {
        # Containers may need a little time to become ready.
    }
    Start-Sleep -Seconds 2
}

if (-not $healthy) {
    Write-Host "[!] Production containers started, but the app did not become healthy at $healthUrl." -ForegroundColor Red
    Write-Host "    Recent logs:" -ForegroundColor Yellow
    docker compose -f docker-compose.prod.yml logs --tail 50
    exit 1
}

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "[+] SchemaShift is deployed and running!" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  Frontend / Web UI:  http://localhost:8080"
Write-Host "  FastAPI Swagger UI: http://localhost:8000/docs"
Write-Host "  FastAPI Health:     http://localhost:8000/health"
Write-Host "  MySQL:              localhost:3308 (MYSQL_HOST_PORT in .env)"
Write-Host "  MongoDB:            localhost:27018 (MONGO_HOST_PORT in .env)"
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "View logs anytime with: docker compose -f docker-compose.prod.yml logs -f"
