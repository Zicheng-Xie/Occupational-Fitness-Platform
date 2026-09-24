param([switch]$Offline, [int]$Port = 8000)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$pythonExe = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonExe)) { throw 'Run scripts/bootstrap.ps1 first.' }
$env:FITNESS_WORKFLOW_CONFIG = if ($Offline) { 'configs/workflow.offline.yaml' } else { 'configs/workflow.yaml' }
Write-Host "Occupational Fitness Platform: http://127.0.0.1:$Port"
Write-Host 'Keep this terminal running. Press Ctrl+C to stop the local workspace.'
& $pythonExe -m uvicorn occupational_fitness_rag.api:app --host 127.0.0.1 --port $Port
