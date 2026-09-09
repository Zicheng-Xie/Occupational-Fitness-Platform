param([switch]$Chroma)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
Push-Location -LiteralPath $projectRoot
try {
    if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
        python -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw 'Virtual environment creation failed' }
    }
    $extras = if ($Chroma) { '.[dev,api,chroma]' } else { '.[dev,api]' }
    & '.venv\Scripts\python.exe' -m pip install -e $extras
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
    & '.venv\Scripts\fitness-rag.exe' build-knowledge
    if ($LASTEXITCODE -ne 0) { throw 'Source verification failed' }
    & '.venv\Scripts\fitness-rag.exe' export-schemas
    if ($LASTEXITCODE -ne 0) { throw 'Schema export failed' }
    Write-Output 'Ready. Run .venv\Scripts\fitness-rag.exe demo from the project root.'
}
finally { Pop-Location }
