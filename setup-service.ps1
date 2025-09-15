# PowerShell script to set up Storj Monitor as a Windows scheduled task
# This will make it start automatically on boot and restart if it crashes

param(
    [string]$TaskName = "StorjMonitorDashboard",
    [string]$Description = "Storj Node Monitor Dashboard - FastAPI Web Server"
)

# Check if running as Administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "This script requires Administrator privileges. Please run PowerShell as Administrator." -ForegroundColor Red
    exit 1
}

# Project paths
$ProjectPath = "C:\Users\lawre\py_projs\storj-monitor"
$PythonScript = Join-Path $ProjectPath "main.py"
$LogPath = Join-Path $ProjectPath "logs"

# Ensure log directory exists
if (!(Test-Path $LogPath)) {
    New-Item -ItemType Directory -Path $LogPath -Force
}

Write-Host "Setting up Storj Monitor Dashboard as a Windows service..." -ForegroundColor Green

# Remove existing task if it exists
try {
    $existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existingTask) {
        Write-Host "Removing existing scheduled task..." -ForegroundColor Yellow
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }
} catch {
    # Task doesn't exist, continue
}

# Create the action (what the task will do)
$Action = New-ScheduledTaskAction -Execute "python.exe" -Argument "`"$PythonScript`"" -WorkingDirectory $ProjectPath

# Create the trigger (when the task will run)
$Trigger = New-ScheduledTaskTrigger -AtStartup

# Create the settings
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

# Create the principal (run as current user)
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest

# Register the scheduled task
try {
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Description $Description
    Write-Host "Successfully created scheduled task: $TaskName" -ForegroundColor Green
    
    # Start the task immediately
    Start-ScheduledTask -TaskName $TaskName
    Write-Host "Started the Storj Monitor Dashboard service." -ForegroundColor Green
    Write-Host ""
    Write-Host "Dashboard will be available at: http://localhost:8080" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "To manage the service:" -ForegroundColor Yellow
    Write-Host "  Stop:    Stop-ScheduledTask -TaskName '$TaskName'" -ForegroundColor White
    Write-Host "  Start:   Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor White
    Write-Host "  Remove:  Unregister-ScheduledTask -TaskName '$TaskName'" -ForegroundColor White
    Write-Host "  Status:  Get-ScheduledTask -TaskName '$TaskName'" -ForegroundColor White
    
} catch {
    Write-Host "Failed to create scheduled task: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Wait a few seconds and check if the service is running
Write-Host ""
Write-Host "Checking if the service started successfully..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

try {
    $response = Invoke-WebRequest -Uri "http://localhost:8080/health" -TimeoutSec 10
    if ($response.StatusCode -eq 200) {
        Write-Host "SUCCESS: Storj Monitor Dashboard is running!" -ForegroundColor Green
        Write-Host "  Access the dashboard at: http://localhost:8080" -ForegroundColor Cyan
    }
} catch {
    Write-Host "WARNING: Dashboard may still be starting up. Check the logs if it doesn't become available soon." -ForegroundColor Yellow
    Write-Host "  Log location: $LogPath" -ForegroundColor White
}

Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green