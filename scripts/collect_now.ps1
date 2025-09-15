#!/usr/bin/env pwsh
# Trigger immediate data collection from Storj nodes

Write-Host "🚀 Triggering immediate data collection..." -ForegroundColor Green

$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptPath
$PythonScript = Join-Path $ProjectRoot "scripts\collect_now.py"

# Set working directory and Python path
Set-Location $ProjectRoot
$env:PYTHONPATH = $ProjectRoot

# Run the collection
python $PythonScript

Write-Host "🌐 Refresh your dashboard at http://127.0.0.1:8080" -ForegroundColor Cyan