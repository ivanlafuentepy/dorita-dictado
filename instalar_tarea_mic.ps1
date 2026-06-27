# Instalador (una sola vez) de la tarea que re-enumera el mic DRELANMIC al iniciar sesion.
# Se auto-eleva: al correrlo aparece el prompt de UAC -> aceptalo.
# Como correrlo: click derecho sobre este archivo -> "Ejecutar con PowerShell".

$ErrorActionPreference = 'Stop'

# Auto-elevacion a administrador
$id = [Security.Principal.WindowsIdentity]::GetCurrent()
$pr = New-Object Security.Principal.WindowsPrincipal($id)
if (-not $pr.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Start-Process powershell.exe "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

$action    = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument '-NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "C:\Users\Ivan\Projects\dorita-dictado\reenumerar_mic.ps1"'
$trigger   = New-ScheduledTaskTrigger -AtLogOn -User 'Ivan'
$principal = New-ScheduledTaskPrincipal -UserId 'Ivan' -LogonType Interactive -RunLevel Highest
$settings  = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 2)

Register-ScheduledTask -TaskName 'DoritaDictado-ReenumerarMic' -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null

Write-Host ""
Write-Host "OK - Tarea 'DoritaDictado-ReenumerarMic' registrada." -ForegroundColor Green
Write-Host "A partir del proximo reinicio, el mic se re-enumera solo al iniciar sesion."
Write-Host "Ya podes cerrar esta ventana."
Start-Sleep -Seconds 5
