"""Añade un teléfono opcional a cada hermano existente."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"


def upgrade() -> None:
    op.add_column("hermanos", sa.Column("telefono", sa.String(), nullable=True))


def downgrade() -> None:
    raise NotImplementedError("Para volver a una revisión anterior, recupera su respaldo.")
