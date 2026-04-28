@echo off
set "SCRIPT_DIR=%~dp0"
set "PATH=%SCRIPT_DIR%;%PATH%"
cmd /k "scaldys.exe --help"
