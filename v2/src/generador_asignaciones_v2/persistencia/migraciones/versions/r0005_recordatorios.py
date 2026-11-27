"""Configuración y confirmaciones de los recordatorios semanales."""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"


def upgrade() -> None:
    op.create_table(
        "configuracion_recordatorios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("puestos", sa.JSON(), nullable=False),
        sa.Column("plantilla", sa.Text(), nullable=False),
    )
    op.create_table(
        "envios_recordatorios",
        sa.Column("inicio_semana", sa.Date(), primary_key=True),
        sa.Column("hermano_id", sa.Integer(), sa.ForeignKey("hermanos.id"), primary_key=True),
        sa.Column("numero", sa.Integer(), primary_key=True),
        sa.Column("programa_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("confirmado_utc", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["programa_id", "version"], ["publicaciones.programa_id", "publicaciones.version"]
        ),
    )


def downgrade() -> None:
    raise NotImplementedError("Para volver a una revisión anterior, recupera su respaldo.")
