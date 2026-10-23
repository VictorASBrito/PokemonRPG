param(
    [Parameter(Mandatory=$true)]
    [string]$Destino
)

$ErrorActionPreference = 'Stop'
$Origem = $PSScriptRoot
$Destino = (Resolve-Path -LiteralPath $Destino).Path

if (-not (Test-Path -LiteralPath (Join-Path $Destino 'app.py'))) {
    throw 'Pasta de destino invalida: app.py nao encontrado.'
}

# Apenas os dois arquivos da atualizacao: sem tocar em .env, uploads,
# campanhas, contas, migracoes, banco ou em outros componentes do site.
$Arquivos = @(
    'static/css/inventario.css',
    'app/services/inventario_apresentacao.py'
)

$Backup = Join-Path $Destino ('backup_inventario_UI2_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
foreach ($Relativo in $Arquivos) {
    $RelativoWindows = $Relativo.Replace('/', '\')
    $ArquivoOrigem = Join-Path $Origem $RelativoWindows
    $ArquivoDestino = Join-Path $Destino $RelativoWindows

    if (-not (Test-Path -LiteralPath $ArquivoOrigem)) {
        throw "Arquivo nao encontrado no pacote: $Relativo"
    }
    if (Test-Path -LiteralPath $ArquivoDestino) {
        $Copia = Join-Path $Backup $RelativoWindows
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Copia) | Out-Null
        Copy-Item -LiteralPath $ArquivoDestino -Destination $Copia -Force
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $ArquivoDestino) | Out-Null
    Copy-Item -LiteralPath $ArquivoOrigem -Destination $ArquivoDestino -Force
}

Write-Host 'Alinhamento do inventario UI2 atualizado.' -ForegroundColor Green
if (Test-Path -LiteralPath $Backup) {
    Write-Host "Backup anterior: $Backup" -ForegroundColor Cyan
}
Write-Host 'Banco, .env, dados e imagens nao foram alterados.' -ForegroundColor Cyan
Write-Host 'Reinicie o servidor e pressione Ctrl+F5 no navegador.' -ForegroundColor Yellow
