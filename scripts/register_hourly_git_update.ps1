param(
    [string]$TaskName = "PULSEAI-Hourly-Git-Update",
    [string]$RepoPath = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$Branch = "main"
)

$ErrorActionPreference = "Stop"

$scriptPath = Join-Path $PSScriptRoot "hourly_git_update.ps1"
if (-not (Test-Path $scriptPath)) {
    throw "Missing script: $scriptPath"
}

$arg = "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`" -RepoPath `"$RepoPath`" -Branch `"$Branch`""
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $arg

$startAt = (Get-Date).AddMinutes(2)
$trigger = New-ScheduledTaskTrigger -Once -At $startAt -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Description "Auto-commit and push PulseAI changes every hour" -Force | Out-Null

Write-Output "Scheduled task '$TaskName' created."
Write-Output "First run at: $startAt"
