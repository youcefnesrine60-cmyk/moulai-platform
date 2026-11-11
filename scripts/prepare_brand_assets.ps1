# ==============================================
# MoulAI™ Platform - Agent-as-a-Service
# Author: Youcef Nesrine
# License: CC BY-NC-ND 4.0
# Copyright (c) 2026 Youcef Nesrine. All Rights Reserved.
# ==============================================

# ==============================================
# APPROVED BRAND RESOURCE DERIVATION
# Preserve original files; remove only near-white pixels outside each favicon
# silhouette row, retaining every interior pixel, including the white doorway.
# ==============================================

$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$source = Join-Path $projectRoot 'assets/originals/GateWay.png'
if ((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash -ne '6F1C9B5B894D789C61081B6D5D49C8B8BCD273ADE8A97C6A8677ACFADDB98BB8') {
    throw 'Unreviewed favicon source; no resource written.'
}
$image = [System.Drawing.Bitmap]::new($source)
$result = [System.Drawing.Bitmap]::new($image.Width, $image.Height, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
$removed = 0
try {
    for ($y = 0; $y -lt $image.Height; $y++) {
        $left = $image.Width
        $right = -1
        for ($x = 0; $x -lt $image.Width; $x++) {
            $pixel = $image.GetPixel($x, $y)
            if ([Math]::Min($pixel.R, [Math]::Min($pixel.G, $pixel.B)) -lt 230) {
                $left = [Math]::Min($left, $x)
                $right = [Math]::Max($right, $x)
            }
        }
        for ($x = 0; $x -lt $image.Width; $x++) {
            $pixel = $image.GetPixel($x, $y)
            if ($x -lt $left -or $x -gt $right) {
                $result.SetPixel($x, $y, [System.Drawing.Color]::FromArgb(0, $pixel.R, $pixel.G, $pixel.B))
                $removed++
            } else {
                $result.SetPixel($x, $y, $pixel)
            }
        }
    }
    $png = Join-Path $projectRoot 'frontend/public/brand/GateWay-transparent-v2.png'
    $result.Save($png, [System.Drawing.Imaging.ImageFormat]::Png)
    # PNG-compressed ICO preserves the exact 30 x 39 raster; no resampling or recolouring.
    $bytes = [System.IO.File]::ReadAllBytes($png)
    $ico = Join-Path $projectRoot 'frontend/public/brand/GateWay-transparent-v2.ico'
    $writer = [System.IO.BinaryWriter]::new([System.IO.File]::Create($ico))
    try {
        $writer.Write([uint16]0); $writer.Write([uint16]1); $writer.Write([uint16]1)
        $writer.Write([byte]$result.Width); $writer.Write([byte]$result.Height)
        $writer.Write([byte]0); $writer.Write([byte]0)
        $writer.Write([uint16]1); $writer.Write([uint16]32)
        $writer.Write([uint32]$bytes.Length); $writer.Write([uint32]22)
        $writer.Write($bytes)
    } finally { $writer.Dispose() }
    [pscustomobject]@{ width=$result.Width; height=$result.Height; exteriorPixelsMadeTransparent=$removed; interiorPixelsUnchanged=($result.Width*$result.Height-$removed) } | ConvertTo-Json
} finally { $image.Dispose(); $result.Dispose() }

# Copy the newly approved dark original byte for byte; the light logo is untouched.
$dark = Join-Path $projectRoot 'assets/originals/moulai-logo-Mode-Sombre.png'
if ((Get-FileHash -LiteralPath $dark -Algorithm SHA256).Hash -ne '2449087CFB4371606965A320FAE2FF22880F802B91C6B84D353B098C9C5BDB0E') {
    throw 'Unreviewed dark logo; original was not changed.'
}
Copy-Item -LiteralPath $dark -Destination (Join-Path $projectRoot 'frontend/public/brand/moulai-logo-dark-approved-20261111.png')
