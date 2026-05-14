<#
.SYNOPSIS
    Sets up the PythonRuntime environment bundled with this application.

.DESCRIPTION
    Creates a Python virtual environment named "PythonRuntime" inside the
    application's installation directory and installs the project package
    and its dependencies (including Jupyter) so that tools such as Quarto
    can render the generated notebooks.

    The required Python version is read from "bin\.python-version" -- the same
    file that drives the build -- so there is a single source of truth.

    The environment is created using the uv.exe bundled with the application,
    so no pre-existing Python or uv installation is required on the machine.

    Re-running this script on an existing environment is safe: uv will skip
    packages that are already installed.

.PARAMETER InstallDir
    Root of the application installation (e.g. "C:\Program Files\Scaldys").
    When omitted, the directory is inferred from the script's own location
    (the script lives in <InstallDir>\bin\).

.EXAMPLE
    # Run from an elevated PowerShell prompt after installation:
    & "C:\Program Files\Scaldys\bin\setup_pyruntime.ps1"

.EXAMPLE
    # Pass the install directory explicitly:
    & "C:\Program Files\Scaldys\bin\setup_pyruntime.ps1" -InstallDir "C:\Program Files\Scaldys"
#>

param(
    [Parameter(Mandatory = $false)]
    [string]$InstallDir
)

Set-StrictMode -Version Latest

# ============================================================
# PROJECT CONFIGURATION -- change these two values when adapting
# this script to a different project.
# ============================================================
$ProjectDisplayName = "Scaldys"   # Human-readable name (used in messages)
$PackageName        = "scaldys"   # pip-installable package name
# ============================================================

function Pause-OnExit {
    Write-Host ""
    Write-Host "Press Enter to close this window..."
    $null = Read-Host
}

try {
    # ---------------------------------------------------------------------------
    # Resolve install directory
    # ---------------------------------------------------------------------------
    if (-not $InstallDir) {
        # Script lives in <InstallDir>\bin\ -- go one level up
        $InstallDir = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
    }

    $uvExe             = Join-Path $InstallDir "bin\uv.exe"
    $pythonVersionFile = Join-Path $InstallDir "bin\.python-version"
    $wheelsDir         = Join-Path $InstallDir "wheels"
    $targetDir         = Join-Path $InstallDir "PythonRuntime"
    $pythonExe         = Join-Path $targetDir  "Scripts\python.exe"

    # ---------------------------------------------------------------------------
    # Read required Python version from .python-version (single source of truth)
    # ---------------------------------------------------------------------------
    if (-not (Test-Path $pythonVersionFile)) {
        throw ".python-version not found at: $pythonVersionFile`nThe $ProjectDisplayName installation may be incomplete. Please re-run the $ProjectDisplayName installer."
    }
    $pythonVersion = (Get-Content $pythonVersionFile).Trim()

    Write-Host ""
    Write-Host "$ProjectDisplayName`: Setting up PythonRuntime environment"
    Write-Host "--------------------------------------------------------------"
    Write-Host "  Install directory : $InstallDir"
    Write-Host "  Python version    : $pythonVersion  (from .python-version)"
    Write-Host "  Target environment: $targetDir"
    Write-Host ""

    # ---------------------------------------------------------------------------
    # Pre-flight: uv must be present
    # ---------------------------------------------------------------------------
    if (-not (Test-Path $uvExe)) {
        throw "uv.exe not found at: $uvExe`nThe $ProjectDisplayName installation may be incomplete. Please re-run the $ProjectDisplayName installer."
    }

    Write-Host "  uv  : $uvExe"
    Write-Host ""

    # ---------------------------------------------------------------------------
    # Step 1: Make the required Python version available to uv
    # ---------------------------------------------------------------------------
    Write-Host "[1/3] Installing Python $pythonVersion via uv (skipped if already cached) ..."
    & $uvExe python install $pythonVersion
    if ($LASTEXITCODE -ne 0) {
        throw "uv python install $pythonVersion failed (exit code $LASTEXITCODE). Check your internet connection and try again."
    }

    # ---------------------------------------------------------------------------
    # Step 2: Create the virtual environment
    # ---------------------------------------------------------------------------
    Write-Host ""
    Write-Host "[2/3] Creating virtual environment ..."
    & $uvExe venv $targetDir --python $pythonVersion
    if ($LASTEXITCODE -ne 0) {
        throw "uv venv failed (exit code $LASTEXITCODE). Target: $targetDir"
    }

    # ---------------------------------------------------------------------------
    # Step 3: Install the project package (with all its dependencies) from the
    #         bundled wheel. pyyaml is added explicitly because Quarto's own
    #         Jupyter scripts need it and it may not be a project dependency.
    # ---------------------------------------------------------------------------
    Write-Host ""
    Write-Host "[3/3] Installing $PackageName and dependencies (this may take a moment) ..."
    & $uvExe pip install --python $pythonExe --find-links $wheelsDir $PackageName pyyaml
    if ($LASTEXITCODE -ne 0) {
        throw "uv pip install failed (exit code $LASTEXITCODE)."
    }

    # ---------------------------------------------------------------------------
    # Done
    # ---------------------------------------------------------------------------
    Write-Host ""
    Write-Host "--------------------------------------------------------------"
    Write-Host "SUCCESS: PythonRuntime environment is ready."
    Write-Host "$ProjectDisplayName's '$PackageName render' command will use it automatically."

} catch {
    Write-Host ""
    Write-Host "--------------------------------------------------------------"
    Write-Host "ERROR: Setup failed."
    Write-Host $_.Exception.Message
    Write-Host ""
    Write-Host "To retry, run from an elevated PowerShell prompt:"
    Write-Host "  & `"$InstallDir\bin\setup_pyruntime.ps1`""
    Pause-OnExit
    exit 1
}

Pause-OnExit
