# Storj Monitor Collector Service Management Scripts

# Configuration
$TaskName = "StorjMonitorCollector"
$ScriptPath = (Get-Location).Path
$PythonPath = Join-Path $ScriptPath "venv\Scripts\python.exe"
$CollectorPath = Join-Path $ScriptPath "collector\service.py"
$LogPath = Join-Path $ScriptPath "logs\collector_task.log"

# Ensure logs directory exists
$LogDir = Split-Path $LogPath -Parent
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
}

# Function to install collector as scheduled task
function Install-Collector {
    Write-Host "Installing Storj Monitor Collector as scheduled task..." -ForegroundColor Green
    
    # Check if task already exists
    $existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existingTask) {
        Write-Host "Task already exists. Removing old task..." -ForegroundColor Yellow
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }
    
    # Create action
    $action = New-ScheduledTaskAction -Execute $PythonPath -Argument $CollectorPath -WorkingDirectory $ScriptPath
    
    # Create trigger (start at boot and restart if stopped)
    $trigger = New-ScheduledTaskTrigger -AtStartup
    
    # Create settings
    $settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5)
    $settings.ExecutionTimeLimit = "PT0S"  # No time limit
    $settings.DisallowStartIfOnBatteries = $false
    $settings.StopIfGoingOnBatteries = $false
    
    # Create principal (run as SYSTEM or current user)
    $principal = New-ScheduledTaskPrincipal -UserId "NT AUTHORITY\SYSTEM" -LogonType ServiceAccount -RunLevel Highest
    
    # Register the task
    try {
        Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Storj Monitor Data Collector Service" | Out-Null
        Write-Host "Successfully installed collector as scheduled task '$TaskName'" -ForegroundColor Green
        Write-Host "The collector will start automatically at boot and restart if it fails" -ForegroundColor Cyan
    } catch {
        Write-Error "Failed to register scheduled task: $_"
    }
}

# Function to uninstall collector
function Uninstall-Collector {
    Write-Host "Uninstalling Storj Monitor Collector..." -ForegroundColor Yellow
    
    $existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existingTask) {
        Stop-Collector
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "Successfully uninstalled collector scheduled task" -ForegroundColor Green
    } else {
        Write-Host "Collector task not found" -ForegroundColor Yellow
    }
}

# Function to start collector
function Start-Collector {
    Write-Host "Starting Storj Monitor Collector..." -ForegroundColor Green
    
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if (-not $task) {
        Write-Error "Collector task not found. Run Install-Collector first."
        return
    }
    
    try {
        Start-ScheduledTask -TaskName $TaskName
        Start-Sleep 2
        $taskState = (Get-ScheduledTask -TaskName $TaskName).State
        if ($taskState -eq "Running") {
            Write-Host "Collector started successfully" -ForegroundColor Green
        } else {
            Write-Warning "Collector may not have started properly. State: $taskState"
        }
    } catch {
        Write-Error "Failed to start collector: $_"
    }
}

# Function to stop collector
function Stop-Collector {
    Write-Host "Stopping Storj Monitor Collector..." -ForegroundColor Yellow
    
    try {
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        
        # Also kill any running Python processes for the collector
        $processes = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*$ScriptPath*" }
        if ($processes) {
            $processes | ForEach-Object {
                Write-Host "Terminating collector process (PID: $($_.Id))" -ForegroundColor Yellow
                Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
            }
        }
        
        Write-Host "Collector stopped" -ForegroundColor Green
    } catch {
        Write-Error "Failed to stop collector: $_"
    }
}

# Function to check collector status
function Get-CollectorStatus {
    Write-Host "Checking Storj Monitor Collector status..." -ForegroundColor Blue
    
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if (-not $task) {
        Write-Host "Status: NOT INSTALLED" -ForegroundColor Red
        return
    }
    
    $taskState = $task.State
    $lastRun = (Get-ScheduledTaskInfo -TaskName $TaskName).LastRunTime
    $nextRun = (Get-ScheduledTaskInfo -TaskName $TaskName).NextRunTime
    $lastResult = (Get-ScheduledTaskInfo -TaskName $TaskName).LastTaskResult
    
    Write-Host "Task State: $taskState" -ForegroundColor $(if ($taskState -eq "Running") { "Green" } elseif ($taskState -eq "Ready") { "Yellow" } else { "Red" })
    Write-Host "Last Run: $lastRun" -ForegroundColor Gray
    Write-Host "Next Run: $nextRun" -ForegroundColor Gray
    Write-Host "Last Result: $lastResult" -ForegroundColor $(if ($lastResult -eq 0) { "Green" } else { "Red" })
    
    # Check for running processes
    $processes = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*collector*service.py*" }
    if ($processes) {
        Write-Host "Running Processes:" -ForegroundColor Blue
        $processes | ForEach-Object {
            Write-Host "  PID: $($_.Id), Started: $($_.StartTime)" -ForegroundColor Gray
        }
    } else {
        Write-Host "No collector processes found" -ForegroundColor Gray
    }
}

# Function to view collector logs
function Show-CollectorLogs {
    param(
        [int]$Lines = 50
    )
    
    $logFiles = @(
        (Join-Path $ScriptPath "logs\collector.log"),
        (Join-Path $ScriptPath "logs\storj_monitor.log")
    )
    
    foreach ($logFile in $logFiles) {
        if (Test-Path $logFile) {
            Write-Host "`nLast $Lines lines from ${logFile}:" -ForegroundColor Blue
            Get-Content $logFile -Tail $Lines | Write-Host
        }
    }
}

# Export functions for use in separate scripts
Export-ModuleMember -Function Install-Collector, Uninstall-Collector, Start-Collector, Stop-Collector, Get-CollectorStatus, Show-CollectorLogs

# If script is run directly, show usage
if ($MyInvocation.InvocationName -eq $MyInvocation.MyCommand.Name) {
    Write-Host "Storj Monitor Collector Management" -ForegroundColor Cyan
    Write-Host "Available functions:" -ForegroundColor White
    Write-Host "  Install-Collector    - Install collector as Windows scheduled task" -ForegroundColor Green
    Write-Host "  Uninstall-Collector  - Remove collector scheduled task" -ForegroundColor Yellow
    Write-Host "  Start-Collector      - Start the collector service" -ForegroundColor Green
    Write-Host "  Stop-Collector       - Stop the collector service" -ForegroundColor Yellow
    Write-Host "  Get-CollectorStatus  - Check collector status" -ForegroundColor Blue
    Write-Host "  Show-CollectorLogs   - View recent log entries" -ForegroundColor Blue
    Write-Host "`nExample usage:" -ForegroundColor White
    Write-Host "  . .\scripts\collector_scripts.ps1; Install-Collector" -ForegroundColor Gray
}