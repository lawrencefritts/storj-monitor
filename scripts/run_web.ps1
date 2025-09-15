#!/usr/bin/env pwsh
# Start the Storj Monitor web server

param(
    [switch]$Debug,
    [switch]$Reload,
    [int]$Port = 8080,
    [string]$Host = "127.0.0.1"
)

$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptPath
$PythonPath = Join-Path $ProjectRoot "venv\Scripts\python.exe"
$WebAppPath = Join-Path $ProjectRoot "webapp\server.py"

# Check if Python virtual environment exists
if (-not (Test-Path $PythonPath)) {
    Write-Error "Python virtual environment not found. Run setup.ps1 first."
    exit 1
}

# Check if web server file exists
if (-not (Test-Path $WebAppPath)) {
    Write-Error "Web server file not found: $WebAppPath"
    exit 1
}

Write-Host "Starting Storj Monitor Web Server..." -ForegroundColor Green
Write-Host "Host: $Host" -ForegroundColor Cyan
Write-Host "Port: $Port" -ForegroundColor Cyan

if ($Debug) {
    Write-Host "Debug mode: ON" -ForegroundColor Yellow
}

if ($Reload) {
    Write-Host "Auto-reload: ON" -ForegroundColor Yellow
}

Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Gray
Write-Host ""

# Set working directory to project root
Set-Location $ProjectRoot

# Build uvicorn command arguments
$uvicornArgs = @(
    "-m", "uvicorn",
    "webapp.server:app",
    "--host", $Host,
    "--port", $Port
)

if ($Debug) {
    $uvicornArgs += "--log-level", "debug"
}

if ($Reload) {
    $uvicornArgs += "--reload"
}

# Start the web server
try {
    & $PythonPath $uvicornArgs
} catch {
    Write-Error "Failed to start web server: $_"
    exit 1
}

Write-Host "Web server stopped." -ForegroundColor Yellow