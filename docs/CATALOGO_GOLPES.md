# Catálogo administrativo de golpes

Esta etapa adiciona ao painel do mestre a administração dos golpes armazenados
no PostgreSQL. O catálogo importado continua preservado, enquanto novos golpes
podem ser criados e configurados sem alteração manual dos arquivos JSON.

## Funcionalidades

- listagem paginada dos golpes;
- pesquisa por nome, código, descrição e efeitos;
- filtros por tipo, categoria, origem e situação;
- criação e edição de golpes;
- expressão de dano, precisão e prioridade;
- marcação de golpe personalizado;
- desativação lógica e reativação;
- duplicação como registro personalizado e inativo;
- editor visual de efeitos;
- vínculos entre golpes e formas Pokémon;
- método e nível de aprendizado;
- auditoria em `historico_alteracoes`.

## Editor visual de efeitos

O editor converte os cartões preenchidos na interface para a coluna JSON
`golpes.efeitos`. A estrutura atual é versionada:

```json
{
  "versao": 1,
  "efeitos": []
}
```

Os tipos de efeito disponíveis são:

- efeito textual;
- aplicação de status;
- alteração de atributo;
- dano adicional;
- cura ou recuperação;
- múltiplos ataques;
- condição especial.

Cada efeito pode informar alvo, chance e uma observação opcional. Golpes antigos
importados no formato `{"texto": "..."}` são convertidos automaticamente para
o editor quando a tela é aberta. A conversão definitiva ocorre apenas quando o
golpe é salvo.

## Vínculos com formas

A tela de vínculos permite definir como uma forma Pokémon aprende um golpe:

- por nível;
- MT/TR;
- tutor;
- movimento de ovo;
- evento;
- inicial;
- método personalizado.

O vínculo pode guardar nível necessário, observações e configurações adicionais.
A mesma forma pode possuir o golpe por métodos diferentes, mas não pode repetir
o mesmo método.

## Rotas

```text
/mestre/catalogo/golpes
/mestre/catalogo/golpes/novo
/mestre/catalogo/golpes/<id>/editar
/mestre/catalogo/golpes/<id>/vinculos
```

As rotas exigem o perfil de mestre. Usuários administradores são representados
como mestre na sessão atual.

## Banco de dados

Não existe migration nova nesta etapa. Foram utilizadas as tabelas já criadas:

```text
golpes
categorias_golpe
forma_pokemon_golpes
formas_pokemon
status_condicoes
atributos
historico_alteracoes
```

A revisão esperada continua sendo:

```text
d94c7ab20e51 (head)
```

## Aplicação

Preserve o `.env` da instalação e execute:

```powershell
pip install -r requirements.txt
flask --app app.py db current
flask --app app.py catalogo verificar
python app.py
```

O comando de diagnóstico agora valida espécies, formas e golpes. O resultado
esperado termina com:

```text
Catálogo de espécies e formas está consistente no PostgreSQL.
Catálogo de golpes está consistente no PostgreSQL.
```

## Teste manual sugerido

1. Entre como mestre.
2. Acesse **Catálogo → Golpes**.
3. Pesquise um golpe importado e abra sua edição.
4. Confirme que o efeito textual antigo aparece no editor.
5. Crie um golpe personalizado com dano, precisão e prioridade.
6. Adicione dois efeitos diferentes e salve.
7. Atualize a página e confirme a persistência.
8. Duplique o golpe e confirme que a cópia nasce inativa.
9. Reative a cópia.
10. Vincule o golpe a uma forma por nível.
11. Atualize o nível do vínculo.
12. Remova o vínculo.
13. Confira as operações em `historico_alteracoes`.

## Regras preservadas

- golpes continuam sem PP;
- desativar um golpe não remove o movimento de Pokémon que já o possuem;
- golpes inativos deixam de aparecer em novos cadastros normais;
- efeitos textuais continuam válidos mesmo quando ainda não possuem automação;
- o editor não executa efeitos em combate nesta etapa; ele apenas estrutura e
  administra os dados que serão utilizados pelo futuro assistente de combate.


> Na versão consolidada do projeto, a revisão atual é `d94c7ab20e51` por causa do módulo posterior de itens e inventário. Consulte `ITENS_INVENTARIO.md`.
