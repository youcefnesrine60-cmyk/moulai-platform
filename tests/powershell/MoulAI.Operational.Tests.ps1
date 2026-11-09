# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

#Requires -Version 5.1

<#
.SYNOPSIS
Verify local application process ownership and launcher behavior without side effects.
.DESCRIPTION
Run with Pester 3.4. The native entry uses temporary command doubles.
These tests use only temporary PowerShell command doubles. No server, database, native application,
or real process management command is invoked by these tests.
#>

Set-StrictMode -Version Latest

[string]$modulePath = Join-Path $PSScriptRoot '..\..\scripts\MoulAI.Process.psm1'
Import-Module -Name $modulePath -Force -ErrorAction Stop

# ==============================================
# INTEGRATED REVIEW NATIVE BOUNDARY
# Command doubles prove that the default local entry cannot fall back to Uvicorn or silently ignore an unsuccessful host startup.
# ==============================================

InModuleScope 'MoulAI.Process' {
    Describe 'Isolated operational review entry' {
        BeforeEach {
            [string]$script:localProject = (New-Item -ItemType Directory -Path 'TestDrive:\Integrated Review' -Force).FullName
            [string]$script:localCommand = Join-Path $script:localProject 'python-double.ps1'
            Mock Get-MoulaiRuntime {
                [pscustomobject]@{ ProjectPath = $script:localProject; PythonPath = $script:localCommand }
            }
            Mock Test-Path { return $true }
            Mock Start-MoulaiApplication { throw 'Legacy backend is forbidden in this test.' }
            Mock Get-CimInstance { throw 'Process enumeration is unnecessary for the Python lease.' }
            Mock Write-Host { }
            Mock Write-Warning { }
        }

        It 'uses only the isolated serve command and preserves its exit status' {
            [string]$source = @'
$global:moulaiCapturedArguments = @($args)
$global:LASTEXITCODE = 7
'@
            [System.IO.File]::WriteAllText($script:localCommand, $source, (New-Object System.Text.UTF8Encoding($true)))
            [string]$before = (Get-Location).Path
            Start-MoulaiOperationalApplication -ProjectRoot $script:localProject | Should Be 7
            $global:moulaiCapturedArguments.Count | Should Be 5
            $global:moulaiCapturedArguments[0] | Should Be '-I'
            $global:moulaiCapturedArguments[1] | Should Be '-B'
            $global:moulaiCapturedArguments[2] | Should Be (Join-Path $script:localProject 'scripts\run_operational_local.py')
            $global:moulaiCapturedArguments[3] | Should Be 'serve'
            $global:moulaiCapturedArguments[4] | Should Be '--keep-running'
            (Get-Location).Path | Should Be $before
            Assert-MockCalled Start-MoulaiApplication -Times 0 -Exactly -Scope It
            Assert-MockCalled Get-CimInstance -Times 0 -Exactly -Scope It
        }

        It 'does not fall back to the old backend when preparation is missing' {
            Mock Test-Path { return $false }
            { Start-MoulaiOperationalApplication -ProjectRoot $script:localProject } | Should Throw
            Assert-MockCalled Start-MoulaiApplication -Times 0 -Exactly -Scope It
        }

        It 'rejects a stale native exit status and restores the caller location' {
            [System.IO.File]::WriteAllText($script:localCommand, "Write-Output 'No exit status'", (New-Object System.Text.UTF8Encoding($true)))
            [string]$before = (Get-Location).Path
            [string]$originalPreference = $ErrorActionPreference
            $global:LASTEXITCODE = 0
            { Start-MoulaiOperationalApplication -ProjectRoot $script:localProject } | Should Throw
            (Get-Location).Path | Should Be $before
            $ErrorActionPreference | Should Be $originalPreference
        }
    }
}
