# Re-enumera el microfono USB DRELANMIC tras el arranque.
# Problema: en arranque en frio el mic USB enumera mal - Windows lo da por OK
# pero el stream entrega silencio. Ciclar el dispositivo (disable/enable) lo arregla,
# igual que desenchufar/enchufar el cable. Lo corre una tarea programada al iniciar sesion.
# Requiere privilegios de admin (la tarea se registra con RunLevel Highest).

$ErrorActionPreference = 'Stop'

# Buscar el dispositivo MEDIA (el USB real, no el AudioEndpoint) por nombre,
# asi sigue funcionando aunque el InstanceId cambie entre reinicios.
$dev = Get-PnpDevice -Class MEDIA -FriendlyName '*DRELANMIC*' -ErrorAction SilentlyContinue | Select-Object -First 1

if (-not $dev) {
    Write-Output "DRELANMIC no encontrado - nada que hacer."
    exit 0
}

try {
    Disable-PnpDevice -InstanceId $dev.InstanceId -Confirm:$false
    Start-Sleep -Seconds 2
    Enable-PnpDevice  -InstanceId $dev.InstanceId -Confirm:$false
    Write-Output "DRELANMIC re-enumerado ($($dev.InstanceId))."
} catch {
    Write-Output "FALLO al ciclar el DRELANMIC: $($_.Exception.Message)"
    exit 1
}
