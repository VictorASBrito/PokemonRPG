POKÉMON RPG — ETAPA 10C.5.1
Correção dos testes da repaginação responsiva no Windows
Base: Etapa 10C.5 já extraída/instalada no projeto.

Este patch altera APENAS:
- scripts/instalar_visual_10c5.py: listas de caminhos usam .as_posix() (Windows e Linux retornam '/').
- tests/test_visual_10c5.py: CSS é validado com Python puro; tinycss2 adiciona validação mais completa apenas se estiver instalado.

INSTALAÇÃO
1. Extraia o conteúdo deste ZIP na RAIZ da pasta PokemonRPG, substituindo os 2 arquivos de mesmo nome.
2. Execute (PowerShell):
   python -m pytest -q tests/test_visual_10c5.py
3. Se o visual 10C.5 já está instalado, NÃO é necessário rodar o instalador novamente.
   Para verificar: python scripts/instalar_visual_10c5.py --verificar
   Retorno esperado se instalado: Visual 10C.5 já instalado. Nenhuma alteração.

O patch não altera templates, CSS, JavaScript, banco PostgreSQL, cadastros, inventários ou permissões.
Validação do patch em ambiente Linux: 6 testes passaram. Precisa confirmar na instalação Windows.
