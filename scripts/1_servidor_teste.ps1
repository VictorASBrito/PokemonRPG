# Inicie este arquivo no primeiro terminal PowerShell, a partir de qualquer pasta.
$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot
$python = Join-Path $raiz ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Ambiente virtual não encontrado em $python. Rode: python -m venv .venv; .\.venv\Scripts\python.exe -m pip install -r requirements.txt"
}
if (-not (Test-Path -LiteralPath (Join-Path $raiz ".env"))) {
    throw "Arquivo .env não encontrado em $raiz. Copie .env.example, configure DATABASE_URL e POKEMON_RPG_SECRET_KEY."
}

Push-Location $raiz
try {
    Write-Host "Iniciando o servidor do Pokémon RPG (somente localhost)..." -ForegroundColor Cyan
    & $python "servidor_teste.py"
    if ($LASTEXITCODE -ne 0) {
        throw "Servidor encerrado com código $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}
