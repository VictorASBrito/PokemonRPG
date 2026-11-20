# Auditoria preliminar das formas regionais — fonte PKMRPG 2.5

Data: 20/11/2026. Fonte consultada: `data/catalogo/pokemons.json` do repositório, carregada somente para leitura. **Não foi feita inspeção do PostgreSQL de produção.**

## Resumo da fonte

- 1.064 formas no catálogo original; 898 espécies distintas da Pokédex nacional.
- 38 registros classificados como **regionais**, conforme `categoria_forma` do importador; os demais são 871 normais, 50 Mega e 105 alternativas.
- Para as 38 regionais foi encontrada uma forma de referência no mesmo grupo de espécie.
- 38/38 diferem nos tipos e 22/38 diferem em pelo menos um atributo base, de acordo com os campos da própria fonte (não necessariamente com os jogos oficiais).
- No caso de Darmanitan (Galar Normal), a referência é Darmanitan (Normal); para (Galar Zen), é Darmanitan (Zen).
- São diferenças de ficha; **não são regras de evolução**. Não inferir, por comparação de nomes, que uma variante regional evolui de/para a forma comum.

## Comparação de tipos e atributos

Diferenças são calculadas como **regional menos referência**. Sem diferenças numéricas indica que os seis atributos base são iguais, não que as formas tenham o mesmo tipo, golpes ou requisitos.

| Forma regional | Referência da mesma espécie | Tipos: referência → regional | Diferenças nos atributos base |
| --- | --- | --- | --- |
| Rattata (Alola) | Rattata | Normal → Normal/Noturno | Sem diferenças numéricas |
| Raticate (Alola) | Raticate | Normal → Normal/Noturno | PV +15, Atq -1, Def +1, Atq.Esp -1, Def.Esp +1, Vel -2 |
| Raichu (Alola) | Raichu | Elétrico → Elétrico/Psíquico | Atq -1 |
| Sandshrew (Alola) | Sandshrew | Terra → Gelo/Metal | Def +1, Atq.Esp -1 |
| Sandslash (Alola) | Sandslash | Terra → Gelo/Metal | Def +1, Atq.Esp -2, Def.Esp +1 |
| Vulpix (Alola) | Vulpix | Fogo → Gelo | Sem diferenças numéricas |
| Ninetales (Alola) | Ninetales | Fogo → Fada/Gelo | Atq -1, Vel +1 |
| Diglett (Alola) | Diglett | Terra → Metal/Terra | Def +1 |
| Dugtrio (Alola) | Dugtrio | Terra → Metal/Terra | Def +1, Vel -1 |
| Meowth (Alola) | Meowth | Normal → Noturno | Atq -1, Atq.Esp +1 |
| Meowth (Galar) | Meowth | Normal → Metal | PV +8, Atq +2, Def +2, Vel -5 |
| Persian (Alola) | Persian | Normal → Noturno | Atq -1, Atq.Esp +1 |
| Geodude (Alola) | Geodude | Pedra/Terra → Elétrico/Pedra | Sem diferenças numéricas |
| Graveler (Alola) | Graveler | Pedra/Terra → Elétrico/Pedra | Sem diferenças numéricas |
| Golem (Alola) | Golem | Pedra/Terra → Elétrico/Pedra | Sem diferenças numéricas |
| Ponyta (Galar) | Ponyta | Fogo → Psíquico | Sem diferenças numéricas |
| Rapidash (Galar) | Rapidash | Fogo → Fada/Psíquico | Sem diferenças numéricas |
| Slowpoke (Galar) | Slowpoke | Água/Psíquico → Psíquico | Sem diferenças numéricas |
| Slowbro (Galar) | Slowbro | Água/Psíquico → Psíquico/Veneno | Atq +3, Def -2, Def.Esp -1 |
| Farfetch'd (Galar) | Farfetch'd | Normal/Voador → Lutador | Vel -1 |
| Grimer (Alola) | Grimer | Veneno → Noturno/Veneno | Sem diferenças numéricas |
| Muk (Alola) | Muk | Veneno → Noturno/Veneno | Sem diferenças numéricas |
| Exeggutor (Alola) | Exeggutor | Grama/Psíquico → Dragão/Grama | Atq +1, Vel -1 |
| Marowak (Alola) | Marowak | Terra → Fantasma/Fogo | Sem diferenças numéricas |
| Weezing (Galar) | Weezing | Veneno → Fada/Veneno | Sem diferenças numéricas |
| Mr. Mime (Galar) | Mr. Mime | Fada/Psíquico → Gelo/Psíquico | PV +8, Atq +2, Atq.Esp -1, Def.Esp -3, Vel +1 |
| Articuno (Galar) | Articuno | Gelo/Voador → Psíquico/Voador | Def -2, Atq.Esp +3, Def.Esp -2, Vel +1 |
| Zapdos (Galar) | Zapdos | Elétrico/Voador → Lutador/Voador | Atq +3, Def +1, Atq.Esp -4 |
| Moltres (Galar) | Moltres | Fogo/Voador → Noturno/Voador | Atq -2, Atq.Esp -2, Def.Esp +4 |
| Slowking (Galar) | Slowking | Água/Psíquico → Psíquico/Veneno | Atq -1, Atq.Esp +1 |
| Corsola (Galar) | Corsola | Água/Pedra → Fantasma | PV -4, Def +1, Def.Esp +1 |
| Zigzagoon (Galar) | Zigzagoon | Normal → Normal/Noturno | Sem diferenças numéricas |
| Linoone (Galar) | Linoone | Normal → Normal/Noturno | Sem diferenças numéricas |
| Darumaka (Galar) | Darumaka | Fogo → Gelo | Sem diferenças numéricas |
| Darmanitan (Galar Normal) | Darmanitan (Normal) | Fogo → Gelo | Sem diferenças numéricas |
| Darmanitan (Galar Zen) | Darmanitan (Zen) | Fogo/Psíquico → Fogo/Gelo | Atq +13, Def -5, Atq.Esp -11, Def.Esp -5, Vel +8 |
| Yamask (Galar) | Yamask | Fantasma → Fantasma/Terra | Atq +2, Atq.Esp -2 |
| Stunfisk (Galar) | Stunfisk | Elétrico/Terra → Metal/Terra | Atq +1, Def +2, Atq.Esp -1, Def.Esp -2 |

## Limites e decisões pendentes

1. Este relatório classifica e compara registros **da fonte original**, não os dados atualizados/administrados no PostgreSQL.
2. Vínculos `evolucoes_pokemon` não foram examinados no banco real. Cada caminho normal/regional deverá ser cadastrado explicitamente; não conectar automaticamente duas variantes da mesma espécie.
3. Para Morpeko, formas alternativas, formas Galar Zen e demais transições reversíveis, definir relacionamento separado de evolução permanente.
4. Para formas personalizadas criadas pelo mestre, validar cada transição em sua configuração, sem impor regras de outra espécie.
5. Confirmar tipos, atributos, restrições de forma e caminhos de evolução com o mestre antes de preencher vínculos ou habilitar botões.
