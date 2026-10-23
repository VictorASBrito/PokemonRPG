# Orientações de continuidade para assistentes de desenvolvimento

Este projeto é **Pokémon RPG — campanha Ankar**. Não recomece a aplicação nem suponha que o manual PKMRPG original se aplique sem as adaptações da campanha.

**LEITURA OBRIGATÓRIA ANTES DE ALTERAR CÓDIGO:**

1. [`CONTINUIDADE_PROJETO.md`](CONTINUIDADE_PROJETO.md) — arquitetura real, adaptações de regras, módulos e roteiro.
2. [`DIARIO_DESENVOLVIMENTO.md`](DIARIO_DESENVOLVIMENTO.md) — últimas decisões, alterações, testes e pendências.
3. `README.md` e a documentação especializada pertinente à tarefa.
4. Código, migrations, testes e `git status` da versão efetivamente fornecida; **o código mais recente prevalece sobre documentos antigos**.

**A cada entrega de código:** atualizar o documento mestre e registrar a entrada no diário no mesmo pacote de alterações. Informar arquivos modificados, testes executados e eventuais falhas, próxima tarefa e se ocorreu alguma migration. Não dizer que testes passaram sem executá-los.

**Preservação e segurança:** não substituir `.env`, JSONs privados em `data/`, `static/uploads/`, banco de dados ou alterações locais não commitadas. Não inserir segredos em documentação. Usar mudanças incrementais, permissões do servidor e migrações controladas.

**Divergências cruciais:** nível compartilhado via `personagens.nivel`; experiência individual, amizade, captura automática e consumo de PP não fazem parte do fluxo atual de Ankar. Equipe de até 6 Pokémon; Box única de 100 espaços. Quatro perfis: administrador, mestre, tester e jogador.

**Limite do procedimento:** documentação só avança quando uma nova etapa é efetivamente trabalhada e os arquivos são atualizados; não há atualização automática do repositório sem acesso a ele.
