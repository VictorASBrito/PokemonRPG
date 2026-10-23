# Ajuste do nível pelo Admin / Mestre

## Problema abordado

A página de ficha envia todos os campos do personagem, e a validação completa
pode rejeitar a operação caso algum outro dado antigo esteja incompatível com
as regras atuais (por exemplo, PV acima do máximo).

A partir desta versão, o nível também pode ser atualizado separadamente em:

- **Painel Geral do Mestre** → campo **Nível** no cartão do personagem → **Salvar nível**.
- **Mestre → Jogadores** → campo **Nível do personagem** → **Atualizar nível**.
- **Ficha aberta pelo mestre** → **Alterar apenas o nível**.

A alteração isolada modifica apenas `personagens.nivel`, sem apagar equipe,
Box, PV, atributos, golpes ou outras informações. Os Pokémon continuam
usando o nível compartilhado do personagem.

## Segurança

- Apenas contas `administrador` ou `mestre` autenticadas podem usar a rota.
- O personagem deve pertencer à campanha ativa.
- O nível deve ser inteiro e respeitar o mínimo/máximo das regras em uso.
- Cada mudança é registrada em `historico_alteracoes` como `ajustar_nivel`.
- Os formulários exigem token CSRF da sessão.
- Jogador e Tester não podem utilizar a ação administrativa.

O mecanismo independente **não altera** os níveis de acesso (perfis)
`administrador`, `mestre`, `tester` e `jogador`.

## Instalação

Não é necessária migration. Preserve `.env`, `data/` e `static/uploads/`,
substitua o projeto e reinicie o servidor. Depois execute:

```powershell
pytest -q tests/test_ajuste_nivel_mestre.py
```

Nota: se a suíte completa apresentar falhas anteriores em testes de redirecionamento
de outros módulos, essas falhas devem ser tratadas separadamente.
