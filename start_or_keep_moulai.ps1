$projectPath = "D:\MoulAI"
$pythonExe = Join-Path $projectPath ".venv\Scripts\python.exe"
$serverCommand = "app.main:app"

if (-not (Test-Path $pythonExe)) {
    Write-Error "Python venv introuvable : $pythonExe"
    exit 1
}

$running = Get-CimInstance Win32_Process |
    Where-Object {
        $_.CommandLine -match 'uvicorn' -and $_.CommandLine -match 'app.main:app'
    }

if ($running) {
    Write-Host "MoulAI est déjà en cours d’exécution."
    Write-Host "PID(s) : $($running | ForEach-Object { $_.ProcessId } -join ', ')"
    exit 0
}

Set-Location $projectPath
& $pythonExe -m uvicorn $serverCommand --reload
