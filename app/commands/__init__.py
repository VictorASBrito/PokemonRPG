from app.commands.database import banco_cli
from app.commands.dados import dados_cli
from app.commands.usuarios import usuarios_cli
from app.commands.ficha import ficha_cli
from app.commands.pokemon import pokemon_cli
from app.commands.catalogo import catalogo_cli
from app.commands.inventario import inventario_cli
from app.commands.midia import midia_cli

__all__ = [
    "banco_cli",
    "dados_cli",
    "usuarios_cli",
    "ficha_cli",
    "pokemon_cli",
    "catalogo_cli",
    "inventario_cli",
    "midia_cli",
]
