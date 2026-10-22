# Execute em um SEGUNDO terminal, com o servidor de teste ativo no primeiro.
# Nao utiliza autenticacao por e-mail Cloudflare.
$ErrorActionPreference = "Stop"

$comando = Get-Command "cloudflared" -ErrorAction SilentlyContinue
if ($comando) {
    $executavel = $comando.Source
}
else {
    $candidato = Join-Path (Split-Path -Parent $PSScriptRoot) "cloudflared.exe"
    if (Test-Path -LiteralPath $candidato) {
        $executavel = $candidato
    }
    else {
        throw "cloudflared não encontrado. Instale pelo site oficial https://developers.cloudflare.com/tunnel/downloads/ e execute cloudflared --version."
    }
}

try {
    Invoke-WebRequest -Uri "http://127.0.0.1:5000/login" -TimeoutSec 4 -UseBasicParsing | Out-Null
}
catch {
    throw "Não encontrei o servidor em http://127.0.0.1:5000/login. Inicie scripts/1_servidor_teste.ps1 em outro terminal primeiro."
}

Write-Host "Iniciando tunel publico HTTPS do Pokemon RPG..." -ForegroundColor Cyan
Write-Host "Compartilhe a URL *.trycloudflare.com somente no grupo do RPG." -ForegroundColor Yellow
Write-Host "AVISO: qualquer pessoa com a URL podera abrir a pagina de login." -ForegroundColor Yellow
Write-Host "Ctrl+C encerra o tunel e invalida o link." -ForegroundColor Yellow
& $executavel tunnel --url http://127.0.0.1:5000
if ($LASTEXITCODE -ne 0) {
    throw "cloudflared encerrou com codigo $LASTEXITCODE."
}
