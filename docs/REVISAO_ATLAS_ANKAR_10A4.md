# Etapa 10A.4 — Ajustes de usabilidade do Atlas de Ankar (28/10/2026)

## Objetivo

Preservar a UI aprovada nas telas de jogadores e mestre e melhorar somente o Atlas. A atualização pressupõe a etapa 10A.3 instalada. Não modifica o banco nem cria migration.

## Alterações de interface

- O mapa parte no tamanho **encaixar inteiro** no espaço à esquerda. Os filtros (Rotas, Cidades e Pontos), seleção direta de local, ficha e legenda estão na coluna à direita no desktop. No celular e tablet, ficam abaixo do mapa. A imagem original permanece intacta; zoom manual continua possível.
- A descrição das cidades, pontos de interesse e rotas mostra uma prévia reduzida. A versão integral fica sob *Conhecer a história e a descrição completa…*. O conteúdo original é preservado e separado visualmente em parágrafos.
- Tabelas de encontros agora são grades de cards: arte do **catálogo Pokémon já existente**, nome, intervalo d100 e % Captura; a taxa de captura não é tratada como peso.
- `x` é apresentado como **X vermelho / Sem encontro**, conforme a definição dada pelo mestre. Entradas sem espécie, `Random` e espécies não encontradas no catálogo continuam visíveis, porém sem geração automática.

## Integração com capturáveis

1. No detalhe, o mestre clica em um card com espécie encontrada no catálogo.
2. Uma janela pergunta: **“Deseja gerar este Pokémon na tela de capturáveis?”**.
3. Após **Sim, continuar**, o mestre escolhe o treinador que encontrou o Pokémon.
4. O POST `/regiao/ankar/<slug>/gerar-encontro` verifica perfil mestre, token CSRF e índices exatos do encontro a partir do JSON, e então chama **`criar_capturavel_campo`**, serviço já existente.
5. Em caso de sucesso, redireciona para `/mestre/capturaveis`. O serviço atual controla capacidade máxima (15), espécie válida, treinador, natureza, sexo, Shiny e histórico. O d100 é **somente informativo**; não é rolado aqui. A atribuição posterior à Box permanece manual.

**Segurança:** nenhuma confiança em um nome de Pokémon enviado pelo navegador. O servidor reconstrói o encontro pelos índices de zona/tabela/entrada; `x` e `Random` não podem ser usados para criar capturáveis. Um POST sem CSRF válido não cria registros. A rota é exclusiva do mestre, seguindo o controle já existente.

## Arquivos incrementais

- `app/routes/regiao.py`
- `app/services/regiao_ankar_service.py`
- `templates/regiao/indice.html`
- `templates/regiao/detalhe.html`
- `static/css/atlas-ankar.css`
- `static/js/atlas-ankar.js`
- `tests/test_ankar_10a4.py`
- `scripts/registrar_atlas_10a4.py`
- `docs/REVISAO_ATLAS_ANKAR_10A4.md`

Não substitui `app/__init__.py`, `templates/base.html`, planilhas, mapa, JSON de locais, arte de Pokémon, dados do usuário ou arquivos `.env`.

## Verificação local

```powershell
python scripts/registrar_atlas_10a4.py
python -m pytest -q tests/test_ankar_10a4.py tests/test_mapa_ankar_visual.py tests/test_atlas_ankar.py tests/test_atlas_ankar_flask.py
```

Depois reinicie o Flask e teste em `/regiao/ankar` e em uma rota com Pokémon que esteja cadastrado, com perfil mestre. Confirme a seleção, o jogador encontrado, o limite de capturáveis e a ficha no painel.

## Limites / próximas etapas

- O atlas **não** altera os intervalos d100 nem captura Pokémon automaticamente na Box.
- Os sprites são buscados **somente** no catálogo Pokémon já cadastrado. Se o nome da planilha não corresponder ao nome de uma forma ativa, a geração do card ficará desabilitada até uma vinculação explícita.
- Os testes Flask + banco deverão rodar no ambiente local; não assumir que passaram só pela verificação sintática. Revisar também os painéis do site em navegador real antes de considerar uma remodelagem global.
