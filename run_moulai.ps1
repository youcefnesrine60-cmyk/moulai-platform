# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

#Requires -Version 5.1

<#
.SYNOPSIS
    Start MoulAI in the foreground using this project's virtualenv.
.DESCRIPTION
    Resolve paths from the script directory and return Uvicorn's exit code.
    Application startup validates its configured database without migrations.
.EXAMPLE
    .\run_moulai.ps1
#>
[CmdletBinding(PositionalBinding = $false)]
param ()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ==============================================
# LOAD THE SHARED RUNTIME AND START THE APPLICATION
# ==============================================

try {
    [string]$modulePath = Join-Path -Path $PSScriptRoot -ChildPath 'scripts\MoulAI.Process.psm1'
    Import-Module -Name $modulePath -Force -ErrorAction Stop
    [int]$exitCode = Start-MoulaiApplication -ProjectRoot $PSScriptRoot
    exit $exitCode
}
catch {
    Write-Error -ErrorRecord $_ -ErrorAction Continue
    exit 1
}
