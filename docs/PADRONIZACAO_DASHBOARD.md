# Padronização de dimensões do dashboard

Esta atualização trata apenas do **dashboard do jogador**. Nenhuma tabela, rota ou regra de Pokémon foi alterada.

- A grade padrão continua com três cartões por linha no desktop, em duas fileiras para os seis espaços.
- Retratos têm dimensões previsíveis e não invadem os nomes ou barras de PV.
- Todos os cartões da mesma fileira possuem altura alinhada, inclusive vagas vazias. No desktop amplo, as duas fileiras usam a mesma altura calculada em função da altura da janela.
- Barras de PV ocupam toda a largura disponível dentro do bloco.
- Atributos base mantêm seis células do mesmo tamanho (três colunas por duas linhas).
- Golpes ficam em linhas compactas sem provocar cartões mais altos; nomes longos são abreviados visualmente, mas o valor completo permanece no título ao passar o mouse e na ficha expandida.
- Os atributos do treinador também mantêm células de altura coerente.
- Breakpoints menores voltam a permitir altura automática para não cortar dados.
- O modo expandido (incluindo Recolher/Esc, troca pela lateral e layout sem scroll no desktop) foi preservado.

## Instalação

Preserve os seus arquivos `.env`, `data/` e `static/uploads/` ao substituir o projeto. Não há migration nova.

```powershell
.\.venv\Scripts\Activate.ps1
python app.py
```

Para validação no seu ambiente de desenvolvimento:

```powershell
pytest -q
```

## Slots de golpes e alinhamento até a base da página

- Todos os Pokémon possuem **exatamente quatro slots visíveis** para golpes, mesmo que nenhum esteja cadastrado. Cada posição sem golpe exibe **Sem golpe definido**.
- O estado expandido também apresenta quatro slots. Nenhum golpe fictício é criado no banco; os espaços são apenas placeholders visuais no template.
- No desktop (acima de 1180 px), as duas fileiras do dashboard ocupam a área útil até a base da coluna do treinador, com cartões da mesma altura, inclusive as vagas vazias.
- As seis células de atributos ocupam duas linhas, e os quatro slots de golpes ocupam quatro linhas de mesma altura total. Isso mantém topo e rodapé alinhados.
- Em telas menores a altura volta a ser automática para preservar a legibilidade; não são cortados os golpes.
- A visualização ampliada, o editor de Pokémon e as regras de combate permanecem inalterados. Não há migration.

Teste específico:

```powershell
pytest -q tests/test_dashboard_slots.py
```
