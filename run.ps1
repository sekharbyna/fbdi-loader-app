# Fusion FBDI Load Console — Windows PowerShell
# No pip / venv / Rust / Visual C++ required.
#
#   cd D:\Fusion_FBDI_Load_Console\fbdi-loader-app
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#   .\run.ps1

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot
Get-ChildItem -File -ErrorAction SilentlyContinue | Unblock-File -ErrorAction SilentlyContinue

$pyLauncher = Get-Command py -ErrorAction SilentlyContinue
$pythonExe = Get-Command python -ErrorAction SilentlyContinue

if ($pyLauncher) {
    Write-Host "Using: py -3"
    Write-Host "Starting server (no package install)..."
    Write-Host "Open http://127.0.0.1:8000" -ForegroundColor Green
    Write-Host "Stop with Ctrl+C"
    py -3 server.py
} elseif ($pythonExe) {
    Write-Host "Using: python"
    Write-Host "Starting server (no package install)..."
    Write-Host "Open http://127.0.0.1:8000" -ForegroundColor Green
    Write-Host "Stop with Ctrl+C"
    python server.py
} else {
    Write-Host "Python is not installed or not on PATH." -ForegroundColor Red
    Write-Host "Install Python 3.11 or 3.12 from https://www.python.org/downloads/"
    Write-Host "Tick 'Add python.exe to PATH'. You do NOT need Visual C++ or Rust."
    exit 1
}
