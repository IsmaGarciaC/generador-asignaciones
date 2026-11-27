"""Conexiones SQLite, migraciones y transacciones de la aplicación."""

import os
import sqlite3
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from datetime import date, datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import URL, Connection, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from generador_asignaciones_v2.persistencia.respaldo import ID_APLICACION, copiar_base

ARCHIVO_BASE = "programa.sqlite3"


def ruta_base_local() -> Path:
    local_app_data = Path(os.environ.get("LOCALAPPDATA", ""))
    if not local_app_data.is_absolute():
        raise OSError("Windows no proporcionó una ruta absoluta en LOCALAPPDATA.")
    return local_app_data / "GeneradorAsignacionesV2" / ARCHIVO_BASE


def _marca_temporal() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")


def _configurar_conexion(dbapi: sqlite3.Connection, _registro: object) -> None:
    dbapi.isolation_level = None
    cursor = dbapi.execute("PRAGMA foreign_keys = ON")
    cursor.close()


def _iniciar_transaccion(conexion: Connection) -> None:
    # La preparación toma el turno de escritor antes de leer la revisión.
    sql = "BEGIN IMMEDIATE" if conexion.get_execution_options().get("reservar") else "BEGIN"
    conexion.exec_driver_sql(sql)


class BaseDatos:
    def __init__(self, ruta: Path) -> None:
        self.ruta = ruta
        self.motor = create_engine(URL.create("sqlite", database=str(ruta)))
        event.listen(self.motor, "connect", _configurar_conexion)
        event.listen(self.motor, "begin", _iniciar_transaccion)
        self._sesiones = sessionmaker(self.motor)

    def preparar(self) -> None:
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        config = Config()
        config.set_main_option(
            "script_location", "generador_asignaciones_v2.persistencia:migraciones"
        )
        revisiones = ScriptDirectory.from_config(config)
        with self.motor.connect().execution_options(reservar=True) as conexion, conexion.begin():
            identificador = conexion.exec_driver_sql("PRAGMA application_id").scalar_one()
            actual = None
            if identificador == ID_APLICACION:
                actual = MigrationContext.configure(conexion).get_current_revision()
                if actual is None:
                    raise sqlite3.DatabaseError("La base de V2 no tiene una revisión registrada.")
                revisiones.get_revision(actual)
            elif identificador or conexion.exec_driver_sql(
                "SELECT 1 FROM sqlite_schema WHERE name NOT LIKE 'sqlite_%' LIMIT 1"
            ).first():
                raise sqlite3.DatabaseError("El archivo existente no es una base del Generador V2.")

            if actual == revisiones.get_current_head():
                destino = self._carpeta_respaldos / f"diario-{date.today().isoformat()}.sqlite3"
                if not destino.exists():
                    copiar_base(self.ruta, destino)
            else:
                if actual is not None:
                    self.respaldar(prefijo="antes-de-migrar")
                config.attributes["connection"] = conexion
                command.upgrade(config, "head")

    def transaccion(self) -> AbstractContextManager[Session]:
        """Confirma todo el trabajo en conjunto y revierte si se propaga una excepción."""
        return self._sesiones.begin()

    @contextmanager
    def escritura(self) -> Iterator[Session]:
        """Serializa una comprobación seguida de una escritura en la misma transacción."""
        with self.motor.connect().execution_options(reservar=True) as conexion:
            with conexion.begin(), Session(conexion) as sesion:
                yield sesion
                sesion.flush()

    @property
    def _carpeta_respaldos(self) -> Path:
        return self.ruta.parent / "respaldos"

    def respaldar(self, *, prefijo: str = "manual") -> Path:
        destino = self._carpeta_respaldos / f"{prefijo}-{_marca_temporal()}.sqlite3"
        return copiar_base(self.ruta, destino)

    def recuperar(self, respaldo: Path) -> Path:
        destino = self.ruta.parent / "recuperaciones" / _marca_temporal() / ARCHIVO_BASE
        return copiar_base(respaldo, destino)

    def close(self) -> None:
        self.motor.dispose()
