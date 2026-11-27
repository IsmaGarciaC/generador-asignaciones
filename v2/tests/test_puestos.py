from itertools import combinations_with_replacement

import pytest

from generador_asignaciones_v2.dominio.puestos import (
    CUPOS_HABITUALES,
    Puesto,
    combinacion_semanal_valida,
)


def test_cupos_de_semana_habitual() -> None:
    assert set(CUPOS_HABITUALES) == set(Puesto)
    assert {puesto for puesto, cupo in CUPOS_HABITUALES.items() if cupo == 2} == {
        Puesto.ACOMODADOR,
        Puesto.MICROFONOS,
    }
    assert all(cupo in (1, 2) for cupo in CUPOS_HABITUALES.values())
    assert sum(CUPOS_HABITUALES.values()) == 10


@pytest.mark.parametrize("primero,segundo", list(combinations_with_replacement(Puesto, 2)))
def test_combinaciones_de_dos_plazas(primero: Puesto, segundo: Puesto) -> None:
    permitidas = {
        frozenset((Puesto.LECTOR_MARTES, Puesto.MICROFONOS)),
        frozenset((Puesto.LECTOR_MARTES, Puesto.PLATAFORMA)),
        frozenset((Puesto.LECTOR_MARTES, Puesto.PRESIDENTE)),
    }
    esperada = frozenset((primero, segundo)) in permitidas
    assert combinacion_semanal_valida((primero, segundo)) == esperada
    assert combinacion_semanal_valida((segundo, primero)) == esperada


def test_sin_asignaciones_o_con_una_sola_plaza() -> None:
    assert combinacion_semanal_valida(())
    assert all(combinacion_semanal_valida((puesto,)) for puesto in Puesto)


def test_no_se_puede_anadir_una_tercera_plaza_a_un_doblete() -> None:
    assert not combinacion_semanal_valida(
        (Puesto.LECTOR_MARTES, Puesto.MICROFONOS, Puesto.PLATAFORMA)
    )
