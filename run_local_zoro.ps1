param([Parameter(Mandatory=$true)][string]$PythonPath,[Parameter(Mandatory=$true)][string]$ModelPath)
$ErrorActionPreference='Stop'
Set-Location $PSScriptRoot
& $PythonPath -m arena.generation_server --model $ModelPath
if ($LASTEXITCODE -ne 0) { throw 'Public generation failed; this is not a Typed Decision server.' }
