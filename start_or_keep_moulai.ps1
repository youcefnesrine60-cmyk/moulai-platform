# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

#Requires -Version 5.1

<#
.SYNOPSIS
    Keep this project's existing MoulAI server or start it in the foreground.
.DESCRIPTION
    Match the project virtualenv and canonical Uvicorn arguments. Servers from
    other projects do not prevent startup. Return the server's actual exit code.
.EXAMPLE
    .\start_or_keep_moulai.ps1
#>
[CmdletBinding(PositionalBinding = $false)]
param ()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ==============================================
# LOAD THE SHARED RUNTIME AND KEEP OR START THE SERVER
# ==============================================

try {
    [string]$modulePath = Join-Path -Path $PSScriptRoot -ChildPath 'scripts\MoulAI.Process.psm1'
    Import-Module -Name $modulePath -Force -ErrorAction Stop
    [int]$exitCode = Start-MoulaiApplication -ProjectRoot $PSScriptRoot -KeepRunning
    exit $exitCode
}
catch {
    Write-Error -ErrorRecord $_ -ErrorAction Continue
    exit 1
}
