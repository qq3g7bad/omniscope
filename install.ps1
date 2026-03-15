# install.ps1 — Set up the omniscope tool on Windows
# Run with: powershell -ExecutionPolicy Bypass -File install.ps1

$ErrorActionPreference = "Stop"
$RequiredMajor = 3
$RequiredMinor = 10

# ── Find Python ───────────────────────────────────────────────────────────────

function Find-Python {
    foreach ($cmd in @("py", "python", "python3")) {
        try {
            $ver = & $cmd -c "import sys; print(sys.version_info.major, sys.version_info.minor)" 2>$null
            if ($ver) {
                $parts = $ver -split " "
                $major = [int]$parts[0]
                $minor = [int]$parts[1]
                if ($major -ge $RequiredMajor -and $minor -ge $RequiredMinor) {
                    return $cmd
                }
            }
        } catch {}
    }
    return $null
}

$Python = Find-Python
if (-not $Python) {
    Write-Host ""
    Write-Host "ERROR: Python $RequiredMajor.$RequiredMinor or newer is required but was not found." -ForegroundColor Red
    Write-Host ""
    Write-Host "Install Python from: https://www.python.org/downloads/"
    Write-Host "  - Check 'Add Python to PATH' during installation."
    Write-Host ""
    Write-Host "Or install via winget:"
    Write-Host "  winget install Python.Python.3.12"
    Write-Host ""
    exit 1
}

$PythonVersion = & $Python --version
Write-Host "Using Python: $Python ($PythonVersion)"

# ── Create virtual environment ────────────────────────────────────────────────

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Venv = Join-Path $ScriptDir "venv"
$VenvPip = "$Venv\Scripts\pip.exe"

if (-not (Test-Path $Venv)) {
    Write-Host "Creating virtual environment..."
    & $Python -m venv $Venv
} elseif (-not (Test-Path $VenvPip) -or -not (& $VenvPip --version 2>$null)) {
    Write-Host "Virtual environment is broken (stale paths), recreating..."
    Remove-Item -Recurse -Force $Venv
    & $Python -m venv $Venv
} else {
    Write-Host "Virtual environment already exists, skipping creation."
}

# ── Install package ───────────────────────────────────────────────────────────

Write-Host "Installing omniscope..."
& $VenvPip install --quiet --upgrade pip
& $VenvPip install --quiet -e $ScriptDir

# ── Install launcher to %USERPROFILE%\.local\bin ──────────────────────────────

$LocalBin = "$env:USERPROFILE\.local\bin"
New-Item -ItemType Directory -Force -Path $LocalBin | Out-Null

$WrapperPath = "$LocalBin\omniscope.bat"
$OmniscopeExe = "$Venv\Scripts\omniscope.exe"
Set-Content -Path $WrapperPath -Value "@echo off`r`n""$OmniscopeExe"" %*"

$UserPath = [System.Environment]::GetEnvironmentVariable("PATH", "User")
if ($UserPath -notlike "*$LocalBin*") {
    [System.Environment]::SetEnvironmentVariable("PATH", "$UserPath;$LocalBin", "User")
    $env:PATH += ";$LocalBin"
    Write-Host "Added $LocalBin to your user PATH."
}

Write-Host ""
Write-Host "Installation complete." -ForegroundColor Green
Write-Host ""
Write-Host "Usage:"
Write-Host "  omniscope <subcommand> [options]"
Write-Host "  omniscope --help"
Write-Host ""
