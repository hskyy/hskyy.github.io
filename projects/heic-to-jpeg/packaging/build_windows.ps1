# Builds HeicToJpeg.exe and the installer wizard on Windows.
# Usage (PowerShell, from projects\heic-to-jpeg):
#   .\packaging\build_windows.ps1
# Requires: Python 3.11+ on PATH, Inno Setup 6 (ISCC.exe) installed.

$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")

$version = (Select-String -Path "src\heic_to_jpeg\__init__.py" -Pattern '__version__ = "([^"]+)"').Matches[0].Groups[1].Value
Write-Host "Building HEIC to JPEG $version"

python -m pip install --upgrade pip
python -m pip install -r requirements-build.txt

python packaging\make_icon.py

if (Test-Path build) { Remove-Item build -Recurse -Force }
if (Test-Path dist)  { Remove-Item dist  -Recurse -Force }

python -m PyInstaller --clean --noconfirm packaging\HeicToJpeg.spec
if (-not (Test-Path "dist\HeicToJpeg.exe")) { throw "PyInstaller did not produce dist\HeicToJpeg.exe" }

$iscc = Get-Command ISCC.exe -ErrorAction SilentlyContinue
if (-not $iscc) {
    $candidates = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
    )
    $found = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $found) { throw "Inno Setup 6 (ISCC.exe) not found. Install from https://jrsoftware.org/isdl.php" }
    $isccPath = $found
} else {
    $isccPath = $iscc.Source
}

& $isccPath "/DAppVersion=$version" "packaging\HeicToJpeg.iss"

Write-Host ""
Write-Host "Done:"
Get-ChildItem dist | ForEach-Object { Write-Host ("  " + $_.FullName + "  (" + [math]::Round($_.Length / 1MB, 1) + " MB)") }
