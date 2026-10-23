# Permissões de edição e etiquetas de tipos

- **Jogador** pode editar apelido, PV atual, bônus manuais, status, golpes e anotações, mas **não** espécie/forma, gênero, natureza ou Shiny. O backend rejeita POST adulterado (403) e o serviço de persistência recusa campos restritos.
- **Tester** pode editar **todos esses campos**, incluindo espécie/forma, gênero, natureza e Shiny, somente dos próprios Pokémon. Não ganha acesso às páginas administrativas nem permissão para criar itens.
- **Admin/Mestre** conserva edição completa dos Pokémon pelas rotas administrativas. Criação de Pokémon continua restrita a Admin/Mestre e Tester, em espaço vazio na Box.
- Para todos os perfis, **itens carregados** são equipados/retirados pela tela de inventário, com movimentação real de unidades.
- Tags dos tipos agora são mini-etiquetas desenhadas em CSS, usando a referência apenas para cores e formato arredondado (sem imagens recortadas). Os 18 tipos são exibidos em português, inclusive quando o catálogo informa o nome em inglês. Tipos personalizados recebem etiqueta neutra, mantendo seu nome.
- Detalhamento expandido mostra até quatro golpes em duas linhas de cartões compactos, com nome, etiqueta colorida do tipo, dano, precisão e prioridade; informações completas aparecem ao passar o mouse.
- Sem migration nova. Preservar .env e static/uploads/ ao atualizar.
