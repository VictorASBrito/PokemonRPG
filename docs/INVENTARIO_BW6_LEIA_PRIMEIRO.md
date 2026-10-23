# Inventário BW6 — alinhamento e versão compacta

Esta atualização altera **apenas** a apresentação da mochila (HTML, CSS, JavaScript e ícones), a indicação de versão e os testes relacionados. Não contém migration e não modifica as regras de manipulação de itens no PostgreSQL.

## O que mudou

- O inventário preenche a altura útil da tela em desktop (largura ≥ 1200 px e altura ≥ 760 px). A página deixa de rolar; **listas longas e detalhes extensos podem rolar dentro dos respectivos painéis**. Em telas pequenas ou com zoom aumentado, a rolagem normal é mantida para não ocultar controles.
- Os seis cartões de Pokémon na esquerda utilizam altura flexível, retratos maiores e barras de PV legíveis.
- As cinco abas mostram **ícone ampliado sem borrão e nome da categoria**.
- “Itens nesta bolsa” fica alinhado horizontalmente ao cartão “Bolsa ativa”, com a mesma altura.
- Uploads, quantidades, permissões, consumo, equipar e transferir continuam funcionando pela implementação existente.

## Instalação recomendada no Windows

1. Pare o servidor local/Cloudflare.
2. Extraia o ZIP em uma pasta temporária.
3. Entre no diretório `PokemonRPG` extraído e rode:

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force
.\INSTALAR_INVENTARIO_BW6.ps1 -Destino "C:\Users\Victor\Desktop\Projetos\PokemonRPG"
```

4. Reinicie o servidor e use `Ctrl+F5` no navegador.

O instalador cria backup dos arquivos substituídos e não toca em `.env`, `data`, `static/uploads` ou banco de dados.

## Como confirmar a versão

Abra o HTML da página no navegador (`Ctrl+U`) e busque por:

```text
bw6-layout-compacto-20261022
```

Também é retornado no cabeçalho HTTP `X-PokemonRPG-Inventario`.

## Testes

```powershell
pytest -q tests/test_inventario_bw_refator.py tests/test_itens_inventario.py
```

O pacote passou por verificação de sintaxe Python, JavaScript e template Jinja e pela validação estrutural dos assets. A suíte Flask não pôde ser executada neste ambiente porque Flask/SQLAlchemy não estão instalados e não há conexão de rede para instalar as dependências.
