"""Modelos do projeto.

Os helpers legados baseados em JSON continuam em ``app.models.jogador`` e
``app.models.pokemon`` durante a migração. Os modelos relacionais ficam em
``app.models.db`` e são importados aqui para que o Alembic reconheça todo o
metadata.
"""

from app.models.db import *  # noqa: F401,F403
