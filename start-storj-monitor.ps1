# Start Storj Monitor with Satellite Tracking
Write-Host "======================================================" -ForegroundColor Green
Write-Host "Starting Storj Monitor with Satellite Tracking" -ForegroundColor Green
Write-Host "======================================================" -ForegroundColor Green

# Check if virtual environment exists
if (-not (Test-Path "venv\Scripts\activate.ps1")) {
    Write-Host "Error: Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please run setup first." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Start collector in background
Write-Host "[1/2] Starting Data Collector with Satellite Tracking..." -ForegroundColor Yellow
$collectorJob = Start-Job -ScriptBlock {
    Set-Location $args[0]
    & "venv\Scripts\activate.ps1"
    python -m collector.service
} -ArgumentList (Get-Location).Path

Start-Sleep -Seconds 3

# Start web server in background  
Write-Host "[2/2] Starting Web Server..." -ForegroundColor Yellow
$webJob = Start-Job -ScriptBlock {
    Set-Location $args[0]
    & "venv\Scripts\activate.ps1"
    python -m webapp.server
} -ArgumentList (Get-Location).Path

Start-Sleep -Seconds 5

# Check if services are running
Write-Host "Checking services..." -ForegroundColor Yellow
$port8080 = netstat -an | Select-String ":8080.*LISTENING"

if ($port8080) {
    Write-Host "======================================================" -ForegroundColor Green
    Write-Host "✅ Storj Monitor is now running with satellite data!" -ForegroundColor Green
    Write-Host "======================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "🌐 Dashboard:     http://localhost:8080" -ForegroundColor Cyan
    Write-Host "🗄️  Database:      http://localhost:8080/db" -ForegroundColor Cyan
    Write-Host "🛰️  Satellites:    http://localhost:8080/api/satellites" -ForegroundColor Cyan
    Write-Host "📊 API Docs:      http://localhost:8080/api/docs" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "📁 Logs are in the 'logs' directory" -ForegroundColor Gray
    Write-Host ""
    
    # Open dashboard
    Start-Process "http://localhost:8080"
    
    Write-Host "Services are running in background jobs:" -ForegroundColor Yellow
    Write-Host "  Collector Job ID: $($collectorJob.Id)" -ForegroundColor Gray
    Write-Host "  Web Server Job ID: $($webJob.Id)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "To stop services, run: Get-Job | Stop-Job" -ForegroundColor Yellow
    Write-Host "To view logs: Get-Job | Receive-Job" -ForegroundColor Yellow
    
} else {
    Write-Host "❌ Web server failed to start!" -ForegroundColor Red
    Get-Job | Receive-Job
}

Write-Host ""
Read-Host "Press Enter to continue"