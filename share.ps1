# SchemaShift - Free Public Tunnel Launcher (PowerShell)
$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " SchemaShift - Free Public Tunnel (Localhost Hosting)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Do not publish a tunnel unless the production frontend and backend are healthy.
try {
    $health = Invoke-WebRequest -Uri "http://localhost:8080/health" -TimeoutSec 5 -UseBasicParsing
    if ($health.StatusCode -ne 200) {
        Write-Host "[!] SchemaShift health check returned HTTP $($health.StatusCode). Start the production stack first." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "[!] SchemaShift is not healthy at http://localhost:8080/health. Start it with .\deploy.ps1 before sharing." -ForegroundColor Red
    exit 1
}

# 1. Check if cloudflared.exe exists, download if missing
$CloudflaredPath = Join-Path $PSScriptRoot "cloudflared.exe"

if (-not (Test-Path $CloudflaredPath)) {
    Write-Host "[*] Downloading cloudflared (official open-source tool)..." -ForegroundColor Yellow
    $DownloadUrl = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
    try {
        Invoke-WebRequest -Uri $DownloadUrl -OutFile $CloudflaredPath -TimeoutSec 120
    } catch {
        Remove-Item $CloudflaredPath -Force -ErrorAction SilentlyContinue
        Write-Host "[!] Could not download cloudflared: $($_.Exception.Message)" -ForegroundColor Red
        exit 1
    }
    Write-Host "[+] Download complete!" -ForegroundColor Green
}

if (-not (Test-Path $CloudflaredPath) -or (Get-Item $CloudflaredPath).Length -eq 0) {
    Write-Host "[!] cloudflared.exe is missing or empty. The tunnel was not started." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "----------------------------------------------------------" -ForegroundColor Gray
Write-Host "  Starting public tunnel to http://localhost:8080" -ForegroundColor Green
Write-Host "  Copy the https://*.trycloudflare.com link from below" -ForegroundColor Yellow
Write-Host "  Anyone with that link can access the app while the tunnel is running." -ForegroundColor Yellow
Write-Host "  Press Ctrl + C at any time to take the app offline" -ForegroundColor Red
Write-Host "----------------------------------------------------------" -ForegroundColor Gray
Write-Host ""

# 2. Run the tunnel
& $CloudflaredPath tunnel --url http://localhost:8080
if ($LASTEXITCODE -ne 0) {
    Write-Host "[!] cloudflared exited with code $LASTEXITCODE." -ForegroundColor Red
    exit $LASTEXITCODE
}
