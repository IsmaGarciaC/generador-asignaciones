from collections.abc import Iterator
from contextlib import closing
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from generador_asignaciones_v2.dominio.programa import Borrador, Plaza
from generador_asignaciones_v2.dominio.puestos import Puesto
from generador_asignaciones_v2.flujo_mensual import generar
from generador_asignaciones_v2.persistencia.base_datos import BaseDatos
from generador_asignaciones_v2.persistencia.programas import Programas

PRIMERA = date(2026, 12, 1)
SEGUNDA = date(2026, 12, 8)
BLOQUEADA = (PRIMERA, Puesto.MICROFONOS, 2)


@pytest.fixture
def programas(tmp_path: Path) -> Iterator[Programas]:
    with closing(BaseDatos(tmp_path / "perfil" / "programa.sqlite3")) as base:
        base.preparar()
        ops = Programas(base)
        puestos = [Puesto.MICROFONOS] * 4 + [Puesto.AUDIO, Puesto.VIDEO]
        personas = [
            ops.guardar_persona(None, f"Persona {i}", "", frozenset({puesto}), True)
            for i, puesto in enumerate(puestos, 1)
        ]
        vista = ops.leer(2026, 12)
        plan = {
            BLOQUEADA: personas[0],
            (PRIMERA, Puesto.MICROFONOS, 1): personas[1],
            (PRIMERA, Puesto.AUDIO, 1): personas[4],
            (SEGUNDA, Puesto.VIDEO, 1): personas[5],
        }
        borrador = replace(vista.borrador, plan=plan, bloqueos=frozenset({BLOQUEADA}))
        ops.guardar(vista, borrador)
        yield ops


@pytest.mark.parametrize("alcance", [None, PRIMERA, Puesto.MICROFONOS])
def test_regeneracion_respeta_bloqueo_y_alcance_tras_reabrir(
    programas: Programas,
    alcance: date | Puesto | None,
) -> None:
    anterior = programas.leer(2026, 12)
    programas.publicar(anterior, acepta_vacantes=True)
    publicada = programas.leer_publicacion(2026, 12)
    with closing(BaseDatos(programas.base.ruta)) as reabierta:
        ops = Programas(reabierta)
        vista = ops.leer(2026, 12)
        assert vista.borrador.bloqueos == frozenset({BLOQUEADA})
        resultado = generar(ops, vista, vista.borrador, alcance=alcance)
        assert resultado.plan is not None
        assert len(resultado.plan) > len(vista.borrador.plan)
        assert resultado.plan[BLOQUEADA] == vista.borrador.plan[BLOQUEADA]
        for plaza in vista.contexto.plazas():
            if alcance is not None and alcance not in plaza[:2]:
                assert resultado.plan.get(plaza) == vista.borrador.plan.get(plaza)
        posterior = ops.leer(2026, 12)
        assert posterior.borrador.plan == resultado.plan
        assert posterior.borrador.bloqueos == frozenset({BLOQUEADA})
        assert not posterior.publicado_al_dia
        assert ops.leer_publicacion(2026, 12) == publicada


def test_ausencia_invalida_bloqueo_e_impide_guardar_regenerar_o_publicar(
    programas: Programas,
) -> None:
    anterior = programas.leer(2026, 12)
    persona = anterior.borrador.plan[BLOQUEADA]
    programas.guardar_ausencias(2026, 12, persona, frozenset({PRIMERA}))
    vista = programas.leer(2026, 12)
    motivo = r"01/12 · microfonos 2: bloqueo inválido, .*ausencia registrada"
    with pytest.raises(ValueError, match=motivo):
        generar(programas, vista, vista.borrador)
    with pytest.raises(ValueError, match=motivo):
        programas.guardar(vista, vista.borrador)
    with pytest.raises(ValueError, match=motivo):
        programas.publicar(vista, acepta_vacantes=True)
    assert programas.leer(2026, 12).borrador == anterior.borrador
    desbloqueado = replace(vista.borrador, bloqueos=frozenset())
    resultado = generar(programas, vista, desbloqueado)
    assert resultado.plan is not None
    assert all(i != persona for (semana, _, _), i in resultado.plan.items() if semana == PRIMERA)


def test_editar_una_plaza_bloqueada_requiere_desbloquearla(programas: Programas) -> None:
    vista = programas.leer(2026, 12)
    nuevo = vista.borrador.plan[BLOQUEADA] + 2
    modificado = replace(vista.borrador, plan={**vista.borrador.plan, BLOQUEADA: nuevo})
    with pytest.raises(ValueError, match="desbloquea la plaza"):
        programas.guardar(vista, modificado)
    programas.guardar(vista, replace(modificado, bloqueos=frozenset()))
    vigente = programas.leer(2026, 12)
    assert vigente.borrador.plan[BLOQUEADA] == nuevo
    assert BLOQUEADA not in vigente.borrador.bloqueos


def test_bloquear_una_vacante_no_se_puede_guardar(programas: Programas) -> None:
    vista = programas.leer(2026, 12)
    vacante: Plaza = (PRIMERA, Puesto.VIDEO, 1)
    borrador: Borrador = replace(vista.borrador, bloqueos=vista.borrador.bloqueos | {vacante})
    with pytest.raises(ValueError, match="el bloqueo requiere una persona"):
        programas.guardar(vista, borrador)
    assert programas.leer(2026, 12).borrador == vista.borrador


def test_alternativa_equivalente_solo_cambia_el_puesto_elegido(tmp_path: Path) -> None:
    with closing(BaseDatos(tmp_path / "perfil" / "programa.sqlite3")) as base:
        base.preparar()
        programas = Programas(base)
        a = programas.guardar_persona(None, "Persona A", "", frozenset({Puesto.AUDIO}), True)
        b = programas.guardar_persona(None, "Persona B", "", frozenset({Puesto.AUDIO}), True)
        c = programas.guardar_persona(None, "Persona C", "", frozenset({Puesto.VIDEO}), True)
        vista = programas.leer(2026, 12)
        semanas = tuple(
            replace(s, martes=False, domingo=False) if s.inicio != PRIMERA else s
            for s in vista.borrador.semanas
        )
        audio = PRIMERA, Puesto.AUDIO, 1
        video = PRIMERA, Puesto.VIDEO, 1
        programas.guardar(
            vista,
            replace(
                vista.borrador,
                semanas=semanas,
                plan={audio: a, video: c},
                bloqueos=frozenset({video}),
            ),
        )
        vista = programas.leer(2026, 12)
        primera = generar(programas, vista, vista.borrador, alcance=Puesto.AUDIO)
        assert primera.plan == {audio: b, video: c}
        vista = programas.leer(2026, 12)
        segunda = generar(programas, vista, vista.borrador, alcance=Puesto.AUDIO)
        assert segunda.plan == {audio: a, video: c}
