$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Clear-Host

# Detect deployment mode based on what is present in the installation.
#
#   Mode 1 (PyInstaller): scaldys.exe is in bin/ alongside this script.
#     Add bin/ to PATH and call the frozen executable directly.
#
#   Mode 2 (PythonRuntime): scaldys.exe is absent; the application runs
#     from the PythonRuntime virtual environment.  Activate the venv so
#     that the 'scaldys' console script is on PATH, then call it.

$pyinstallerExe    = Join-Path $scriptDir 'scaldys.exe'
$pyruntimeActivate = Join-Path (Split-Path -Parent $scriptDir) 'PythonRuntime\Scripts\Activate.ps1'

if (Test-Path $pyinstallerExe) {
    $env:Path += ";$scriptDir"
    scaldys.exe --help
} elseif (Test-Path $pyruntimeActivate) {
    & $pyruntimeActivate
    scaldys --help
} else {
    Write-Warning "Application not found. Check your installation or run setup_pyruntime.ps1 as administrator."
}
