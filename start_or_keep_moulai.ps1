# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

#Requires -Version 5.1

<#
.SYNOPSIS
    Keep or start the isolated integrated MoulAI review in the foreground.
.DESCRIPTION
    Default to the prepared local instance, without reading the legacy backend
    database target. LegacyBackend explicitly selects the historical launcher;
    its schema validation remains mandatory and no migration is automatic.
.EXAMPLE
    .\start_or_keep_moulai.ps1
#>
[CmdletBinding(PositionalBinding = $false)]
param (
    [switch]$LegacyBackend
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ==============================================
# LOAD THE SHARED RUNTIME AND KEEP OR START THE SERVER
# ==============================================

try {
    [string]$modulePath = Join-Path -Path $PSScriptRoot -ChildPath 'scripts\MoulAI.Process.psm1'
    Import-Module -Name $modulePath -Force -ErrorAction Stop
    [int]$exitCode = if ($LegacyBackend) {
        Start-MoulaiApplication -ProjectRoot $PSScriptRoot -KeepRunning
    }
    else {
        Start-MoulaiOperationalApplication -ProjectRoot $PSScriptRoot
    }
    exit $exitCode
}
catch {
    Write-Error -ErrorRecord $_ -ErrorAction Continue
    exit 1
}
