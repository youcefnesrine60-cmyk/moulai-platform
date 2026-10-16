# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

#Requires -Version 5.1

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ==============================================
# RESOLVE THE PROJECT RUNTIME
# ==============================================

function Get-MoulaiRuntime {
    <#
    .SYNOPSIS
        Resolve project paths without changing the caller's working directory.
    #>
    [CmdletBinding(PositionalBinding = $false)]
    [OutputType([pscustomobject])]
    param (
        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string]$ProjectRoot
    )

    if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
        throw 'Le dossier du projet MoulAI est introuvable.'
    }

    [string]$projectPath = (Resolve-Path -LiteralPath $ProjectRoot).ProviderPath
    return [pscustomobject]@{
        ProjectPath = $projectPath
        PythonPath = Join-Path -Path $projectPath -ChildPath '.venv\Scripts\python.exe'
        Application = 'app.main:app'
    }
}

# ==============================================
# IDENTIFY SERVERS OWNED BY THIS PROJECT
# ==============================================

function Get-MoulaiServerRoots {
    <#
    .SYNOPSIS
        Match the project's Python runtime and canonical Uvicorn arguments.
    .DESCRIPTION
        Windows virtualenv redirectors can expose the base executable path.
        Accept the exact invocation path or the exact virtualenv executable.
        Missing identity data and other projects fail closed.
    #>
    [CmdletBinding(PositionalBinding = $false)]
    [OutputType([psobject])]
    param (
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [object[]]$ProcessInventory,

        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string]$PythonPath
    )

    foreach ($process in $ProcessInventory) {
        if (
            $process.ProcessId -le 0 -or
            $process.ProcessId -eq $PID -or
            $null -eq $process.CreationDate -or
            [string]::IsNullOrWhiteSpace([string]$process.CommandLine)
        ) {
            continue
        }

        [string[]]$arguments = @(
            [regex]::Matches([string]$process.CommandLine, '(?:[^\s"]|"[^"]*")+') |
                ForEach-Object { $_.Value.Trim('"') }
        )
        if ($arguments.Count -lt 4) {
            continue
        }

        [bool]$ownedInvocation = [string]::Equals(
            $arguments[0], $PythonPath, [System.StringComparison]::OrdinalIgnoreCase
        )
        [bool]$ownedExecutable = [string]::Equals(
            [string]$process.ExecutablePath,
            $PythonPath,
            [System.StringComparison]::OrdinalIgnoreCase
        )
        [bool]$relativeInvocation = -not [System.IO.Path]::IsPathRooted($arguments[0])
        if (
            ($ownedInvocation -or ($ownedExecutable -and $relativeInvocation)) -and
            $arguments[1] -ceq '-m' -and
            $arguments[2] -ceq 'uvicorn' -and
            $arguments[3] -ceq 'app.main:app'
        ) {
            Write-Output -InputObject $process
        }
    }
}

# ==============================================
# TRACK RELOAD CHILDREN WITHOUT CROSSING PROJECTS
# ==============================================

function Get-MoulaiProcessTree {
    <#
    .SYNOPSIS
        Return owned roots and descendants in child-first shutdown order.
    .DESCRIPTION
        Reject older orphan processes whose parent PID has been reused.
        Track visited IDs to avoid duplicate shutdown attempts and cycles.
    #>
    [CmdletBinding(PositionalBinding = $false)]
    [OutputType([pscustomobject])]
    param (
        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [object[]]$Roots,

        [Parameter(Mandatory = $true)]
        [AllowEmptyCollection()]
        [object[]]$ProcessInventory
    )

    $pending = New-Object 'System.Collections.Generic.Stack[object]'
    $visited = New-Object 'System.Collections.Generic.HashSet[int]'
    $processTree = New-Object 'System.Collections.Generic.List[object]'
    foreach ($root in $Roots) {
        $pending.Push([pscustomobject]@{
            Process = $root
            Depth = 0
            Expanded = $false
        })
    }

    while ($pending.Count -gt 0) {
        $node = $pending.Pop()
        if ($node.Expanded) {
            $processTree.Add($node)
            continue
        }

        [int]$processId = $node.Process.ProcessId
        if ($processId -le 0 -or $processId -eq $PID -or -not $visited.Add($processId)) {
            continue
        }

        # Postorder keeps children ahead of parents even when the supplied
        # root set contains both a parent server and its nested server.
        $pending.Push([pscustomobject]@{
            Process = $node.Process
            Depth = $node.Depth
            Expanded = $true
        })
        foreach ($child in $ProcessInventory) {
            if (
                $child.ParentProcessId -eq $processId -and
                $null -ne $child.CreationDate -and
                $child.CreationDate -ge $node.Process.CreationDate
            ) {
                $pending.Push([pscustomobject]@{
                    Process = $child
                    Depth = $node.Depth + 1
                    Expanded = $false
                })
            }
        }
    }

    $processTree
}

# ==============================================
# RUN UVICORN IN THE FOREGROUND
# ==============================================

function Invoke-MoulaiPythonServer {
    <#
    .SYNOPSIS
        Preserve native output and the actual exit code of the Python server.
    .DESCRIPTION
        Native stderr contains normal Uvicorn logging. Handle failure by its
        exit code instead of treating every stderr message as a PowerShell error.
    #>
    [CmdletBinding(PositionalBinding = $false)]
    [OutputType([int])]
    param (
        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string]$PythonPath,

        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string]$Application
    )

    [string]$previousErrorAction = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        # LASTEXITCODE is PowerShell's global native-command status. Do not
        # shadow it with a local variable or retain a previous command's result.
        $global:LASTEXITCODE = $null
        & $PythonPath -m uvicorn $Application --reload | Out-Host
        if ($null -eq $global:LASTEXITCODE) {
            throw 'Impossible de déterminer le code de sortie du serveur MoulAI.'
        }
        return [int]$global:LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorAction
    }
}

# ==============================================
# START THE SERVER OR KEEP ITS EXISTING INSTANCE
# ==============================================

function Start-MoulaiApplication {
    <#
    .SYNOPSIS
        Launch MoulAI using its virtualenv and restore the caller's location.
    .PARAMETER KeepRunning
        Return successfully when this project's Uvicorn server already exists.
    #>
    [CmdletBinding(PositionalBinding = $false)]
    [OutputType([int])]
    param (
        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string]$ProjectRoot,

        [switch]$KeepRunning
    )

    $runtime = Get-MoulaiRuntime -ProjectRoot $ProjectRoot
    if (-not (Test-Path -LiteralPath $runtime.PythonPath -PathType Leaf)) {
        throw 'Python est introuvable dans le virtualenv du projet MoulAI.'
    }

    if ($KeepRunning) {
        [object[]]$inventory = @(Get-CimInstance -ClassName Win32_Process)
        [object[]]$running = @(Get-MoulaiServerRoots -ProcessInventory $inventory -PythonPath $runtime.PythonPath)
        if ($running.Count -gt 0) {
            [string]$processIds = ($running | ForEach-Object { $_.ProcessId }) -join ', '
            Write-Host "MoulAI est déjà en cours d'exécution. PID(s) : $processIds"
            return 0
        }
    }

    Push-Location -LiteralPath $runtime.ProjectPath
    try {
        Write-Host 'Démarrage du serveur MoulAI.'
        [int]$exitCode = Invoke-MoulaiPythonServer -PythonPath $runtime.PythonPath -Application $runtime.Application
        if ($exitCode -ne 0) {
            Write-Warning "Le serveur MoulAI s'est terminé avec le code $exitCode."
        }
        return $exitCode
    }
    finally {
        Pop-Location
    }
}

# ==============================================
# STOP ONLY THE VERIFIED PROJECT PROCESS TREE
# ==============================================

function Stop-MoulaiApplication {
    <#
    .SYNOPSIS
        Stop this project's Uvicorn server and its reload children.
    .DESCRIPTION
        Recheck each PID's creation time before stopping it. A missing process
        is already stopped; a reused PID is refused and reported as a failure.
        Supports -WhatIf and -Confirm through standard PowerShell semantics.
    #>
    [CmdletBinding(PositionalBinding = $false, SupportsShouldProcess = $true, ConfirmImpact = 'Medium')]
    [OutputType([int])]
    param (
        [Parameter(Mandatory = $true)]
        [ValidateNotNullOrEmpty()]
        [string]$ProjectRoot
    )

    $runtime = Get-MoulaiRuntime -ProjectRoot $ProjectRoot
    [object[]]$inventory = @(Get-CimInstance -ClassName Win32_Process)
    [object[]]$roots = @(Get-MoulaiServerRoots -ProcessInventory $inventory -PythonPath $runtime.PythonPath)
    if ($roots.Count -eq 0) {
        Write-Host "Aucun serveur MoulAI en cours d'exécution."
        return 0
    }

    [int]$exitCode = 0
    [object[]]$ownedProcesses = @(Get-MoulaiProcessTree -Roots $roots -ProcessInventory $inventory)
    foreach ($node in $ownedProcesses) {
        [int]$processId = $node.Process.ProcessId
        if (-not $PSCmdlet.ShouldProcess("MoulAI PID $processId", 'Stop process')) {
            continue
        }

        try {
            [object[]]$current = @(Get-CimInstance -ClassName Win32_Process -Filter "ProcessId = $processId")
            if ($current.Count -eq 0) {
                continue
            }
            if (
                $current.Count -ne 1 -or
                $current[0].ProcessId -ne $processId -or
                $current[0].CreationDate -ne $node.Process.CreationDate
            ) {
                $exitCode = 1
                Write-Warning "Arrêt refusé : le PID $processId ne correspond plus au processus identifié."
                continue
            }

            Stop-Process -Id $processId -Force -ErrorAction Stop
            Write-Host "Serveur arrêté : PID $processId"
        }
        catch {
            $exitCode = 1
            Write-Warning "Impossible d'arrêter le PID $processId : $($_.Exception.Message)"
        }
    }
    return $exitCode
}

# ==============================================
# PUBLIC OPERATION CONTRACT
# ==============================================

Export-ModuleMember -Function @(
    'Get-MoulaiRuntime',
    'Start-MoulaiApplication',
    'Stop-MoulaiApplication'
)
