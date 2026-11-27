"""Guarda los bloqueos junto a las asignaciones del borrador."""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"


def upgrade() -> None:
    op.add_column(
        "asignaciones",
        sa.Column("bloqueada", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    raise NotImplementedError("Para volver a una revisión anterior, recupera su respaldo.")
