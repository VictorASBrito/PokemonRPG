# Atlas visual de Ankar — Etapa 10A.2

## Objetivo e escopo

Este pacote substitui, **para fins de navegação visual**, a tentativa anterior de tratar todas as divergências das planilhas como impeditivas. Primeiro expomos a geografia da região e as tabelas de encontro no site; funções posteriores dependerão de aprovação do mestre.

- 73 rotas, 26 cidades (18 ginásios + 8 auxiliares) e 20 pontos de interesse: 119 páginas de locais.
- 352 tabelas por terreno/zona e 2.683 entradas exibidas.
- Aba adicional `REGIÃO DE ANKAR`: contexto narrativo, não é local com rota própria.
- Habitat principal/secundário, terrenos do local, descrição, duração/extensão, acessos (com links quando o destino é identificado), zonas, espécies e intervalos d100.
- `% Captura` é a **taxa de captura do Pokémon**, nunca o peso no sorteio de encontro.
- Em locais onde as zonas são lado a lado na planilha, são preservadas como zonas distintas, não fundidas.

## Instalação no projeto Flask existente

1. Extraia os arquivos do ZIP incremental **na raiz** do projeto.
2. Na raiz do projeto, com ambiente virtual ativado, execute:

   ```powershell
   python scripts/instalar_atlas_ankar.py
   python -m pytest -q tests/test_atlas_ankar.py tests/test_atlas_ankar_flask.py
   ```

3. Reinicie o Flask e abra **`/regiao/ankar`** com uma conta de **mestre**. O menu **Região** é incluído nas duas visões do mestre (normal e prévia), sem expor as tabelas de encontros aos jogadores.

O instalador só acrescenta import e registro do blueprint em `app/__init__.py` e links de menu em `templates/base.html`; também apende o histórico dos documentos, se presentes. Ele não substitui seus arquivos completos, preservando alterações locais. É idempotente.

## Dados e regeneração

O JSON `app/data/catalogo_ankar_visual.json` **já está incluído no ZIP**. O servidor **não precisa das planilhas para exibir o atlas**. As duas planilhas originais não são sobrescritas, incluídas no ZIP nem enviadas ao PostgreSQL.

Para atualizar o catálogo depois de editar as planilhas:

```powershell
python scripts/gerar_catalogo_ankar.py `
  --rotas "data\ankar\Região de Ankar - Rotas - PokéRPG.xlsx" `
  --cidades "data\ankar\Ankar - Cidades e Pontos de Interesse - PokéRPG.xlsx"
```

Esse comando lê as planilhas e substitui **apenas o JSON gerado**. Reinicie o processo Flask após a geração, pois o serviço mantém os dados em cache de leitura.

## Tratamento responsável dos dados

- Intervalos como `1-10` salvos pelo Excel como `2017-10-01` são mostrados como `1-10`. O valor serial original fica preservado em `d100_original` e `faixa_reconstituida=true`. Não é reescrita a planilha.
- Células com `x` aparecem como **Marcador x**, pois seu significado não está confirmado. Não inventar espécies.
- D100 sobrepostos, lacunas, faixas invertidas, `Random`, entradas vazias e outras particularidades são preservados. Não impor validação que esconda os dados.
- As porcentagens, independentemente de serem 100/75/20, continuam atribuídas à captura, não ao encontro.
- Alguns acessos, como “Cidade Gelo”, não possuem correspondência inequívoca na planilha: permanecem em texto, sem link inventado.
- Uma tabela de terreno não significa necessariamente um **tipo de terreno físico** presente na lista E4:H4; ambas as informações são apresentadas separadamente.

## Arquitetura e segurança

- Blueprint: `app/routes/regiao.py`, endpoints `regiao.indice_ankar`, `regiao.detalhe_ankar`.
- Serviço estático: `app/services/regiao_ankar_service.py`.
- Templates: `templates/regiao/indice.html`, `templates/regiao/detalhe.html`.
- CSS/JS isolados: `static/css/atlas-ankar.css` e `static/js/atlas-ankar.js`.
- Fonte do catálogo: `app/data/catalogo_ankar_visual.json`.
- Fonte de extração: `scripts/gerar_catalogo_ankar.py` (somente biblioteca padrão Python).
- Scripts de integração: `scripts/instalar_atlas_ankar.py`.
- Testes: `tests/test_atlas_ankar.py` (independentes do Flask), `tests/test_atlas_ankar_flask.py` (integração da instalação).

O atlas utiliza `@perfil_obrigatorio('mestre')`; **não cria acessos públicos** para encontros ainda não revelados. Não existem POST, rolagens, migrations ou novas tabelas no PostgreSQL nesta etapa.

## Próximo passo

Após o mestre validar as páginas no navegador, revisar especialmente nomes, descrição de acessos, linhas `x` e faixas d100 reconstituídas. Somente depois planejar mecanismos de escolha de habitat e sorteio de Pokémon com regras da campanha.
