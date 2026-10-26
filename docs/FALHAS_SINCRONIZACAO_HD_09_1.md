# Diagnóstico da primeira sincronização HD — Etapa 09.1

**Fonte:** relatório textual enviado pelo mestre em 25/10/2026.

- Catálogo original: 1.064 formas; comando informou 953 atualizadas e 110 não atualizadas entre 1.063 processadas.
- No trecho visível (a partir de Armaldo), há 90 erros explícitos: 88 HTTP 404, um timeout (Beautifly) e um limite de tamanho (Mew).
- As primeiras 54 entradas do catálogo não aparecem no trecho. Pela contagem (34 atualizadas, 20 não atualizadas) e pelo perfil de formas do catálogo, as 20 pendências anteriores são **inferidas** como duas formas de Aegislash e 18 variantes de Arceus. Confirme executando o novo comando `pokemon-hd-pendentes`.
- 'Não atualizada' **não significa** ausência de imagem no site: pode existir imagem antiga, sem resolução HD, ou imagem Shiny ausente.

## 90 falhas identificadas nominalmente no log

| Código da campanha | Problema inicial | Nome equivalente na PokéAPI / providência |
|---|---|---|
| `basculin-azul` | 404 | `basculin-blue-striped` |
| `basculin-vermelho` | 404 | `basculin-red-striped` |
| `beautifly` | Timeout | Nova tentativa automática |
| `burmy-arenoso` | 404 | `burmy-sandy` |
| `burmy-entulho` | 404 | `burmy-trash` |
| `burmy-planta` | 404 | `burmy-plant` |
| `calyrex-cavaleiro-gelado` | 404 | `calyrex-ice` |
| `calyrex-cavaleiro-sombrio` | 404 | `calyrex-shadow` |
| `castform-chuvoso` | 404 | `castform-rainy` |
| `castform-ensolarado` | 404 | `castform-sunny` |
| `castform-nevado` | 404 | `castform-snowy` |
| `darmanitan-galar-normal` | 404 | `darmanitan-galar-standard` |
| `darmanitan-normal` | 404 | `darmanitan-standard` |
| `deoxys-ataque` | 404 | `deoxys-attack` |
| `deoxys-velocidade` | 404 | `deoxys-speed` |
| `eevee-parceiro` | 404 | `eevee-starter` |
| `eiscue-congelado` | 404 | `eiscue-ice` |
| `eiscue-revelado` | 404 | `eiscue-noice` |
| `farfetch-d` | 404 | `farfetchd` |
| `farfetch-d-galar` | 404 | `farfetchd-galar` |
| `frillish` | 404 | Tentar fonte oficial em caso de imagem 404 |
| `giratina-alternativa` | 404 | `giratina-altered` |
| `giratina-origem` | 404 | `giratina-origin` |
| `gourgeist-gigante` | 404 | `gourgeist-super` |
| `gourgeist-grande` | 404 | `gourgeist-large` |
| `gourgeist-medio` | 404 | `gourgeist-average` |
| `gourgeist-pequeno` | 404 | `gourgeist-small` |
| `groudon-primitivo` | 404 | `groudon-primal` |
| `hoopa-confinado` | 404 | `hoopa` |
| `hoopa-livre` | 404 | `hoopa-unbound` |
| `indeedee-femea` | 404 | `indeedee-female` |
| `indeedee-macho` | 404 | `indeedee-male` |
| `jellicent` | 404 | Tentar fonte oficial em caso de imagem 404 |
| `keldeo-corajoso` | 404 | `keldeo-resolute` |
| `keldeo-normal` | 404 | `keldeo-ordinary` |
| `kyogre-primitivo` | 404 | `kyogre-primal` |
| `kyurem-branco` | 404 | `kyurem-white` |
| `kyurem-preto` | 404 | `kyurem-black` |
| `landorus-animal` | 404 | `landorus-therian` |
| `landorus-corporeo` | 404 | `landorus-incarnate` |
| `lycanroc-crepusculo` | 404 | `lycanroc-dusk` |
| `lycanroc-meia-noite` | 404 | `lycanroc-midnight` |
| `lycanroc-meio-dia` | 404 | `lycanroc-midday` |
| `meloetta-melodia` | 404 | `meloetta-aria` |
| `meloetta-pirueta` | 404 | `meloetta-pirouette` |
| `meowstic-femea` | 404 | `meowstic-female` |
| `meowstic-macho` | 404 | `meowstic-male` |
| `mew` | Limite de resposta | Ampliar limite de resposta JSON |
| `mimikyu` | 404 | `mimikyu-disguised` |
| `minior-meteoro` | 404 | `minior-red-meteor` |
| `minior-nucleo` | 404 | Sem correspondência HD segura: cor do núcleo não especificada |
| `morpeko-faminto` | 404 | `morpeko-hangry` |
| `morpeko-satisfeito` | 404 | `morpeko-full-belly` |
| `necrozma-alvorada` | 404 | `necrozma-dawn` |
| `necrozma-crepusculo-mane` | 404 | `necrozma-dusk` |
| `nidoran` | 404 | `nidoran-f` |
| `nidoran-2` | 404 | `nidoran-m` |
| `oricorio-pa-hu` | 404 | `oricorio-pau` |
| `pikachu-parceiro` | 404 | `pikachu-starter` |
| `pumpkaboo-gigante` | 404 | `pumpkaboo-super` |
| `pumpkaboo-grande` | 404 | `pumpkaboo-large` |
| `pumpkaboo-medio` | 404 | `pumpkaboo-average` |
| `pumpkaboo-pequeno` | 404 | `pumpkaboo-small` |
| `pyroar` | 404 | Tentar fonte oficial em caso de imagem 404 |
| `rotom-aparador` | 404 | `rotom-mow` |
| `rotom-geladeira` | 404 | `rotom-frost` |
| `rotom-maquina-de-lavar` | 404 | `rotom-wash` |
| `rotom-microondas` | 404 | `rotom-heat` |
| `rotom-ventilador` | 404 | `rotom-fan` |
| `shaymin-ceu` | 404 | `shaymin-sky` |
| `shaymin-terra` | 404 | `shaymin-land` |
| `sirfetch-d` | 404 | `sirfetchd` |
| `thundurus-animal` | 404 | `thundurus-therian` |
| `thundurus-corporeo` | 404 | `thundurus-incarnate` |
| `tornadus-animal` | 404 | `tornadus-therian` |
| `tornadus-corporeo` | 404 | `tornadus-incarnate` |
| `toxtricity-amplificado` | 404 | `toxtricity-amped` |
| `toxtricity-suave` | 404 | `toxtricity-low-key` |
| `urshifu-ataque-rapido` | 404 | `urshifu-rapid-strike` |
| `urshifu-golpe-unico` | 404 | `urshifu-single-strike` |
| `wishiwashi-cardume` | 404 | `wishiwashi-school` |
| `wishiwashi-sozinho` | 404 | `wishiwashi-solo` |
| `wormadam-arenoso` | 404 | `wormadam-sandy` |
| `wormadam-entulho` | 404 | `wormadam-trash` |
| `wormadam-planta` | 404 | `wormadam-plant` |
| `zacian-espada` | 404 | `zacian-crowned` |
| `zacian-heroi` | 404 | `zacian-hero` |
| `zamazenta-escudo` | 404 | `zamazenta-crowned` |
| `zamazenta-heroi` | 404 | `zamazenta-hero` |
| `zygarde-100` | 404 | `zygarde-complete` |

## 20 pendências inferidas no início do catálogo

| Código da campanha | Correspondência para nova tentativa |
|---|---|
| `aegislash-escudo` | `aegislash-shield` |
| `aegislash-lamina` | `aegislash-blade` |
| `arceus-agua` | `arceus-water` |
| `arceus-dragao` | `arceus-dragon` |
| `arceus-eletrico` | `arceus-electric` |
| `arceus-fada` | `arceus-fairy` |
| `arceus-fantasma` | `arceus-ghost` |
| `arceus-fogo` | `arceus-fire` |
| `arceus-gelo` | `arceus-ice` |
| `arceus-grama` | `arceus-grass` |
| `arceus-inseto` | `arceus-bug` |
| `arceus-lutador` | `arceus-fighting` |
| `arceus-metal` | `arceus-steel` |
| `arceus-normal` | `arceus-normal` |
| `arceus-noturno` | `arceus-dark` |
| `arceus-pedra` | `arceus-rock` |
| `arceus-psiquico` | `arceus-psychic` |
| `arceus-terra` | `arceus-ground` |
| `arceus-veneno` | `arceus-poison` |
| `arceus-voador` | `arceus-flying` |

## Procedimento de confirmação no seu banco

```powershell
flask --app app.py midia pokemon-hd-pendentes
flask --app app.py midia pokemon-hd --aplicar
flask --app app.py midia pokemon-hd-pendentes
```

Os resultados de cada execução ficam em `static/img/pokemon-hd/relatorio-ultima-sincronizacao.json`. As opções alternativas nunca substituem uma forma por espécie base incompatível. Quando faltarem artes HD, preservar a imagem existente e analisar pontualmente a forma.
