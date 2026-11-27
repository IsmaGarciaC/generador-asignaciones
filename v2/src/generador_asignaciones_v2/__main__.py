"""Arranque de escritorio y operaciones locales de mantenimiento."""

import argparse
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

from alembic.util import CommandError
from sqlalchemy.exc import SQLAlchemyError

from generador_asignaciones_v2.persistencia.base_datos import BaseDatos, ruta_base_local


def ejecutar() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    comandos = parser.add_subparsers(dest="comando")
    comandos.add_parser("preparar", help="crea o actualiza la base local")
    comandos.add_parser("respaldar", help="crea y verifica un respaldo")
    recuperar = comandos.add_parser("recuperar", help="restaura una copia en otra ubicación")
    recuperar.add_argument("respaldo", type=Path)
    opciones = parser.parse_args()

    try:
        with closing(BaseDatos(ruta_base_local())) as base:
            if opciones.comando == "respaldar":
                print(base.respaldar())
            elif opciones.comando == "recuperar":
                print(base.recuperar(opciones.respaldo))
            else:
                base.preparar()
                if opciones.comando == "preparar":
                    print(base.ruta)
                else:
                    from generador_asignaciones_v2.escritorio import iniciar
                    from generador_asignaciones_v2.persistencia.programas import Programas

                    iniciar(Programas(base))
    except (OSError, sqlite3.Error, SQLAlchemyError, CommandError) as error:
        mensaje = f"No se pudo completar la operación.\n{error}"
        if sys.stderr is None and sys.platform == "win32":
            from ctypes import windll

            windll.user32.MessageBoxW(None, mensaje, "Generador de Asignaciones", 0x10)
        else:
            print(mensaje, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(ejecutar())
