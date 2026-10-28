# Atlas de Ankar — Etapa 10A.4.1: correção de renderização isolada

## Sintoma

Após a Etapa 10A.4, a suíte da Etapa 10A.3 passou a falhar em
`tests/test_mapa_ankar_visual.py::test_template_detalhe_aponta_para_mapa_sem_alterar_encontros`.
O teste chama a página Jinja diretamente, sem a variável `formas`, e produz
`jinja2.exceptions.UndefinedError: 'formas' is undefined`.

## Causa e correção

A rota Flask `detalhe_ankar()` já fornece `formas` corretamente em produção,
mas o teste legado não cria esse contexto. O template usa agora fallbacks
para `formas`, `encontrados_por`, `descricao_paragrafos` e `atlas_csrf` quando
faltam. O comportamento normal não muda quando os valores vêm da rota.
Sem lista de treinadores, botões de geração e modal não são exibidos.

## Instalação

Extraia o ZIP na raiz do projeto, mantendo a estrutura de diretórios e
substituindo **apenas** `templates/regiao/detalhe.html`. O novo teste e o
script de documentação são aditivos. Execute:

```powershell
python scripts/registrar_correcao_atlas_10a4_1.py
python -m pytest -q tests/test_atlas_10a4_1_template.py tests/test_mapa_ankar_visual.py tests/test_ankar_10a4.py tests/test_atlas_ankar.py tests/test_atlas_ankar_flask.py
```

As rotas Flask, planilhas, geração de Pokémon, banco e demais telas ficam
inalteradas. Nenhuma migration. Não confundir a validação Jinja isolada com
uma execução Flask completa em PostgreSQL.
