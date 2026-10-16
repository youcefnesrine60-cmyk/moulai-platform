# MoulAI PowerShell standards

The maintained launchers are `run_moulai.ps1`, `start_or_keep_moulai.ps1`, and
`stop_moulai.ps1`. They share `scripts/MoulAI.Process.psm1`; their isolated tests
are in `tests/powershell/MoulAI.Process.Tests.ps1`.

## Source format

Every maintained PowerShell source starts with this exact header:

```powershell
# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================
```

Save `.ps1` and `.psm1` files as UTF-8 with BOM for Windows PowerShell 5.1,
including accented French text and the trademark character. Use straight
quotation marks for delimiters and avoid typographic apostrophes inside
single-quoted strings. Declare `#Requires -Version 5.1` explicitly.

## Function and error contracts

- Use advanced functions with named, typed parameters. Runtime operations use
  `PositionalBinding = $false`, validate required arguments, and declare output
  types. Python keyword-only `*` syntax does not apply to PowerShell.
- Enable `Set-StrictMode -Version Latest` and use terminating errors for runtime
  operations. Document the specific exception at the native Python boundary:
  Uvicorn writes normal logs to stderr, so its exit code determines failure.
- Keep comment-based help, consistent section headings, and comments explaining
  ownership checks and native-process behavior. Remove unused code and imports;
  do not leave unfinished functions, TODOs, or placeholder implementations.
- Report meaningful startup, shutdown, and failure events without logging
  credentials, connection strings, tokens, or payment account details. Return
  structured values from helpers and keep progress messages out of those values.
- Resolve paths with `$PSScriptRoot` and `Join-Path`; use `-LiteralPath` for
  filesystem operations. Restore a changed working directory in `finally`.
- Preserve the actual Python exit code. A script-level failure returns `1`;
  keeping an existing server or finding no server to stop returns `0`.

Configuration belongs to the existing central Settings system and the local
`.env`, not PowerShell literals. The scripts do not perform database migrations,
administrative identity changes, Render deployments, or Telegram configuration.

## Application process ownership

`run_moulai.ps1` always invokes this project's virtualenv Python in the foreground
with `-m uvicorn app.main:app --reload`. `start_or_keep_moulai.ps1` first checks
for an existing server belonging to this project. Another project's Uvicorn
process does not count as an existing MoulAI server.

The canonical match requires `-m`, `uvicorn`, and `app.main:app` in that order
immediately after the Python invocation. Ownership requires either the exact
absolute project virtualenv invocation path, or a relative Python invocation
whose recorded executable path equals that virtualenv path. Missing identity
data and other projects are rejected. A differently formatted manual command
may not be recognized; there is no fallback that stops every Python or Uvicorn
process by name.

`stop_moulai.ps1` follows verified roots and their reload descendants, stopping
children before parents. It checks creation times while constructing the tree
and rechecks each PID's creation time immediately before stopping it, refusing
reused PIDs. `-WhatIf` previews the operation; `-Confirm` uses standard PowerShell
confirmation behavior. Declining a proposed stop leaves that process running.

## Verification without starting or stopping the application

Parse the maintained sources without executing their contents:

```powershell
$paths = @(
    'run_moulai.ps1',
    'start_or_keep_moulai.ps1',
    'stop_moulai.ps1',
    'scripts/MoulAI.Process.psm1',
    'tests/powershell/MoulAI.Process.Tests.ps1'
)
foreach ($path in $paths) {
    $tokens = $null
    $parseErrors = $null
    $null = [System.Management.Automation.Language.Parser]::ParseFile(
        (Join-Path -Path (Get-Location).Path -ChildPath $path),
        [ref]$tokens,
        [ref]$parseErrors
    )
    if ($parseErrors.Count -gt 0) {
        throw ($parseErrors.Message -join [Environment]::NewLine)
    }
}
```

From the project directory, run the Pester 3.4 suite in an isolated Windows
PowerShell process:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command '$result = Invoke-Pester -Script ./tests/powershell/MoulAI.Process.Tests.ps1 -PassThru; if ($result.FailedCount -gt 0) { exit 1 }'
```

`-ExecutionPolicy Bypass` applies only to that process; it does not change the
machine's saved execution policy. The tests mock process inventory, termination,
and the Python server boundary. Boundary-specific command doubles are temporary
PowerShell script files in Pester's test directory. The suite does not start a server, connect to a database,
or stop real processes.

The current verification completed all 24 isolated Pester cases successfully,
with no skipped or pending cases. Both file parsing and explicit UTF-8 parsing
reported zero syntax errors for the three launchers, shared module, and test
source. All five files have the required header and UTF-8 BOM. The saved
[Pester results](../artifacts/powershell-review/pester-results.xml) record the
test outcome. This verification did not launch the application or stop live
processes, and did not change the saved execution policy.
