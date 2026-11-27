from collections.abc import Iterator
from contextlib import closing
from dataclasses import replace
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from sqlalchemy import select

from generador_asignaciones_v2.dominio.puestos import Puesto
from generador_asignaciones_v2.dominio.recordatorios import Configuracion, semana_actual
from generador_asignaciones_v2.persistencia.base_datos import BaseDatos
from generador_asignaciones_v2.persistencia.modelos import EnvioRecordatorio
from generador_asignaciones_v2.persistencia.programas import Programas
from generador_asignaciones_v2.persistencia.recordatorios import Recordatorios


@pytest.fixture
def programas(tmp_path: Path) -> Iterator[Programas]:
    with closing(BaseDatos(tmp_path / "programa.sqlite3")) as base:
        base.preparar()
        yield Programas(base)


def test_ronda_usa_solo_semanas_publicadas_y_agrupa_doblete(programas: Programas) -> None:
    recordatorios = Recordatorios(programas.base)
    roles = frozenset({Puesto.LECTOR_MARTES, Puesto.MICROFONOS, Puesto.PRESIDENTE})
    persona = programas.guardar_persona(None, "Persona Álvarez", "+1 (202) 555-0101", roles, True)
    otra = programas.guardar_persona(None, "Persona B", "", roles, True)
    vista = programas.leer(2026, 12)
    primera, segunda, tercera, *resto = vista.borrador.semanas
    plan = {
        (primera.inicio, Puesto.MICROFONOS, 1): persona,
        (primera.inicio, Puesto.LECTOR_MARTES, 1): persona,
        (primera.inicio, Puesto.PRESIDENTE, 1): otra,
        (segunda.inicio, Puesto.MICROFONOS, 1): otra,
    }
    semanas = (primera, segunda, replace(tercera, martes=False, domingo=False), *resto)
    programas.guardar(vista, replace(vista.borrador, plan=plan, semanas=semanas))
    assert not recordatorios.semanas()
    assert recordatorios.leer(primera.inicio).version is None

    programas.publicar(programas.leer(2026, 12), acepta_vacantes=True)
    assert semana_actual(date(2026, 12, 1)) == primera.inicio
    assert semana_actual(date(2027, 1, 3)) == date(2026, 12, 29)
    assert recordatorios.semanas() == tuple(s.inicio for s in semanas)
    (mensaje,) = recordatorios.leer(primera.inicio).recordatorios
    assert mensaje.puestos == (Puesto.MICROFONOS, Puesto.LECTOR_MARTES)
    enlace = urlsplit(recordatorios.verificar(mensaje, reenvio=False))
    assert (enlace.scheme, enlace.netloc, enlace.path) == ("https", "wa.me", "/12025550101")
    assert parse_qs(enlace.query)["text"] == [mensaje.mensaje]
    assert "Micrófonos" in mensaje.mensaje and "Lector del martes" in mensaje.mensaje
    (sin_telefono,) = recordatorios.leer(segunda.inicio).recordatorios
    assert sin_telefono.persona == otra
    with pytest.raises(ValueError, match="teléfono"):
        recordatorios.verificar(sin_telefono, reenvio=False)
    assert recordatorios.leer(tercera.inicio).cancelada
    assert not recordatorios.leer(tercera.inicio).recordatorios

    with pytest.raises(ValueError, match="solo los campos"):
        recordatorios.guardar_configuracion(Configuracion(roles, "{nombre.__class__}"))
    recordatorios.guardar_configuracion(
        Configuracion(frozenset({Puesto.PRESIDENTE}), "Aviso para {nombre}\n{puestos}")
    )
    (alternativo,) = Recordatorios(programas.base).leer(primera.inicio).recordatorios
    assert alternativo.persona == otra
    assert alternativo.mensaje == "Aviso para Persona B\n• Presidente"


def test_confirmaciones_sobreviven_reapertura_y_republicacion(programas: Programas) -> None:
    puesto = Puesto.AUDIO
    persona = programas.guardar_persona(None, "Persona A", "12025550101", frozenset({puesto}), True)
    vista = programas.leer(2026, 12)
    primera, segunda, *_ = vista.borrador.semanas
    plan = {(primera.inicio, puesto, 1): persona}
    programas.guardar(vista, replace(vista.borrador, plan=plan))
    assert programas.publicar(programas.leer(2026, 12), acepta_vacantes=True) == 1
    recordatorios = Recordatorios(programas.base)
    (mensaje,) = recordatorios.leer(primera.inicio).recordatorios
    recordatorios.verificar(mensaje, reenvio=False)
    assert recordatorios.leer(primera.inicio).recordatorios == (mensaje,)
    recordatorios.confirmar(mensaje, reenvio=False)
    with pytest.raises(ValueError, match="ronda cambió"):
        recordatorios.confirmar(mensaje, reenvio=False)

    vista = programas.leer(2026, 12)
    plan[segunda.inicio, puesto, 1] = persona
    programas.guardar(vista, replace(vista.borrador, plan=plan))
    assert programas.publicar(programas.leer(2026, 12), acepta_vacantes=True) == 2

    with closing(BaseDatos(programas.base.ruta)) as base:
        base.preparar()
        reabiertos = Recordatorios(base)
        (confirmado,) = reabiertos.leer(primera.inicio).recordatorios
        assert confirmado.confirmaciones == 1
        assert (confirmado.ultima_version, confirmado.version) == (1, 2)
        with pytest.raises(ValueError, match="acción de reenvío"):
            reabiertos.verificar(confirmado, reenvio=False)
        reabiertos.verificar(confirmado, reenvio=True)
        reabiertos.confirmar(confirmado, reenvio=True)
        with pytest.raises(ValueError, match="ronda cambió"):
            reabiertos.confirmar(confirmado, reenvio=True)
        with base.transaccion() as sesion:
            envios = sesion.scalars(select(EnvioRecordatorio).order_by(EnvioRecordatorio.numero))
            assert [(e.numero, e.version) for e in envios] == [(1, 1), (2, 2)]
