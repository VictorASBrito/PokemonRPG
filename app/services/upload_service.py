from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
import uuid

from flask import current_app
from sqlalchemy import func, or_, select
from werkzeug.datastructures import FileStorage

from app.extensions import db


EXTENSOES_IMAGEM = {
    "png": ".png",
    "jpeg": ".jpg",
    "gif": ".gif",
    "webp": ".webp",
}


class ErroUploadImagem(ValueError):
    """Erro de validação de uma imagem enviada pelo usuário."""


@dataclass(frozen=True)
class ImagemPreparada:
    url: str | None
    upload_novo: str | None = None
    url_anterior_substituida: str | None = None


def _limite_bytes() -> int:
    return int(current_app.config.get("UPLOAD_IMAGEM_MAX_BYTES", 8 * 1024 * 1024))


def _diretorio_uploads() -> Path:
    configurado = current_app.config.get("UPLOAD_IMAGENS_DIR")
    if configurado:
        return Path(configurado)
    return Path(current_app.static_folder or "static") / "uploads"


def _prefixo_url_uploads() -> str:
    prefixo_static = (current_app.static_url_path or "/static").rstrip("/")
    return f"{prefixo_static}/uploads/"


def _detectar_formato(conteudo: bytes) -> str | None:
    if conteudo.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if conteudo.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if conteudo.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if len(conteudo) >= 12 and conteudo[:4] == b"RIFF" and conteudo[8:12] == b"WEBP":
        return "webp"
    return None


def normalizar_url_imagem(valor: object) -> str | None:
    url = str(valor or "").strip()
    if not url:
        return None
    if len(url) > 500:
        raise ErroUploadImagem("A URL da imagem excede o limite de 500 caracteres.")

    prefixo_static = (current_app.static_url_path or "/static").rstrip("/") + "/"
    if url.startswith(prefixo_static):
        return url

    analisada = urlparse(url)
    if analisada.scheme in {"http", "https"} and analisada.netloc:
        return url
    raise ErroUploadImagem("Use uma URL http/https válida ou envie um arquivo de imagem.")


def salvar_imagem_upload(arquivo: FileStorage | None, *, subpasta: str) -> str | None:
    if arquivo is None or not arquivo.filename:
        return None

    limite = _limite_bytes()
    conteudo = arquivo.stream.read(limite + 1)
    if len(conteudo) > limite:
        limite_mb = max(1, limite // (1024 * 1024))
        raise ErroUploadImagem(f"A imagem deve ter no máximo {limite_mb} MB.")
    if not conteudo:
        raise ErroUploadImagem("O arquivo de imagem está vazio.")

    formato = _detectar_formato(conteudo)
    if formato is None:
        raise ErroUploadImagem("Formato não suportado. Envie PNG, JPG/JPEG, WEBP ou GIF.")

    pasta_segura = "".join(c for c in subpasta.lower() if c.isalnum() or c in {"-", "_"})
    if not pasta_segura:
        raise ErroUploadImagem("Destino de upload inválido.")

    diretorio = _diretorio_uploads() / pasta_segura
    nome = f"{uuid.uuid4().hex}{EXTENSOES_IMAGEM[formato]}"
    destino = diretorio / nome
    try:
        diretorio.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(conteudo)
    except OSError as erro:
        raise ErroUploadImagem(
            "Não foi possível gravar a imagem no diretório de uploads."
        ) from erro

    prefixo = _prefixo_url_uploads()
    return f"{prefixo}{pasta_segura}/{nome}"


def preparar_imagem_formulario(
    *,
    arquivo: FileStorage | None,
    url_informada: object,
    remover: bool,
    subpasta: str,
    url_atual: str | None = None,
) -> ImagemPreparada:
    upload_novo = salvar_imagem_upload(arquivo, subpasta=subpasta)
    if upload_novo:
        nova_url = upload_novo
    elif remover:
        nova_url = None
    else:
        nova_url = normalizar_url_imagem(url_informada)

    anterior = url_atual if url_atual and url_atual != nova_url else None
    return ImagemPreparada(
        url=nova_url,
        upload_novo=upload_novo,
        url_anterior_substituida=anterior,
    )


def caminho_imagem_local(url: str | None) -> Path | None:
    if not url:
        return None
    prefixo = _prefixo_url_uploads()
    if not url.startswith(prefixo):
        return None
    relativo = url[len(prefixo):].split("?", 1)[0].split("#", 1)[0]
    if not relativo:
        return None

    base = _diretorio_uploads().resolve()
    destino = (base / relativo).resolve()
    try:
        destino.relative_to(base)
    except ValueError:
        return None
    return destino


def contar_referencias_imagem(url: str | None) -> int:
    if not url:
        return 0
    # Imports locais evitam ciclos entre os serviços e os modelos.
    from app.models.db.inventory import Insignia, Item
    from app.models.db.pokemon_catalog import FormaPokemon, TipoPokemon

    total = 0
    total += int(db.session.scalar(select(func.count(Item.id)).where(Item.imagem_url == url)) or 0)
    total += int(
        db.session.scalar(
            select(func.count(FormaPokemon.id)).where(
                or_(FormaPokemon.imagem_url == url, FormaPokemon.imagem_shiny_url == url)
            )
        )
        or 0
    )
    total += int(db.session.scalar(select(func.count(Insignia.id)).where(Insignia.imagem_url == url)) or 0)
    total += int(db.session.scalar(select(func.count(TipoPokemon.id)).where(TipoPokemon.icone_url == url)) or 0)
    return total


def excluir_imagem_local(url: str | None, *, somente_se_orfa: bool = True) -> bool:
    caminho = caminho_imagem_local(url)
    if caminho is None or not caminho.is_file():
        return False
    if somente_se_orfa and contar_referencias_imagem(url) > 0:
        return False
    try:
        caminho.unlink(missing_ok=True)
    except OSError:
        current_app.logger.exception("Falha ao remover upload local: %s", caminho)
        return False
    return True


def listar_arquivos_upload() -> list[Path]:
    base = _diretorio_uploads()
    if not base.exists():
        return []
    return sorted(
        caminho
        for caminho in base.rglob("*")
        if caminho.is_file() and caminho.name != ".gitkeep"
    )


def url_de_arquivo_local(caminho: Path) -> str | None:
    base = _diretorio_uploads().resolve()
    try:
        relativo = caminho.resolve().relative_to(base)
    except ValueError:
        return None
    return f"{_prefixo_url_uploads()}{relativo.as_posix()}"
