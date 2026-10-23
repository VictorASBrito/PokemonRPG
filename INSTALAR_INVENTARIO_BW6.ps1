param(
    [Parameter(Mandatory=$true)]
    [string]$Destino
)

$ErrorActionPreference = "Stop"
$Origem = $PSScriptRoot
$Destino = (Resolve-Path -LiteralPath $Destino).Path

if (-not (Test-Path -LiteralPath (Join-Path $Destino "app.py"))) {
    throw "A pasta informada nao contem app.py. Confira o caminho do projeto PokemonRPG."
}

$Arquivos = @(
    "templates/jogador/inventario.html",
    "static/css/inventario.css",
    "static/js/inventario.js",
    "app/services/inventario_apresentacao.py",
    "static/img/inventory/icon-cura-hq.png",
    "static/img/inventory/icon-pokebolas-hq.png",
    "static/img/inventory/icon-frutas-hq.png",
    "static/img/inventory/icon-chave-hq.png",
    "static/img/inventory/icon-avulsos-hq.png",
    "static/img/inventory/bag-cura.png",
    "static/img/inventory/bag-pokebolas.png",
    "static/img/inventory/bag-frutas.png",
    "static/img/inventory/bag-chave.png",
    "static/img/inventory/bag-avulsos.png"
)

$Backup = Join-Path $Destino ("backup_inventario_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
$Substituidos = 0
foreach ($Relativo in $Arquivos) {
    $RelativoWindows = $Relativo.Replace('/', '\')
    $ArquivoOrigem = Join-Path $Origem $RelativoWindows
    $ArquivoDestino = Join-Path $Destino $RelativoWindows
    if (-not (Test-Path -LiteralPath $ArquivoOrigem)) {
        throw "Arquivo ausente no pacote: $Relativo"
    }
    $PastaDestino = Split-Path -Parent $ArquivoDestino
    New-Item -ItemType Directory -Force -Path $PastaDestino | Out-Null
    if (Test-Path -LiteralPath $ArquivoDestino) {
        $ArquivoBackup = Join-Path $Backup $RelativoWindows
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $ArquivoBackup) | Out-Null
        Copy-Item -LiteralPath $ArquivoDestino -Destination $ArquivoBackup -Force
    }
    Copy-Item -LiteralPath $ArquivoOrigem -Destination $ArquivoDestino -Force
    $Substituidos++
}

Write-Host "Inventario BW6 instalado: $Substituidos arquivos." -ForegroundColor Green
if (Test-Path -LiteralPath $Backup) {
    Write-Host "Backup dos arquivos anteriores: $Backup" -ForegroundColor Cyan
}
Write-Host "Seus dados PostgreSQL, .env, data/ e static/uploads/ nao foram alterados." -ForegroundColor Cyan
Write-Host "Reinicie o servidor e pressione Ctrl+F5 no navegador." -ForegroundColor Yellow
