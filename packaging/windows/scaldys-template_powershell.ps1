$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Clear-Host

# Use passed arguments if any, otherwise default to --help
$Command = if ($args.Count -gt 0) { $args } else { "--help" }

# Detect deployment mode based on what is present in the installation.
#
#   Mode 1 (PyInstaller): scaldys-template.exe is in bin/ alongside this script.
#     Add bin/ to PATH and call the frozen executable directly.
#
#   Mode 2 (PythonRuntime): scaldys-template.exe is absent; the application runs
#     from the PythonRuntime virtual environment.  Activate the venv so
#     that the 'scaldys-template' console script is on PATH, then call it.

$pyinstallerExe    = Join-Path $scriptDir 'scaldys-template.exe'
$pyruntimeActivate = Join-Path (Split-Path -Parent $scriptDir) 'PythonRuntime\Scripts\Activate.ps1'

if (Test-Path $pyinstallerExe) {
    $env:Path += ";$scriptDir"
    scaldys-template.exe $Command
} elseif (Test-Path $pyruntimeActivate) {
    & $pyruntimeActivate
    scaldys-template $Command
} else {
    Write-Warning "Application not found. Check your installation or run setup_pyruntime.ps1 as administrator."
}
