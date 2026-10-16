# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

#Requires -Version 5.1

<#
.SYNOPSIS
    Stop only this project's MoulAI server and its reload children.
.DESCRIPTION
    Recheck process identity before stopping any PID. Forward -WhatIf and
    -Confirm to the shared operation without affecting other Uvicorn projects.
.EXAMPLE
    .\stop_moulai.ps1 -WhatIf
.EXAMPLE
    .\stop_moulai.ps1
#>
[CmdletBinding(PositionalBinding = $false, SupportsShouldProcess = $true, ConfirmImpact = 'Medium')]
param ()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ==============================================
# LOAD THE SHARED RUNTIME AND STOP VERIFIED PROCESSES
# ==============================================

try {
    [string]$modulePath = Join-Path -Path $PSScriptRoot -ChildPath 'scripts\MoulAI.Process.psm1'
    Import-Module -Name $modulePath -Force -ErrorAction Stop
    [hashtable]$operationParameters = @{ ProjectRoot = $PSScriptRoot }
    foreach ($parameterName in @('WhatIf', 'Confirm')) {
        if ($PSBoundParameters.ContainsKey($parameterName)) {
            $operationParameters[$parameterName] = $PSBoundParameters[$parameterName]
        }
    }
    [int]$exitCode = Stop-MoulaiApplication @operationParameters
    exit $exitCode
}
catch {
    Write-Error -ErrorRecord $_ -ErrorAction Continue
    exit 1
}
