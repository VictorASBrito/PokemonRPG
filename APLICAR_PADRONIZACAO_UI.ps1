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
