$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
#$binDir = Join-Path $scriptDir 'bin'

$env:Path += ';{0}' -f $scriptDir
Clear-Host
scaldys.exe --help