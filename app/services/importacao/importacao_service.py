from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.extensions import db
from app.services.importacao.campanha_importer import CampanhaImporter
from app.services.importacao.catalogo_importer import CatalogoImporter
from app.services.importacao.validacao_importer import ValidacaoImportacao


@dataclass(slots=True)
class ResumoImportacao:
    modo: str
    inicio: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    fim: str | None = None
    criados: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    atualizados: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    removidos: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    avisos: list[str] = field(default_factory=list)
    erros: list[str] = field(default_factory=list)
    validacao: dict[str, Any] | None = None
    relatorio: str | None = None

    def criado(self, entidade: str) -> None:
        self.criados[entidade] += 1

    def atualizado(self, entidade: str) -> None:
        self.atualizados[entidade] += 1

    def removido(self, entidade: str) -> None:
        self.removidos[entidade] += 1

    def aviso(self, mensagem: str) -> None:
        self.avisos.append(mensagem)

    def erro(self, mensagem: str) -> None:
        self.erros.append(mensagem)

    def finalizar(self) -> None:
        self.fim = datetime.now(timezone.utc).isoformat()

    def para_dict(self) -> dict[str, Any]:
        dados = asdict(self)
        dados["criados"] = dict(self.criados)
        dados["atualizados"] = dict(self.atualizados)
        dados["removidos"] = dict(self.removidos)
        dados["sucesso"] = not self.erros
        return dados


class ImportacaoService:
    def __init__(self, fontes, *, raiz_projeto: Path) -> None:
        self.fontes = fontes
        self.raiz_projeto = Path(raiz_projeto)

    def importar(self, *, dry_run: bool = False) -> ResumoImportacao:
        resumo = ResumoImportacao(modo="simulacao" if dry_run else "importacao")
        resumo.avisos.extend(self.fontes.avisos)

        try:
            catalogo = CatalogoImporter(self.fontes, resumo)
            catalogo.executar()
            CampanhaImporter(self.fontes, catalogo, resumo).executar()
            db.session.flush()

            if resumo.erros:
                raise RuntimeError("A importação encontrou erros impeditivos.")

            if dry_run:
                db.session.rollback()
            else:
                db.session.commit()
                resumo.validacao = ValidacaoImportacao(self.fontes).executar()
        except Exception as exc:
            db.session.rollback()
            if str(exc) not in resumo.erros:
                resumo.erro(str(exc))
        finally:
            resumo.finalizar()
            resumo.relatorio = str(self._salvar_relatorio(resumo))

        return resumo

    def validar(self) -> dict[str, Any]:
        resultado = ValidacaoImportacao(self.fontes).executar()
        pasta = self.raiz_projeto / "logs"
        pasta.mkdir(parents=True, exist_ok=True)
        horario = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        arquivo = pasta / f"validacao_importacao_{horario}.json"
        arquivo.write_text(
            json.dumps(resultado, ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        resultado["relatorio"] = str(arquivo)
        return resultado

    def _salvar_relatorio(self, resumo: ResumoImportacao) -> Path:
        pasta = self.raiz_projeto / "logs"
        pasta.mkdir(parents=True, exist_ok=True)
        horario = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        arquivo = pasta / f"importacao_{resumo.modo}_{horario}.json"
        arquivo.write_text(
            json.dumps(resumo.para_dict(), ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        return arquivo
