param([int]$Port = 8781)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$pythonExe = Join-Path $projectRoot '.venv\Scripts\python.exe'
Write-Host "Retrieval and model judgment: http://127.0.0.1:$Port/refinement/index.html"
Write-Host "All ten preserved methods: http://127.0.0.1:$Port/ten-methods/index.html"
Write-Host 'Keep this terminal running. Model calls are serialized and cached.'
& $pythonExe -m tools.serve_retrieval_judgments --port $Port
