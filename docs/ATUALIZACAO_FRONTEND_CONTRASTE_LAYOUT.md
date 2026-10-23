# Atualização de frontend — contraste e layout Pokémon

## Mudanças

- Retratos Pokémon no modo escuro agora permanecem em superfícies escuras, sem blocos brancos.
- Corrigida a largura do retrato dos Pokémon no dashboard 3x2 para impedir sobreposição sobre nome/PV.
- O Pokémon expandido não recolhe mais ao clicar no próprio cartão. Para voltar à grade use **Recolher** ou `Esc`.
- O cartão expandido permite selecionar/copiar texto normalmente.
- Tela de Equipe: até 6 Pokémon por linha no desktop.
- Equipe ativa dentro da Box e Box principal: até 6 cartões por linha no desktop.
- Layout continua responsivo em resoluções menores.

## Banco de dados

Nenhuma migration nova.

## Arquivos locais a preservar ao atualizar

- `.env`
- `data/` (backup legado)
- `static/uploads/`
