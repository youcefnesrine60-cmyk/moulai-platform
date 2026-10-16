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
Run with Pester 3.4. Process inventory and termination are mocked.
The launcher uses a mocked Python boundary; boundary-specific tests use only
temporary PowerShell command doubles. No server, database, native application,
or real process management command is invoked by these tests.
#>

Set-StrictMode -Version Latest

[string]$modulePath = Join-Path $PSScriptRoot '..\..\scripts\MoulAI.Process.psm1'
Import-Module -Name $modulePath -Force -ErrorAction Stop

InModuleScope 'MoulAI.Process' {
    # ==============================================
    # PROCESS FIXTURES
    # ==============================================

    function New-MoulaiTestProcess {
        <#
        .SYNOPSIS
            Build an explicit process inventory record for isolated ownership tests.
        #>
        [CmdletBinding()]
        [OutputType([pscustomobject])]
        param (
            [Parameter(Mandatory = $true)]
            [int]$ProcessIdentifier,

            [int]$ParentIdentifier = 0,

            [string]$CommandLine = '',

            [string]$ExecutablePath = '',

            [datetime]$CreationDate = [datetime] '2026-10-15T08:00:00Z'
        )

        return [pscustomobject]@{
            ProcessId = $ProcessIdentifier
            ParentProcessId = $ParentIdentifier
            CommandLine = $CommandLine
            ExecutablePath = $ExecutablePath
            CreationDate = $CreationDate
            Name = 'python.exe'
        }
    }

    # ==============================================
    # EXACT PROJECT PROCESS OWNERSHIP
    # ==============================================

    Describe 'MoulAI application process ownership' {
        BeforeEach {
            [string]$script:testPythonPath = 'C:\MoulAI Test\.venv\Scripts\python.exe'
            Mock Get-CimInstance { throw 'Real process inventory is forbidden in this test.' }
            Mock Stop-Process { throw 'Real process termination is forbidden in this test.' }
            Mock Invoke-MoulaiPythonServer { throw 'Real Python invocation is forbidden in this test.' }
        }

        It 'recognizes a quoted project Python path regardless of case' {
            [object]$owned = New-MoulaiTestProcess -ProcessIdentifier 88001 `
                -CommandLine ('"{0}" -m uvicorn app.main:app --reload' -f $script:testPythonPath.ToUpperInvariant())

            [object[]]$roots = @(Get-MoulaiServerRoots -ProcessInventory @($owned) -PythonPath $script:testPythonPath)

            $roots.Count | Should Be 1
            $roots[0].ProcessId | Should Be 88001
        }

        It 'uses the verified executable path when Python was invoked relatively' {
            [object]$owned = New-MoulaiTestProcess -ProcessIdentifier 88001 `
                -CommandLine 'python.exe -m uvicorn app.main:app --reload' `
                -ExecutablePath $script:testPythonPath

            @(Get-MoulaiServerRoots -ProcessInventory @($owned) -PythonPath $script:testPythonPath).Count | Should Be 1
        }

        It 'recognizes an unquoted project interpreter path without spaces' {
            [string]$pythonPath = 'C:\MoulAI\.venv\Scripts\python.exe'
            [object]$owned = New-MoulaiTestProcess -ProcessIdentifier 88001 `
                -CommandLine ('{0} -m uvicorn app.main:app --reload' -f $pythonPath)

            @(Get-MoulaiServerRoots -ProcessInventory @($owned) -PythonPath $pythonPath).Count | Should Be 1
        }

        It 'rejects another project and similar application names' {
            [object[]]$inventory = @(
                (New-MoulaiTestProcess -ProcessIdentifier 88001 -CommandLine 'C:\Other\.venv\Scripts\python.exe -m uvicorn app.main:app --reload'),
                (New-MoulaiTestProcess -ProcessIdentifier 88002 -CommandLine ('"{0}" -m uvicorn app.main:application' -f $script:testPythonPath)),
                (New-MoulaiTestProcess -ProcessIdentifier 88003 -CommandLine ('"{0}" -m uvicorn app.other:app' -f $script:testPythonPath)),
                (New-MoulaiTestProcess -ProcessIdentifier 88004 -CommandLine ('"{0}" -c "print(''uvicorn app.main:app'')"' -f $script:testPythonPath)),
                (New-MoulaiTestProcess -ProcessIdentifier 88005 -CommandLine '')
            )

            @(Get-MoulaiServerRoots -ProcessInventory $inventory -PythonPath $script:testPythonPath).Count | Should Be 0
        }

        It 'does not trust a relative Python command without its executable identity' {
            [object]$unverified = New-MoulaiTestProcess -ProcessIdentifier 88001 `
                -CommandLine 'python.exe -m uvicorn app.main:app --reload'

            @(Get-MoulaiServerRoots -ProcessInventory @($unverified) -PythonPath $script:testPythonPath).Count | Should Be 0
        }

        It 'rejects a conflicting absolute invocation even when the executable path matches' {
            [object]$conflicting = New-MoulaiTestProcess -ProcessIdentifier 88001 `
                -CommandLine 'C:\Other\.venv\Scripts\python.exe -m uvicorn app.main:app --reload' `
                -ExecutablePath $script:testPythonPath

            @(Get-MoulaiServerRoots -ProcessInventory @($conflicting) -PythonPath $script:testPythonPath).Count | Should Be 0
        }

        It 'orders reload descendants before their server parent' {
            [object]$root = New-MoulaiTestProcess -ProcessIdentifier 88001
            [object]$child = New-MoulaiTestProcess -ProcessIdentifier 88002 -ParentIdentifier 88001 `
                -CreationDate ([datetime] '2026-10-15T08:01:00Z')
            [object]$grandchild = New-MoulaiTestProcess -ProcessIdentifier 88003 -ParentIdentifier 88002 `
                -CreationDate ([datetime] '2026-10-15T08:02:00Z')
            [object]$foreign = New-MoulaiTestProcess -ProcessIdentifier 88004 -ParentIdentifier 120

            [object[]]$tree = @(Get-MoulaiProcessTree -Roots @($root) -ProcessInventory @($root, $child, $grandchild, $foreign))

            ($tree | ForEach-Object { $_.Process.ProcessId }) -join ',' | Should Be '88003,88002,88001'
        }

        It 'rejects stale parent links and never targets the calling shell or PID zero' {
            [object]$root = New-MoulaiTestProcess -ProcessIdentifier 88001
            [object[]]$inventory = @(
                $root,
                (New-MoulaiTestProcess -ProcessIdentifier 88002 -ParentIdentifier 88001 -CreationDate ([datetime] '2026-10-15T07:00:00Z')),
                (New-MoulaiTestProcess -ProcessIdentifier $PID -ParentIdentifier 88001),
                (New-MoulaiTestProcess -ProcessIdentifier 0 -ParentIdentifier 88001)
            )

            [object[]]$tree = @(Get-MoulaiProcessTree -Roots @($root) -ProcessInventory $inventory)

            $tree.Count | Should Be 1
            $tree[0].Process.ProcessId | Should Be 88001
        }

        It 'includes a process only once when roots overlap' {
            [object]$root = New-MoulaiTestProcess -ProcessIdentifier 88001
            [object]$child = New-MoulaiTestProcess -ProcessIdentifier 88002 -ParentIdentifier 88001

            [object[]]$tree = @(Get-MoulaiProcessTree -Roots @($root, $child, $root) -ProcessInventory @($root, $child))

            $tree.Count | Should Be 2
            @($tree | ForEach-Object { $_.Process.ProcessId } | Select-Object -Unique).Count | Should Be 2
            ($tree | ForEach-Object { $_.Process.ProcessId }) -join ',' | Should Be '88002,88001'
        }

        It 'terminates traversal when malformed process inventory contains a cycle' {
            [object]$root = New-MoulaiTestProcess -ProcessIdentifier 88001 -ParentIdentifier 88002
            [object]$child = New-MoulaiTestProcess -ProcessIdentifier 88002 -ParentIdentifier 88001

            [object[]]$tree = @(Get-MoulaiProcessTree -Roots @($root) -ProcessInventory @($root, $child))

            $tree.Count | Should Be 2
            ($tree | ForEach-Object { $_.Process.ProcessId }) -join ',' | Should Be '88002,88001'
        }
    }

    # ==============================================
    # LAUNCHER AND STOP OPERATION BOUNDARIES
    # ==============================================

    Describe 'MoulAI launcher and stop operations' {
        BeforeEach {
            [string]$script:operationProjectPath = (New-Item -ItemType Directory -Path 'TestDrive:\Application With Spaces' -Force).FullName
            [string]$script:operationPythonPath = Join-Path $script:operationProjectPath '.venv\Scripts\python.exe'
            [object[]]$script:inventory = @()
            [hashtable]$script:currentProcesses = @{}
            $script:stoppedIdentifiers = New-Object 'System.Collections.Generic.List[int]'
            $script:operationMessages = New-Object 'System.Collections.Generic.List[string]'
            [string]$script:invocationLocation = ''

            Mock Get-MoulaiRuntime {
                return [pscustomobject]@{
                    ProjectPath = $script:operationProjectPath
                    PythonPath = $script:operationPythonPath
                    Application = 'app.main:app'
                }
            }
            Mock Test-Path { return $true }
            Mock Write-Host {
                $script:operationMessages.Add(($Object -join ' '))
            }
            Mock Get-CimInstance {
                if ([string]::IsNullOrWhiteSpace($Filter)) {
                    return $script:inventory
                }
                if ($Filter -notmatch '^\s*ProcessId\s*=\s*(\d+)\s*$') {
                    throw 'Unexpected process query in isolated test.'
                }
                [int]$requestedIdentifier = [int]$Matches[1]
                if ($script:currentProcesses.ContainsKey($requestedIdentifier)) {
                    return $script:currentProcesses[$requestedIdentifier]
                }
                return
            }
            Mock Stop-Process {
                foreach ($identifier in $Id) {
                    $script:stoppedIdentifiers.Add([int]$identifier)
                }
            }
            Mock Invoke-MoulaiPythonServer {
                throw 'Unexpected Python invocation in isolated test.'
            }
        }

        It 'preserves the server exit status and restores the caller directory' {
            [string]$originalLocation = (Get-Location).Path
            Mock Invoke-MoulaiPythonServer {
                [string]$script:invocationLocation = (Get-Location).Path
                return 7
            }

            [int]$result = Start-MoulaiApplication -ProjectRoot $script:operationProjectPath

            $result | Should Be 7
            $script:invocationLocation | Should Be $script:operationProjectPath
            (Get-Location).Path | Should Be $originalLocation
            Assert-MockCalled Invoke-MoulaiPythonServer -Times 1 -Exactly -Scope It
            Assert-MockCalled Stop-Process -Times 0 -Exactly -Scope It
        }

        It 'restores the caller directory after the Python invocation fails' {
            [string]$originalLocation = (Get-Location).Path
            Mock Invoke-MoulaiPythonServer { throw 'Controlled launcher failure.' }

            { Start-MoulaiApplication -ProjectRoot $script:operationProjectPath } | Should Throw 'Controlled launcher failure'

            (Get-Location).Path | Should Be $originalLocation
            Assert-MockCalled Invoke-MoulaiPythonServer -Times 1 -Exactly -Scope It
        }

        It 'refuses to launch when the project virtual environment is missing' {
            Mock Test-Path { return $false }

            { Start-MoulaiApplication -ProjectRoot $script:operationProjectPath } | Should Throw

            Assert-MockCalled Invoke-MoulaiPythonServer -Times 0 -Exactly -Scope It
        }

        It 'keeps owned servers running and reports their joined identifiers' {
            $script:inventory = @(
                (New-MoulaiTestProcess -ProcessIdentifier 88001 -CommandLine ('"{0}" -m uvicorn app.main:app --reload' -f $script:operationPythonPath)),
                (New-MoulaiTestProcess -ProcessIdentifier 88002 -CommandLine ('"{0}" -m uvicorn app.main:app --reload' -f $script:operationPythonPath))
            )

            Start-MoulaiApplication -ProjectRoot $script:operationProjectPath -KeepRunning | Should Be 0

            ($script:operationMessages -join ' ') | Should Match '88001, 88002'
            Assert-MockCalled Invoke-MoulaiPythonServer -Times 0 -Exactly -Scope It
        }

        It 'starts the application when only another project is running' {
            $script:inventory = @(
                (New-MoulaiTestProcess -ProcessIdentifier 88001 -CommandLine 'C:\Other\.venv\Scripts\python.exe -m uvicorn app.main:app --reload')
            )
            Mock Invoke-MoulaiPythonServer { return 0 }

            Start-MoulaiApplication -ProjectRoot $script:operationProjectPath -KeepRunning | Should Be 0

            Assert-MockCalled Invoke-MoulaiPythonServer -Times 1 -Exactly -Scope It
            Assert-MockCalled Stop-Process -Times 0 -Exactly -Scope It
        }

        It 'stops the owned reload child before its parent' {
            [object]$root = New-MoulaiTestProcess -ProcessIdentifier 88001 `
                -CommandLine ('"{0}" -m uvicorn app.main:app --reload' -f $script:operationPythonPath)
            [object]$child = New-MoulaiTestProcess -ProcessIdentifier 88002 -ParentIdentifier 88001 `
                -CreationDate ([datetime] '2026-10-15T08:01:00Z')
            [object]$foreign = New-MoulaiTestProcess -ProcessIdentifier 88003 `
                -CommandLine 'C:\Other\.venv\Scripts\python.exe -m uvicorn app.main:app --reload'
            $script:inventory = @($root, $child, $foreign)
            $script:currentProcesses[88001] = $root
            $script:currentProcesses[88002] = $child

            Stop-MoulaiApplication -ProjectRoot $script:operationProjectPath -Confirm:$false | Should Be 0

            ($script:stoppedIdentifiers -join ',') | Should Be '88002,88001'
        }

        It 'refuses a process identifier reused after inventory was collected' {
            [object]$root = New-MoulaiTestProcess -ProcessIdentifier 88001 `
                -CommandLine ('"{0}" -m uvicorn app.main:app --reload' -f $script:operationPythonPath)
            $script:inventory = @($root)
            $script:currentProcesses[88001] = New-MoulaiTestProcess -ProcessIdentifier 88001 `
                -CreationDate ([datetime] '2026-10-15T09:00:00Z')

            Stop-MoulaiApplication -ProjectRoot $script:operationProjectPath -Confirm:$false | Should Be 1

            $script:stoppedIdentifiers.Count | Should Be 0
            Assert-MockCalled Stop-Process -Times 0 -Exactly -Scope It
        }

        It 'skips a process that exited between inventory and identity verification' {
            [object]$root = New-MoulaiTestProcess -ProcessIdentifier 88001 `
                -CommandLine ('"{0}" -m uvicorn app.main:app --reload' -f $script:operationPythonPath)
            $script:inventory = @($root)

            Stop-MoulaiApplication -ProjectRoot $script:operationProjectPath -Confirm:$false | Should Be 0

            Assert-MockCalled Stop-Process -Times 0 -Exactly -Scope It
        }

        It 'returns failure when an owned process could not be stopped' {
            [object]$root = New-MoulaiTestProcess -ProcessIdentifier 88001 `
                -CommandLine ('"{0}" -m uvicorn app.main:app --reload' -f $script:operationPythonPath)
            $script:inventory = @($root)
            $script:currentProcesses[88001] = $root
            Mock Stop-Process { throw 'Controlled stop failure.' }

            Stop-MoulaiApplication -ProjectRoot $script:operationProjectPath -Confirm:$false | Should Be 1

            Assert-MockCalled Stop-Process -Times 1 -Exactly -Scope It
        }

        It 'never stops a process when WhatIf is requested' {
            [object]$root = New-MoulaiTestProcess -ProcessIdentifier 88001 `
                -CommandLine ('"{0}" -m uvicorn app.main:app --reload' -f $script:operationPythonPath)
            $script:inventory = @($root)
            $script:currentProcesses[88001] = $root

            Stop-MoulaiApplication -ProjectRoot $script:operationProjectPath -WhatIf | Should Be 0

            Assert-MockCalled Stop-Process -Times 0 -Exactly -Scope It
        }

        It 'returns success without stopping anything when no owned server exists' {
            Stop-MoulaiApplication -ProjectRoot $script:operationProjectPath -Confirm:$false | Should Be 0

            Assert-MockCalled Stop-Process -Times 0 -Exactly -Scope It
            Assert-MockCalled Invoke-MoulaiPythonServer -Times 0 -Exactly -Scope It
        }
    }

    # ==============================================
    # LITERAL RUNTIME PATH RESOLUTION
    # ==============================================

    Describe 'MoulAI runtime path resolution' {
        BeforeEach {
            Mock Get-CimInstance { throw 'Real process inventory is forbidden in this test.' }
            Mock Stop-Process { throw 'Real process termination is forbidden in this test.' }
            Mock Invoke-MoulaiPythonServer { throw 'Real Python invocation is forbidden in this test.' }
        }

        It 'resolves a project path containing spaces and brackets without changing location' {
            [string]$projectPath = Join-Path (Get-Item 'TestDrive:').FullName 'Application [Local]'
            [void][System.IO.Directory]::CreateDirectory($projectPath)
            [string]$originalLocation = (Get-Location).Path

            [object]$runtime = Get-MoulaiRuntime -ProjectRoot $projectPath

            $runtime.ProjectPath | Should Be $projectPath
            $runtime.PythonPath | Should Be (Join-Path $projectPath '.venv\Scripts\python.exe')
            $runtime.Application | Should Be 'app.main:app'
            (Get-Location).Path | Should Be $originalLocation
        }
    }

    # ==============================================
    # EXIT STATUS BOUNDARY WITHOUT A NATIVE PROCESS
    # ==============================================

    Describe 'MoulAI Python exit status boundary' {
        BeforeEach {
            [string]$script:commandDoubleDirectory = (New-Item -ItemType Directory -Path 'TestDrive:\Command Boundary' -Force).FullName
            [object]$nativeExitCodeVariable = Get-Variable -Name LASTEXITCODE -Scope Global -ErrorAction SilentlyContinue
            [bool]$script:hadNativeExitCode = $null -ne $nativeExitCodeVariable
            [object]$script:savedNativeExitCodeValue = $null
            if ($script:hadNativeExitCode) {
                $script:savedNativeExitCodeValue = $nativeExitCodeVariable.Value
            }
            Mock Get-CimInstance { throw 'Real process inventory is forbidden in this test.' }
            Mock Stop-Process { throw 'Real process termination is forbidden in this test.' }
        }

        AfterEach {
            if (-not $script:hadNativeExitCode) {
                Remove-Variable -Name LASTEXITCODE -Scope Global -ErrorAction SilentlyContinue
            }
            else {
                $global:LASTEXITCODE = $script:savedNativeExitCodeValue
            }
        }

        It 'returns only the integer exit status while preserving normal command output' {
            [string]$commandPath = Join-Path $script:commandDoubleDirectory 'reported-exit.ps1'
            [string]$commandContent = @'
# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# Synthetic command used only to exercise the exit status boundary.
Write-Output 'Synthetic command output.'
$global:LASTEXITCODE = 7
'@
            [System.IO.File]::WriteAllText($commandPath, $commandContent, (New-Object System.Text.UTF8Encoding($true)))
            [string]$originalErrorAction = $ErrorActionPreference

            [object[]]$result = @(Invoke-MoulaiPythonServer -PythonPath $commandPath -Application 'app.main:app')

            $result.Count | Should Be 1
            ($result[0] -is [int]) | Should Be $true
            $result[0] | Should Be 7
            $ErrorActionPreference | Should Be $originalErrorAction
            Assert-MockCalled Get-CimInstance -Times 0 -Exactly -Scope It
            Assert-MockCalled Stop-Process -Times 0 -Exactly -Scope It
        }

        It 'refuses a stale exit status and restores error handling after failure' {
            [string]$commandPath = Join-Path $script:commandDoubleDirectory 'missing-exit.ps1'
            [string]$commandContent = @'
# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# Synthetic command deliberately reports no native exit status.
Write-Output 'Synthetic command without an exit status.'
'@
            [System.IO.File]::WriteAllText($commandPath, $commandContent, (New-Object System.Text.UTF8Encoding($true)))
            $global:LASTEXITCODE = 29
            [string]$originalErrorAction = $ErrorActionPreference

            { Invoke-MoulaiPythonServer -PythonPath $commandPath -Application 'app.main:app' } | Should Throw

            ($null -eq $global:LASTEXITCODE) | Should Be $true
            $ErrorActionPreference | Should Be $originalErrorAction
            Assert-MockCalled Get-CimInstance -Times 0 -Exactly -Scope It
            Assert-MockCalled Stop-Process -Times 0 -Exactly -Scope It
        }
    }
}
