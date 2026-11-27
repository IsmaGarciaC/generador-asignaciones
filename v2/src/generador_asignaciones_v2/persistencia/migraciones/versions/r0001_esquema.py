"""Crea los registros base del programa y sus referencias estables."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None


def upgrade() -> None:
    puesto = sa.Enum(
        "audio", "video", "acomodador", "microfonos", "plataforma",
        "lector_martes", "presidente", "lector_domingo",
        native_enum=False, create_constraint=True, name="puesto",
    )
    op.execute("PRAGMA application_id = 0x47415632")
    op.create_table(
        "hermanos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint("length(trim(nombre)) > 0", name="nombre_no_vacio"),
        sqlite_autoincrement=True,
    )
    op.create_table(
        "capacitaciones",
        sa.Column("hermano_id", sa.Integer(), sa.ForeignKey("hermanos.id"), primary_key=True),
        sa.Column("puesto", puesto, primary_key=True),
    )
    op.create_table(
        "ausencias",
        sa.Column("hermano_id", sa.Integer(), sa.ForeignKey("hermanos.id"), primary_key=True),
        sa.Column("inicio_semana", sa.Date(), primary_key=True),
    )
    op.create_table(
        "programas",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("anio", sa.Integer(), nullable=False),
        sa.Column("mes", sa.Integer(), nullable=False),
        sa.UniqueConstraint("anio", "mes", name="mes_del_programa"),
        sa.CheckConstraint("anio BETWEEN 1 AND 9999 AND mes BETWEEN 1 AND 12", name="mes_valido"),
    )
    op.create_table(
        "semanas_programa",
        sa.Column("programa_id", sa.Integer(), sa.ForeignKey("programas.id"), primary_key=True),
        sa.Column("inicio_semana", sa.Date(), primary_key=True),
        sa.Column("limpieza", sa.Integer()),
        sa.Column("hospitalidad", sa.Integer()),
        sa.CheckConstraint("limpieza > 0", name="grupo_limpieza_positivo"),
        sa.CheckConstraint("hospitalidad > 0", name="grupo_hospitalidad_positivo"),
    )
    op.create_table(
        "asignaciones",
        sa.Column("programa_id", sa.Integer(), primary_key=True),
        sa.Column("inicio_semana", sa.Date(), primary_key=True),
        sa.Column("puesto", puesto.copy(), primary_key=True),
        sa.Column("plaza", sa.Integer(), primary_key=True),
        sa.Column("hermano_id", sa.Integer(), sa.ForeignKey("hermanos.id")),
        sa.ForeignKeyConstraint(
            ["programa_id", "inicio_semana"],
            ["semanas_programa.programa_id", "semanas_programa.inicio_semana"],
        ),
        sa.CheckConstraint("plaza > 0", name="plaza_positiva"),
    )
    op.create_index("ix_asignaciones_hermano_id", "asignaciones", ["hermano_id"])


def downgrade() -> None:
    raise NotImplementedError("Para volver a una revisión anterior, recupera su respaldo.")
