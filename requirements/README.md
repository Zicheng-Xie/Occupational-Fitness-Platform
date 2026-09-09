# Environment snapshot

`environment-windows-py314.txt` records the tested local Python 3.14 Windows environment, including optional Chroma/API/development packages. It contains pinned package versions, not package hashes or model weights. It is a platform-specific environment record; `pyproject.toml` remains the portable dependency definition.

For a fresh project environment use `scripts/bootstrap.ps1` (add `-Chroma` for the vector backend), or `python -m pip install -e ".[dev,api]"`. Ollama and its model weights are installed separately; model names are configured in `configs/workflow*.yaml`.

The included CI definition targets Python 3.11 and 3.14. Remote CI has not been run because this local project has no Git repository or remote configured.
