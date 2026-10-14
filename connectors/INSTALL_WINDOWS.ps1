param([Parameter(Mandatory=$true)][string]$Server)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
py -3 -m venv .executor-venv
if ($LASTEXITCODE -ne 0) { throw 'Falha criando ambiente Python' }
& .\.executor-venv\Scripts\python.exe -m pip install -r connectors/requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Falha instalando dependências' }
& .\.executor-venv\Scripts\python.exe -m connectors.setup --server $Server
if ($LASTEXITCODE -ne 0) { throw 'Falha criando configuração' }
$privateDir = Join-Path $HOME '.jarvis-executor'
$account = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
icacls $privateDir /inheritance:r /grant:r "${account}:(OI)(CI)F" | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Falha protegendo diretório privado' }
Write-Host 'Instalado. Pareamento: .executor-venv\Scripts\python.exe -m connectors.agent pair'
