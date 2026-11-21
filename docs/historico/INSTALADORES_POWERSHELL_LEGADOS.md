# Instaladores PowerShell históricos

> Estes instaladores por cópia de arquivos foram criados antes da estrutura atual em Git. **Não são o procedimento recomendado de atualização** e não devem ser executados sobre a versão mais recente. O conteúdo foi preservado aqui por referência; a origem também segue disponível no histórico Git.

## APLICAR_PADRONIZACAO_UI.ps1

~~~powershell
param(
    [Parameter(Mandatory = $true)]
    [string]$Destino
)

$ErrorActionPreference = 'Stop'
$Origem = $PSScriptRoot
$Destino = [System.IO.Path]::GetFullPath($Destino)

if (-not (Test-Path -LiteralPath (Join-Path $Destino 'app.py'))) {
    throw "Destino invalido: nao foi encontrado app.py em $Destino"
}

# Copia apenas arquivos alterados nesta etapa. Nao mexe em .env, dados,
# migrations, static/uploads, imagens dos jogadores ou arquivos do PostgreSQL.
$Arquivos = @(
    'templates/base.html',
    'templates/conta/trocar_senha.html',
    'static/css/sistema-ui.css',
    'app/services/inventario_apresentacao.py'
)

$TemplateRoot = Join-Path $Origem 'templates'
$OutrosTemplates = Get-ChildItem -LiteralPath $TemplateRoot -Recurse -File -Filter '*.html' |
    ForEach-Object { 'templates/' + $_.FullName.Substring($TemplateRoot.Length).TrimStart([char]92, [char]47).Replace([char]92, [char]47) }
$Arquivos = @($Arquivos + $OutrosTemplates | Sort-Object -Unique)
$Carimbo = Get-Date -Format 'yyyyMMdd_HHmmss'
$Backup = Join-Path $Destino ("backups\padronizacao_ui_$Carimbo")
$Copiados = 0

foreach ($Relativo in $Arquivos) {
    $RelativoWindows = $Relativo.Replace([char]47, [char]92)
    $Fonte = Join-Path $Origem $RelativoWindows
    $Alvo = Join-Path $Destino $RelativoWindows
    if (-not (Test-Path -LiteralPath $Fonte)) { continue }

    if (Test-Path -LiteralPath $Alvo) {
        $Salvamento = Join-Path $Backup $RelativoWindows
        $PastaBackup = Split-Path $Salvamento -Parent
        New-Item -ItemType Directory -Force -Path $PastaBackup | Out-Null
        Copy-Item -LiteralPath $Alvo -Destination $Salvamento -Force
    }
    New-Item -ItemType Directory -Force -Path (Split-Path $Alvo -Parent) | Out-Null
    Copy-Item -LiteralPath $Fonte -Destination $Alvo -Force
    $Copiados++
}

Write-Host "Padronizacao visual aplicada: $Copiados arquivo(s)." -ForegroundColor Green
Write-Host "Backup dos arquivos anteriores em: $Backup"
Write-Host "Reinicie o servidor e pressione Ctrl+F5 no navegador."
Write-Host "Nao e necessario executar flask db upgrade para esta etapa."
~~~

## INSTALAR_ALINHAMENTO_INVENTARIO_UI2.ps1

~~~powershell
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
~~~

## INSTALAR_INVENTARIO_BW6.ps1

~~~powershell
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
~~~

