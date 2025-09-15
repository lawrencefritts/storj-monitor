# PowerShell script to set up Storj Monitor as a Windows scheduled task
# This version uses a batch file for better service management

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
$BatchScript = Join-Path $ProjectPath "run-background.bat"
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

# Create the action (what the task will do) - Use cmd.exe to run batch file
$Action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$BatchScript`"" -WorkingDirectory $ProjectPath

# Create the trigger (when the task will run)
$Trigger = New-ScheduledTaskTrigger -AtStartup

# Create the settings for long-running process
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 0) -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1)

# Create the principal (run as current user, but hidden)
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType ServiceAccount -RunLevel Highest

# Register the scheduled task
try {
    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Description $Description
    Write-Host "Successfully created scheduled task: $TaskName" -ForegroundColor Green
    
    # Start the task immediately
    Start-ScheduledTask -TaskName $TaskName
    Write-Host "Started the Storj Monitor Dashboard service." -ForegroundColor Green
    Write-Host ""
    Write-Host "Dashboard should be available at: http://localhost:8080" -ForegroundColor Cyan
    Write-Host "Logs will be written to: $LogPath\service.log" -ForegroundColor White
    Write-Host ""
    Write-Host "To manage the service:" -ForegroundColor Yellow
    Write-Host "  Stop:    Stop-ScheduledTask -TaskName '$TaskName'" -ForegroundColor White
    Write-Host "  Start:   Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor White
    Write-Host "  Remove:  Unregister-ScheduledTask -TaskName '$TaskName'" -ForegroundColor White
    Write-Host "  Status:  Get-ScheduledTask -TaskName '$TaskName'" -ForegroundColor White
    Write-Host "  Logs:    Get-Content '$LogPath\service.log' -Tail 20" -ForegroundColor White
    
} catch {
    Write-Host "Failed to create scheduled task: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Setup complete! The service should start automatically on boot and restart if it crashes." -ForegroundColor Green
Write-Host "Give it about 30 seconds to fully start, then check http://localhost:8080" -ForegroundColor Cyan