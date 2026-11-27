"""Tablas de identidad, disponibilidad registrada y programa semanal."""

from datetime import date

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    UniqueConstraint,
    true,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from generador_asignaciones_v2.dominio.puestos import Puesto


class Base(DeclarativeBase):
    type_annotation_map = {
        Puesto: Enum(
            Puesto,
            values_callable=lambda puestos: [puesto.value for puesto in puestos],
            name="puesto",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
    }


class Hermano(Base):
    __tablename__ = "hermanos"
    __table_args__ = (
        CheckConstraint("length(trim(nombre)) > 0", name="nombre_no_vacio"),
        {"sqlite_autoincrement": True},
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str]
    activo: Mapped[bool] = mapped_column(server_default=true())
    telefono: Mapped[str | None]


class Capacitacion(Base):
    __tablename__ = "capacitaciones"

    hermano_id: Mapped[int] = mapped_column(ForeignKey("hermanos.id"), primary_key=True)
    puesto: Mapped[Puesto] = mapped_column(primary_key=True)


class Ausencia(Base):
    __tablename__ = "ausencias"

    hermano_id: Mapped[int] = mapped_column(ForeignKey("hermanos.id"), primary_key=True)
    inicio_semana: Mapped[date] = mapped_column(primary_key=True)


class Programa(Base):
    __tablename__ = "programas"
    __table_args__ = (
        UniqueConstraint("anio", "mes", name="mes_del_programa"),
        CheckConstraint("anio BETWEEN 1 AND 9999 AND mes BETWEEN 1 AND 12", name="mes_valido"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    anio: Mapped[int]
    mes: Mapped[int]


class SemanaPrograma(Base):
    __tablename__ = "semanas_programa"
    __table_args__ = (
        CheckConstraint("limpieza > 0", name="grupo_limpieza_positivo"),
        CheckConstraint("hospitalidad > 0", name="grupo_hospitalidad_positivo"),
    )

    programa_id: Mapped[int] = mapped_column(ForeignKey("programas.id"), primary_key=True)
    inicio_semana: Mapped[date] = mapped_column(primary_key=True)
    limpieza: Mapped[int | None]
    hospitalidad: Mapped[int | None]


class Asignacion(Base):
    __tablename__ = "asignaciones"
    __table_args__ = (
        ForeignKeyConstraint(
            ["programa_id", "inicio_semana"],
            ["semanas_programa.programa_id", "semanas_programa.inicio_semana"],
        ),
        CheckConstraint("plaza > 0", name="plaza_positiva"),
    )

    programa_id: Mapped[int] = mapped_column(primary_key=True)
    inicio_semana: Mapped[date] = mapped_column(primary_key=True)
    puesto: Mapped[Puesto] = mapped_column(primary_key=True)
    plaza: Mapped[int] = mapped_column(primary_key=True)
    hermano_id: Mapped[int | None] = mapped_column(ForeignKey("hermanos.id"), index=True)
