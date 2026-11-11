# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# LOCAL INVOICE PDF VISUAL VERIFICATION
# Render only the three known acceptance PDFs under this repository's artifacts folder using Windows' existing PDF engine.
# ==============================================

<#
.SYNOPSIS
Reopen generated FR/EN/AR acceptance PDFs and render every actual page to PNG.
.DESCRIPTION
No download, application automation, external service or database access. Fail if
the directory is outside artifacts, an expected PDF is absent or rendering fails.
#>
param([Parameter(Mandatory = $true)][string]$Directory)

$ErrorActionPreference = 'Stop'
$artifactRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../artifacts')) + [IO.Path]::DirectorySeparatorChar
$targetDirectory = [IO.Path]::GetFullPath($Directory)
if (-not $targetDirectory.StartsWith($artifactRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'Only repository acceptance artifacts can be rendered.'
}
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Data.Pdf.PdfDocument, Windows.Data.Pdf, ContentType = WindowsRuntime]
$null = [Windows.Data.Pdf.PdfPageRenderOptions, Windows.Data.Pdf, ContentType = WindowsRuntime]
$null = [Windows.Storage.Streams.InMemoryRandomAccessStream, Windows.Storage.Streams, ContentType = WindowsRuntime]
$null = [Windows.Storage.Streams.DataReader, Windows.Storage.Streams, ContentType = WindowsRuntime]
$asTask = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
} | Select-Object -First 1
$asAction = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and -not $_.IsGenericMethod -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.FullName -eq 'Windows.Foundation.IAsyncAction'
} | Select-Object -First 1

# ==============================================
# AWAIT ONE WINDOWS RUNTIME RESULT
# Convert the supplied asynchronous file, PDF or buffer operation without bypassing errors.
# ==============================================

function Wait-WinRtResult {
    param([object]$Operation, [Type]$ResultType)
    $task = $asTask.MakeGenericMethod($ResultType).Invoke($null, @($Operation))
    return $task.GetAwaiter().GetResult()
}

# ==============================================
# REOPEN AND RENDER ALL PAGES
# The result comes from the exported PDF bytes, not a second HTML screenshot.
# ==============================================

$results = @()
foreach ($locale in @('fr', 'en', 'ar')) {
    $pdfPath = Join-Path $targetDirectory "invoice-$locale.pdf"
    $file = Wait-WinRtResult -Operation ([Windows.Storage.StorageFile]::GetFileFromPathAsync($pdfPath)) -ResultType ([Windows.Storage.StorageFile])
    $pdf = Wait-WinRtResult -Operation ([Windows.Data.Pdf.PdfDocument]::LoadFromFileAsync($file)) -ResultType ([Windows.Data.Pdf.PdfDocument])
    if ($pdf.PageCount -lt 1) { throw 'An exported invoice has no readable pages.' }
    $pages = @()
    for ($index = 0; $index -lt $pdf.PageCount; $index++) {
        $page = $pdf.GetPage($index)
        $stream = [Windows.Storage.Streams.InMemoryRandomAccessStream]::new()
        try {
            $options = [Windows.Data.Pdf.PdfPageRenderOptions]::new()
            $options.DestinationWidth = 1191
            $renderTask = $asAction.Invoke($null, @($page.RenderToStreamAsync($stream, $options)))
            $null = $renderTask.GetAwaiter().GetResult()
            $reader = [Windows.Storage.Streams.DataReader]::new($stream.GetInputStreamAt(0))
            try {
                $null = Wait-WinRtResult -Operation ($reader.LoadAsync([uint32]$stream.Size)) -ResultType ([uint32])
                $bytes = [byte[]]::new([int]$stream.Size)
                $null = $reader.ReadBytes($bytes)
                $name = "render-$locale-$($index + 1).png"
                [IO.File]::WriteAllBytes((Join-Path $targetDirectory $name), $bytes)
                $pages += @{ image = $name; width = $page.Size.Width; height = $page.Size.Height }
            }
            finally { $reader.Dispose() }
        }
        finally { $stream.Dispose(); $page.Dispose() }
    }
    $results += @{ locale = $locale; pages = $pages; pageCount = $pdf.PageCount; sha256 = (Get-FileHash -LiteralPath $pdfPath -Algorithm SHA256).Hash }
}
$receipt = @{ status = 'PASS'; renderer = 'Windows.Data.Pdf'; source = 'actual exported PDF bytes'; physicalPrinter = 'NOT TESTED'; results = $results } | ConvertTo-Json -Depth 6
[IO.File]::WriteAllText((Join-Path $targetDirectory 'pdf-rendering.json'), $receipt, [Text.UTF8Encoding]::new($false))
Write-Output $receipt
