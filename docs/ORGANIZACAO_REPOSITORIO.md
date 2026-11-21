# Organização do repositório e política de arquivos

**Revisão:** 21/11/2026. Inventário da `main` antes desta limpeza: **2.762 arquivos**, cerca de **2.258 arquivos em `static/`**, principalmente sprites e imagens. **Não interpretar quantidade alta de sprites como lixo.**

## Mantidos sem modificação

- `migrations/versions/`: cadeia Alembic requerida para instalações existentes.
- `data/ankar/`, `data/catalogo/`, `data/referencias/`, `app/data/`: fontes de região, Pokédex e regras.
- `static/img/`, `static/uploads/`: sprites e uploads; uso/atribuição pode ocorrer pelo banco, portanto exclusão por inspeção estática não é segura.
- `tests/fixtures_*/`, `tests/`: fixtures e contratos antigos que ainda são executados.
- `scripts/` e `servidor_teste.py`: importadores, verificadores, túnel de teste; nenhum foi eliminado indiscriminadamente.
- Relatórios de auditoria com conteúdo ainda potencialmente útil, como `auditoria-pokedex.json`: permanecem disponíveis até revisão funcional específica.

## Limpeza realizada

- **37 arquivos de backup** (`.bak`, `.bak-*`, `.antes_*.bak`, arquivos sob `relatorios/backups_ui_*`) removidos apenas da árvore de trabalho Git; o histórico de commits permite recuperar versões anteriores.
- **`static/css/refinamento.css`** removido após migração de regras efetivas para `sistema-ui.css`; seletores de cabeçalho contraditórios eliminados.
- **16 textos antigos na raiz** consolidados em `docs/historico/INSTRUCOES_LEGADAS_10A_10B.md` e `README_ETAPAS_LEGADAS_10C_10D.md`.
- **3 instaladores PowerShell de cópia manual** arquivados em `docs/historico/INSTALADORES_POWERSHELL_LEGADOS.md`; não são recomendados para a aplicação versionada.
- `README.md` canônico na raiz para execução, arquitetura e links.
- `.gitignore` ampliado para evitar novas cópias de backup, temporários e arquivos locais gerados.

Nenhuma alteração nesta limpeza moveu arquivos do PostgreSQL, dados de personagens, fixtures, imagens ou migrações. O histórico Git permanece como referência para recuperar backups antigos sem mantê-los na pasta ativa.

## Convenção para novos arquivos

- Documentação atual de módulos: `docs/ETAPA_*.md`; preferir atualizar a mesma área em vez de `README_10XYZ.txt` na raiz.
- Histórico que não representa procedimento atual: `docs/historico/`.
- Scripts mantidos por testes: continuar em `scripts/`; mover exige atualizar todos os imports/caminhos dos testes.
- Temporários, logs, dumps e snapshots: ignorar no Git, guardar fora do repositório ou em backup privado.
- Novos CSS/JS: diretórios `static/css` e `static/js`, nome de componente/página em vez de sufixos de “correção final”.
- Migrations nunca devem ser usadas como arquivos descartáveis.

## Futuras oportunidades (não incluídas por segurança)

- Revisar `auditoria-pokedex.json` e `static/img/pokemon-hd/historico-sincronizacao.jsonl` para decidir se logs/relatórios gerados podem sair da pasta pública.
- Reorganizar `scripts/` por finalidade **após** atualizar comandos documentados e testes de instalação legados.
- Separar o serviço de rotas do catálogo em Blueprints menores somente após testes de regressão de permissões.
- Consolidar CSSs de módulos legados gradualmente, verificando contraste, responsividade e animações, sem substituir de uma vez as mais de 2.000 imagens.

## Como conferir

```bash
python -m pytest -q tests/test_contrato_visual_repositorio.py tests/test_sistema_ui.py tests/test_refinamento_frontend.py
python -m pytest -q
```

Em caso de regressão, consultar o PR de limpeza, identificar o arquivo e restaurar pelo histórico Git — **não reinstalar PowerShell legado**.
