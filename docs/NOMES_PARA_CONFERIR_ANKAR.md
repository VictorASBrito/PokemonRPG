# Nomes de Pokémon que exigem conferência com o PostgreSQL

**Este é um levantamento de candidatos, não uma lista confirmada de nomes ausentes.** O catálogo do site utiliza correspondência pelo nome; o PostgreSQL local não está acessível nesta análise.

Foram encontrados **25 nomes de formas regionais/alternativas** com sufixos `-A`, `-G` ou letras entre parênteses. Outros **8 nomes com grafia especial** também merecem revisão pontual.

| Nome na planilha | Ocorrências | Rotas/cidades/pontos encontrados |
|---|---:|---|
| Corsola-G | 7 | ROTA 13, ROTA 14, ROTA 4 |
| Darumaka-G | 2 | ROTA 20, ROTA 72 |
| Diglett-A | 10 | CAVERNA CIRCULAR, CAVERNA MAGNÉTICA, CRATERA HEATRAN, MONTE APAGADO, ROTA 45 |
| Farfetch'd | 3 | ROTA 15, ROTA 6, ROTA 62 |
| Farfetch'd-G | 4 | ROTA 33, ROTA 34, ROTA 61 |
| Flabébé | 6 | CIDADE GINÁSIO 05 - LUFAY, ILHA DOS NAMORADOS, ILHAS DOS QUATRO, ROTA 5, ROTA 6 |
| Geodude-A | 5 | CAVERNA MAGNÉTICA, RIO DE AREIA, ROTA 16, ROTA 39, ROTA 45 |
| Graveler-A | 3 | CAVERNA MAGNÉTICA, RIO DE AREIA, ROTA 16 |
| Grimer-A | 13 | CIDADE AUXILIAR 01 - LIGHTMOR, CIDADE GINÁSIO 01 - YREZON, CIDADE GINÁSIO 02 - FINNALGA, CIDADE GINÁSIO 03 - DIANELT, ILHA DOS NAMORADOS |
| Hakamo-o | 1 | ROTA 73 |
| Jangmo-o | 2 | ROTA 12, ROTA 73 |
| Linoone-G | 1 | ROTA 48 |
| Meowth-A | 9 | CIDADE AUXILIAR 06 - KATTO, CIDADE GINÁSIO 02 - FINNALGA, CIDADE GINÁSIO 06 - GRAMÁLIA, CIDADE GINÁSIO 13 - VELARDIS, CIDADE GINÁSIO 18 - VALAIS |
| Meowth-G | 4 | ROTA 20, ROTA 21, ROTA 24, ROTA 25 |
| Mime Jr. | 6 | CIDADE AUXILIAR 06 - VILA LAPRAS, CIDADE GINÁSIO 05 - LUFAY, CIDADE GINÁSIO 08 - ALBAROCK, TÚNEL DOS PESCADORES |
| Mr. Mime | 1 | CIDADE AUXILIAR 06 - VILA LAPRAS |
| Mr. Mime-G | 1 | ROTA 20 |
| Muk-A | 1 | CIDADE AUXILIAR 01 - LIGHTMOR |
| Nidoran♀ | 5 | ROTA 41, ROTA 46, ROTA 49, ROTA 50, ROTA 55 |
| Nidoran♂ | 5 | ROTA 46, ROTA 47, ROTA 50, ROTA 51, ROTA 55 |
| Oricorio (E) | 2 | ROTA 49, ROTA 5 |
| Oricorio (F) | 2 | ROTA 49, ROTA 6 |
| Oricorio (G) | 3 | ILHAS DOS QUATRO, ROTA 49 |
| Oricorio (P) | 2 | ILHA DOS NAMORADOS, ROTA 49 |
| Ponyta-G | 3 | ROTA 64, ROTA 65, ROTA 66 |
| Rattata-A | 8 | CIDADE AUXILIAR 02 - GASTRIAL, CIDADE AUXILIAR 03 - NANABAN, ROTA 53, ROTA 65, ROTA 66 |
| Sandshrew-A | 4 | ROTA 20, ROTA 21, ROTA 25, ROTA 72 |
| Shellos (A) | 4 | ROTA 2, ROTA 27, ROTA 31 |
| Shellos (R) | 17 | CIDADE GINÁSIO 02 - FINNALGA, ILHAS DOS QUATRO, ROTA 14, ROTA 51 |
| Stunfisk-G | 2 | ROTA 52, ROTA 56 |
| Vulpix-A | 3 | ROTA 20, ROTA 24, ROTA 72 |
| Yamask-G | 2 | RIO DE AREIA, ROTA 38 |
| Zigzagoon-G | 2 | GREYPEAK, ROTA 48 |

### Registros que não devem ser comparados com o catálogo Pokémon

- **391** entradas `x`: o mestre confirmou que significam **sem encontro**.
- **14** entradas `Random`: não são nomes de Pokémon, todas em Ilhas dos Quatro.
- **11** campos de Pokémon vazios.

Para saber **exatamente quais Pokémon estão indisponíveis por nome no site**, rode `scripts/listar_pokemon_pendentes_ankar.py` no ambiente local do projeto (consulta somente leitura do catálogo ativo).
