import sqlite3
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import date
from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from generador_asignaciones_v2.dominio.puestos import Puesto
from generador_asignaciones_v2.persistencia.base_datos import BaseDatos, ruta_base_local
from generador_asignaciones_v2.persistencia.modelos import (
    Asignacion,
    Ausencia,
    Base,
    Capacitacion,
    Hermano,
    Programa,
    SemanaPrograma,
)
from generador_asignaciones_v2.persistencia.respaldo import copiar_base

MARTES = date(2026, 12, 1)


@pytest.fixture
def base(tmp_path: Path) -> Iterator[BaseDatos]:
    with closing(BaseDatos(tmp_path / "Ubicación privada" / "programa.sqlite3")) as datos:
        yield datos


def _revision_inicial(base: BaseDatos) -> None:
    base.ruta.parent.mkdir(parents=True)
    config = Config()
    config.set_main_option("script_location", "generador_asignaciones_v2.persistencia:migraciones")
    with base.motor.begin() as conexion:
        config.attributes["connection"] = conexion
        command.upgrade(config, "0001")
        conexion.exec_driver_sql("INSERT INTO hermanos (id, nombre) VALUES (41, 'Persona 41')")
        conexion.exec_driver_sql("INSERT INTO programas (id, anio, mes) VALUES (9, 2026, 12)")
        conexion.exec_driver_sql(
            "INSERT INTO semanas_programa VALUES (9, '2026-12-01', 4, 3)"
        )
        conexion.exec_driver_sql(
            "INSERT INTO asignaciones VALUES (9, '2026-12-01', 'audio', 1, 41)"
        )


def _guardar_programa(sesion: Session) -> None:
    sesion.add_all([Hermano(id=41, nombre="Persona 41"), Programa(id=9, anio=2026, mes=12)])
    sesion.flush()
    sesion.add(SemanaPrograma(programa_id=9, inicio_semana=MARTES, limpieza=4, hospitalidad=3))
    sesion.add(Capacitacion(hermano_id=41, puesto=Puesto.AUDIO))
    sesion.add(Ausencia(hermano_id=41, inicio_semana=date(2026, 12, 8)))
    sesion.flush()
    sesion.add_all([
        Asignacion(
            programa_id=9, inicio_semana=MARTES, puesto=Puesto.AUDIO, plaza=1, hermano_id=41
        ),
        Asignacion(
            programa_id=9, inicio_semana=MARTES, puesto=Puesto.VIDEO, plaza=1, hermano_id=41
        ),
        Asignacion(programa_id=9, inicio_semana=MARTES, puesto=Puesto.MICROFONOS, plaza=1),
    ])
    sesion.flush()


def test_base_vacia_con_esquema_al_dia(base: BaseDatos) -> None:
    base.preparar()
    with base.motor.connect() as conexion:
        assert conexion.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
        contexto = MigrationContext.configure(conexion, opts={"compare_server_default": True})
        assert contexto.get_current_revision() == "0002"
        assert compare_metadata(contexto, Base.metadata) == []
    with base.transaccion() as sesion:
        assert sesion.scalars(select(Programa)).all() == []
    assert not (base.ruta.parent / "respaldos").exists()


def test_dos_arranques_concurrentes_crean_solo_un_respaldo_diario(base: BaseDatos) -> None:
    with closing(BaseDatos(base.ruta)) as segunda, ThreadPoolExecutor(max_workers=2) as tareas:
        arranques = [tareas.submit(datos.preparar) for datos in (base, segunda)]
        for arranque in arranques:
            arranque.result(timeout=10)
    base.preparar()
    respaldos = list((base.ruta.parent / "respaldos").glob("diario-*.sqlite3"))
    assert len(respaldos) == 1


def test_migracion_conserva_datos_y_guarda_revision_anterior(base: BaseDatos) -> None:
    _revision_inicial(base)
    base.preparar()

    with base.transaccion() as sesion:
        persona = sesion.get_one(Hermano, 41)
        assert (persona.nombre, persona.telefono) == ("Persona 41", None)
        assert sesion.get_one(Asignacion, (9, MARTES, Puesto.AUDIO, 1)).hermano_id == persona.id
        semana = sesion.get_one(SemanaPrograma, (9, MARTES))
        assert (semana.limpieza, semana.hospitalidad) == (4, 3)
        persona.telefono = "000"

    (respaldo,) = (base.ruta.parent / "respaldos").glob("antes-de-migrar-*.sqlite3")
    with closing(sqlite3.connect(respaldo)) as anterior:
        assert anterior.execute("SELECT version_num FROM alembic_version").fetchone() == ("0001",)
        assert anterior.execute("SELECT id, nombre FROM hermanos").fetchone() == (41, "Persona 41")
        assert {fila[1] for fila in anterior.execute("PRAGMA table_info(hermanos)")} == {
            "id", "nombre", "activo"
        }


def test_error_en_migracion_revierte_esquema_y_permite_reintento(
    base: BaseDatos, monkeypatch: pytest.MonkeyPatch
) -> None:
    _revision_inicial(base)
    aplicar = command.upgrade

    def migracion_interrumpida(config: Config, revision: str) -> None:
        aplicar(config, revision)
        raise RuntimeError("Interrupción simulada")

    with monkeypatch.context() as cambios:
        cambios.setattr(command, "upgrade", migracion_interrumpida)
        with pytest.raises(RuntimeError, match="Interrupción simulada"):
            base.preparar()

    with base.motor.connect() as conexion:
        assert MigrationContext.configure(conexion).get_current_revision() == "0001"
        assert "telefono" not in {
            fila[1] for fila in conexion.exec_driver_sql("PRAGMA table_info(hermanos)")
        }
    base.preparar()
    with base.transaccion() as sesion:
        assert sesion.get_one(Hermano, 41).nombre == "Persona 41"


def test_sin_respaldo_previo_la_migracion_se_detiene(base: BaseDatos) -> None:
    _revision_inicial(base)
    (base.ruta.parent / "respaldos").touch()
    with pytest.raises(FileExistsError):
        base.preparar()
    with base.motor.connect() as conexion:
        assert MigrationContext.configure(conexion).get_current_revision() == "0001"
        assert conexion.exec_driver_sql("SELECT id FROM hermanos").scalar_one() == 41


def test_escritura_interrumpida_no_deja_un_programa_parcial(base: BaseDatos) -> None:
    base.preparar()
    with pytest.raises(RuntimeError, match="Interrupción simulada"):
        with base.transaccion() as sesion:
            _guardar_programa(sesion)
            raise RuntimeError("Interrupción simulada")

    with base.transaccion() as sesion:
        assert all(
            sesion.scalars(select(modelo)).first() is None
            for modelo in (Programa, SemanaPrograma, Asignacion, Hermano, Capacitacion, Ausencia)
        )
        _guardar_programa(sesion)

    with base.transaccion() as sesion:
        assert sesion.get_one(Asignacion, (9, MARTES, Puesto.AUDIO, 1)).hermano_id == 41


def test_historial_conserva_identidad_al_renombrar_y_desactivar(base: BaseDatos) -> None:
    base.preparar()
    with base.transaccion() as sesion:
        _guardar_programa(sesion)
    with base.transaccion() as sesion:
        persona = sesion.get_one(Hermano, 41)
        persona.nombre = "Persona 41 corregida"
        persona.activo = False

    with base.transaccion() as sesion:
        assert sesion.get_one(Hermano, 41).nombre == "Persona 41 corregida"
        assert not sesion.get_one(Hermano, 41).activo
        ids = sesion.scalars(select(Asignacion.hermano_id)).all()
        assert ids.count(41) == 2
        assert ids.count(None) == 1
    with pytest.raises(IntegrityError), base.transaccion() as sesion:
        sesion.delete(sesion.get_one(Hermano, 41))


def test_restauracion_de_una_copia_en_otra_ubicacion(base: BaseDatos) -> None:
    base.preparar()
    with base.transaccion() as sesion:
        _guardar_programa(sesion)
    with base.transaccion() as sesion:
        sesion.get_one(Hermano, 41).nombre = "Cambio aún sin confirmar"
        sesion.flush()
        respaldo = base.respaldar()

    recuperada = base.recuperar(respaldo)
    assert recuperada.parent.parent == base.ruta.parent / "recuperaciones"
    with closing(BaseDatos(recuperada)) as copia, copia.transaccion() as sesion:
        assert sesion.get_one(Hermano, 41).nombre == "Persona 41"
        assert sesion.get_one(Programa, 9).mes == 12
        assert sesion.get_one(SemanaPrograma, (9, MARTES)).limpieza == 4
        assert sesion.get_one(Asignacion, (9, MARTES, Puesto.VIDEO, 1)).hermano_id == 41
        assert sesion.get_one(Capacitacion, (41, Puesto.AUDIO)).puesto == Puesto.AUDIO
        assert sesion.get_one(Ausencia, (41, date(2026, 12, 8))).hermano_id == 41
    with base.transaccion() as sesion:
        assert sesion.get_one(Hermano, 41).nombre == "Cambio aún sin confirmar"


def test_copia_rechaza_destino_existente_y_bases_ajenas(base: BaseDatos, tmp_path: Path) -> None:
    base.preparar()
    respaldo = base.respaldar()
    contenido = respaldo.read_bytes()
    with pytest.raises(FileExistsError):
        copiar_base(base.ruta, respaldo)
    assert respaldo.read_bytes() == contenido

    ajena = tmp_path / "ajena.sqlite3"
    with closing(sqlite3.connect(ajena)) as conexion:
        conexion.execute("CREATE TABLE ajena (id INTEGER)")
    with pytest.raises(sqlite3.DatabaseError, match="no es una base"):
        base.recuperar(ajena)
    with closing(BaseDatos(ajena)) as otra:
        with pytest.raises(sqlite3.DatabaseError, match="no es una base"):
            otra.preparar()
    assert not (base.ruta.parent / "recuperaciones").exists()


def test_respaldo_invalido_no_publica_archivo_final(base: BaseDatos) -> None:
    base.preparar()
    with closing(sqlite3.connect(base.ruta)) as conexion, conexion:
        conexion.execute("PRAGMA foreign_keys = OFF")
        conexion.execute("INSERT INTO capacitaciones VALUES (404, 'audio')")
    with pytest.raises(sqlite3.DatabaseError, match="integridad"):
        base.respaldar()
    assert list((base.ruta.parent / "respaldos").iterdir()) == []


def test_ubicacion_usa_el_directorio_privado_de_windows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert ruta_base_local() == tmp_path / "GeneradorAsignacionesV2" / "programa.sqlite3"
