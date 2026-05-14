@echo off
set "SCRIPT_DIR=%~dp0"

:: Detect deployment mode based on what is present in the installation.
::
::   Mode 1 (PyInstaller): scaldys.exe is in bin/ alongside this script.
::     Add bin/ to PATH and call the frozen executable directly.
::
::   Mode 2 (PythonRuntime): scaldys.exe is absent; the application runs
::     from the PythonRuntime virtual environment.  Activate the venv so
::     that the 'scaldys' console script is on PATH, then call it.

if exist "%SCRIPT_DIR%scaldys.exe" (
    set "PATH=%SCRIPT_DIR%;%PATH%"
    cmd /k "scaldys.exe --help"
) else (
    set "PYRUNTIME_ACTIVATE=%SCRIPT_DIR%..\PythonRuntime\Scripts\activate.bat"
    if exist "%PYRUNTIME_ACTIVATE%" (
        call "%PYRUNTIME_ACTIVATE%"
        cmd /k "scaldys --help"
    ) else (
        echo ERROR: Application not found. Check your installation or run setup_pyruntime.ps1 as administrator.
        pause
    )
)
