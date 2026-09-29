$processes = Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python|uvicorn' -and $_.CommandLine -match 'app.main:app|uvicorn' }

if (-not $processes) {
    Write-Host 'Aucun serveur MoulAI en cours d’exécution.'
    exit 0
}

foreach ($p in $processes) {
    try {
        Stop-Process -Id $p.ProcessId -Force
        Write-Host "Serveur arrêté : PID $($p.ProcessId)"
    } catch {
        Write-Host "Impossible d’arrêter le PID $($p.ProcessId) : $($_.Exception.Message)"
    }
}
