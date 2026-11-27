"""Copia SQLite consistente y verificación previa a la publicación del archivo."""

import os
import sqlite3
from contextlib import closing
from pathlib import Path
from tempfile import NamedTemporaryFile

ID_APLICACION = 0x47415632


def copiar_base(origen: Path, destino: Path) -> Path:
    """Publica una copia íntegra en un archivo nuevo y conserva ambos originales."""
    if destino.exists():
        raise FileExistsError(f"Ya existe {destino}")
    uri_origen = f"{origen.resolve().as_uri()}?mode=ro"
    with closing(sqlite3.connect(uri_origen, uri=True)) as entrada:
        if entrada.execute("PRAGMA application_id").fetchone() != (ID_APLICACION,):
            raise sqlite3.DatabaseError("El origen no es una base del Generador V2.")

        destino.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(dir=destino.parent, suffix=".tmp", delete=False) as archivo:
            temporal = Path(archivo.name)
        try:
            with closing(sqlite3.connect(temporal)) as salida:
                entrada.backup(salida)
                integridad = salida.execute("PRAGMA integrity_check").fetchall()
                referencias_invalidas = salida.execute("PRAGMA foreign_key_check").fetchone()
                revision = salida.execute("SELECT version_num FROM alembic_version").fetchone()
                if integridad != [("ok",)] or referencias_invalidas or not revision:
                    raise sqlite3.DatabaseError("La copia no superó la verificación de integridad.")

            if os.name == "nt":
                temporal.rename(destino)  # Windows rechaza un destino existente.
            else:
                temporal.hardlink_to(destino)
        finally:
            temporal.unlink(missing_ok=True)
    return destino
