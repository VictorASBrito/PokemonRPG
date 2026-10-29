# Etapa 10C.1 — Revisão de Catálogo e Inventários de Ankar

**Estado:** ferramenta de diagnóstico preparada, sem atualização dos registros da campanha.

## Por que esta etapa vem antes das alterações

A fonte congelada de fichas (`app/seed/fichas_jogadores_ankar.json`) registra **109 entradas de inventário**, **455 unidades** e **77 grafias distintas**, entre nove personagens. Esses números descrevem **a fonte histórica**, não necessariamente o PostgreSQL atual. A documentação de outubro cita contagens diferentes depois da importação (110 entradas/456 unidades). **Não usar o JSON para sobrescrever o banco atual.**

Exemplos reais do arquivo congelado: `Poke Bolas`, `Poké bolas`, `poké bolas`, `pokebola`, `Pokebola`, `Pokéball`; `Greatball`, `GreatBall`, `great ball`, `Grande Bola`, `Bola Grande`; `Pokedex`, `pokedex`; `Antídoto`, `Antidoto`, `antidoto`; `Incubadora Comúm` e `incubadora comum`.

**Atenção:** a origem histórica registra 22 Pokédex para Juliano Lima (login `jao`); é um dado a **conferir**, não uma quantidade a corrigir automaticamente. Itens como `Colar Quebrado`, `Flor Roxa`, `Mega pedra`, `Iscas (P)/(N)` e outras peculiaridades da campanha podem ser intencionalmente distintos.

## Diagnóstico atual — somente leitura

Execute a partir da raiz, com o ambiente virtual ativado e banco configurado:

```powershell
flask --app app.py catalogo auditar-itens --todos
flask --app app.py inventario verificar
python scripts/revisar_itens_ankar_10c1.py
```

O último comando produz `relatorios/revisao_itens_ankar/`:

- `catalogo_itens.csv`: código, nome, categoria, preço, características, imagem e quantidades agregadas;
- `inventarios_por_jogador.csv`: jogador/login, personagem, item/código, quantidade e imagem;
- `possiveis_duplicatas.csv`: nomes equivalentes a **revisar**, sem alteração;
- `imagens_pendentes.csv`: itens sem URL, com arquivo local ausente ou URL inválida;
- `modelo_novos_itens.csv`: campos para especificar novos itens a cadastrar;
- `modelo_distribuicao.csv`: login, código do item e quantidade **a adicionar**, não total final;
- `resumo.json` e `LEIA_PRIMEIRO.md`.

Para extrair **somente a origem congelada**, sem Flask/PostgreSQL (não usar como inventário vigente):

```powershell
python scripts/revisar_itens_ankar_10c1.py --fonte-seed
```

Esse relatório histórico terá o catálogo vazio, pois a fonte de fichas não contém a tabela `itens` do banco, suas categorias e imagens. **Não concluir que não existem imagens no site** a partir desse modo.

## Padrão proposto — sujeito à aprovação

| Grupo | Exemplos | Observação |
|---|---|---|
| Bolas | Poké Bola, Grande Bola, Ultra Bola, Premier Ball | Manter variantes com efeitos diferentes separadas |
| Cura e suporte | Poção, Antídoto, Elixir, Cura Paralisia | Conferir efeitos, uso e preço |
| Evolução e Pokémon | Pedra de Fogo, Pedra do Sol, Mega pedra | Mega pedras podem ter efeitos/identidade específicos |
| Exploração | Lanterna, Vara de pesca, Corda, Iscas | Não unificar tipos/tamanhos diferentes |
| Alimentos | Frutas, Maçã Vermelha, Ameixas | Itens genéricos e específicos podem coexistir |
| Narrativos/únicos | Colar Quebrado, Flor Roxa, Fóssil desconhecido | Preservar como personalizados, sem fusão automática |

Cada item do catálogo deverá ter **código único e estável**, nome padronizado, categoria, descrição, flags de uso, preço em Pokédolares, efeito conforme as regras da campanha, imagem e status ativo.

## Imagens

O próprio catálogo já suporta `Item.imagem_url` e o formulário do mestre permite URL HTTPS ou upload de PNG, JPG, WEBP e GIF para `static/uploads/itens/`. Ao adicionar um item à mochila, a interface reutiliza a imagem desse cadastro. Portanto:

1. **Criar/identificar o registro único** no catálogo;
2. **Vincular uma imagem apropriada** ao registro (preferencialmente upload local para não depender de links externos);
3. Confirmar prévia e nome na tela Catálogo e no Inventário;
4. **Só então distribuir** o item aos personagens.

Não usar imagens genéricas para substituir objetos narrativos que exigem arte própria; solicitar/definir referências específicas antes de criá-las.

## Regras de segurança e consistência

- Relatórios e propostas **não** executam `UPDATE`, `DELETE`, `INSERT` ou migrations.
- **Não fundir itens sem conhecer todas as referências** (`personagem_itens`, `pokemons.item_equipado_id`, histórico e efeitos). Padronizar uma grafia exibida não é o mesmo que remover a outra linha.
- Caso haja necessidade de fusão, preparar simulação explícita, backup e operação transacional com histórico. Nunca somar em duplicidade as unidades de um mesmo registro.
- Antes de aplicar distribuições, revisar `modelo_distribuicao.csv`, validar logins/códigos existentes, impedir quantidade negativa e registrar alterações; usar os serviços oficiais `adicionar_item` ou formulário do mestre.
- O projeto usa URLs individuais `/p/<login>/` para fichas simultâneas: conferir imagens e quantidades em dois navegadores/personagens, para não regredir as sessões.
- Os CSVs em `relatorios/` trazem dados reais da campanha; **não versionar/publicar sem revisão**.

## Próxima decisão

Revisar o CSV de duplicatas e preencher a lista concreta de novos itens, respectivas categorias e imagens, destinatários e quantidades. Só então preparar um pacote de cadastro/distribuição com simulação e confirmação. Sem esse detalhamento, qualquer adição seria arbitrária.

## Arquivos nesta entrega

- `scripts/revisar_itens_ankar_10c1.py`
- `scripts/registrar_revisao_itens_10c1.py`
- `tests/test_revisao_itens_10c1.py`
- `docs/REVISAO_CATALOGO_INVENTARIO_10C1.md`

**Sem migration; nenhuma escrita no banco real.**
