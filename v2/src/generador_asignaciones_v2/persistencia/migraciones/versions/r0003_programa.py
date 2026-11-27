"""Añade calendario configurable, publicaciones y registro de importaciones."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"


def upgrade() -> None:
    op.add_column(
        "programas", sa.Column("num_grupos", sa.Integer(), nullable=False, server_default="4")
    )
    op.add_column(
        "programas", sa.Column("grupo_inicial", sa.Integer(), nullable=False, server_default="1")
    )
    op.add_column(
        "programas", sa.Column("revision", sa.Integer(), nullable=False, server_default="0")
    )
    op.add_column(
        "programas", sa.Column("historico", sa.Boolean(), nullable=False, server_default="0")
    )
    for reunion in ("martes", "domingo"):
        op.add_column(
            "semanas_programa",
            sa.Column(reunion, sa.Boolean(), nullable=False, server_default=sa.true()),
        )
    op.add_column(
        "semanas_programa",
        sa.Column("desactivados", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.create_table(
        "publicaciones",
        sa.Column("programa_id", sa.Integer(), sa.ForeignKey("programas.id"), primary_key=True),
        sa.Column("version", sa.Integer(), primary_key=True),
        sa.Column("revision_borrador", sa.Integer(), nullable=False),
        sa.Column("contenido", sa.JSON(), nullable=False),
    )
    op.create_table(
        "lotes_importados",
        sa.Column("huella", sa.String(), primary_key=True),
        sa.Column("resumen", sa.JSON(), nullable=False),
    )


def downgrade() -> None:
    raise NotImplementedError("Para volver a una revisión anterior, recupera su respaldo.")
