# Registers the portal as a scheduled task so it runs without a console window
# and comes back by itself after a reboot.
#
#   powershell -ExecutionPolicy Bypass -File install_tasks.ps1
#   powershell -ExecutionPolicy Bypass -File install_tasks.ps1 -Remove
#
# -AtLogOn needs -User or Task Scheduler demands an admin prompt, which is why
# the trigger below names the current user explicitly.

param([switch]$Remove)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$taskName = 'InternRadar-Portal'
$python = Join-Path $PSScriptRoot '.venv\Scripts\pythonw.exe'   # pythonw: no console
if (-not (Test-Path $python)) {
    $python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
}
if (-not (Test-Path $python)) {
    throw "No virtual environment found. Run setup.ps1 first."
}

if ($Remove) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed $taskName."
    return
}

$me = "$env:USERDOMAIN\$env:USERNAME"
$action = New-ScheduledTaskAction -Execute $python -Argument 'app.py' -WorkingDirectory $PSScriptRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $me
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5) `
    -ExecutionTimeLimit (New-TimeSpan -Days 0)

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
    -Settings $settings -Description 'InternRadar portal: website, scraper and digest mailer' `
    -Force | Out-Null

Write-Host "Registered $taskName - the portal starts at logon."
Write-Host "Start it now with:  Start-ScheduledTask -TaskName $taskName"
Write-Host "Then open http://127.0.0.1:8700"
Write-Host ""
Write-Host "The scraper and the mailer live inside that one process, so there is"
Write-Host "nothing else to schedule. Logs: Get-ScheduledTaskInfo -TaskName $taskName"
