"""Suite aislada del spike, descubierta con su pytest.ini local."""

from dataclasses import replace
from itertools import combinations, product

import pytest
from datos import PUESTO, Mes, Persona
from evaluacion import infracciones, metricas
from ortools.sat.python import cp_model as cp
from solver import resolver


def persona(numero, *roles, **kwargs):
    return Persona(numero, frozenset(roles), **kwargs)


def optimo(mes):
    resultado = resolver(mes)
    assert resultado.estado == "OPTIMAL", resultado.etapas
    assert resultado.plan is not None
    assert not infracciones(mes, resultado.plan)
    return resultado


@pytest.mark.parametrize("semanas", [4, 5])
def test_mes_ordinario_completo(semanas):
    personas = tuple(persona(i, rol) for i, rol in enumerate(PUESTO.values(), 1))
    mes = Mes(personas, (tuple(PUESTO),) * semanas)
    r = optimo(mes)
    assert len(r.plan) == 10 * semanas
    assert r.vacantes == ()
    assert metricas(mes, r.plan)["dobletes"] == 0


def test_vacante_evitable_del_greedy():
    mes = Mes((persona(1, "audio", "video"), persona(2, "audio")), (("audio", "video"),))
    usados = set()
    for plaza in mes.semanas[0]:
        for p in mes.personas:
            if plaza in p.puestos and p.id not in usados:
                usados.add(p.id)
                break
    assert len(usados) == 1
    assert len(optimo(mes).plan) == 2


def test_capacitacion_ausencia_inactividad_y_vacante():
    mes = Mes(
        (
            persona(1, "audio", ausencias={2}),
            persona(2, "audio", activa=False),
            persona(3, "video"),
        ),
        (("audio",), ("audio",)),
    )
    r = optimo(mes)
    assert r.plan == ((1, "audio", 1),)
    assert r.vacantes == ((2, "audio"),)


def test_cancelaciones_y_puestos_desactivados():
    p = persona(1, "audio", "video")
    mes = Mes((p,), (("audio",), ("audio", "video")), canceladas={2})
    assert optimo(mes).plan == ((1, "audio", 1),)
    assert mes.oportunidades(p) == 1
    for fila in [(2, "audio", 1), (1, "video", 1)]:
        r = resolver(replace(mes, bloqueos=(fila,)))
        assert r.estado == "INFEASIBLE"
        assert "no requerida" in " ".join(r.diagnostico)


PARES_ADMITIDOS = {
    frozenset({"lector_martes", "microfonos"}),
    frozenset({"lector_martes", "plataforma"}),
    frozenset({"lector_martes", "presidente"}),
}


@pytest.mark.parametrize("a,b", list(combinations(dict.fromkeys(PUESTO.values()), 2)))
def test_todas_las_parejas_de_puestos(a, b):
    plazas = tuple(next(p for p, rol in PUESTO.items() if rol == r) for r in (a, b))
    mes = Mes((persona(1, a, b),), (plazas,))
    r = optimo(mes)
    permitido = frozenset({a, b}) in PARES_ADMITIDOS
    assert len(r.plan) == 1 + permitido
    assert metricas(mes, r.plan)["dobletes"] == int(permitido)


@pytest.mark.parametrize(
    "plazas",
    [
        ("microfonos_1", "microfonos_2"),
        ("acomodador_1", "acomodador_2"),
        ("lector_martes", "presidente", "plataforma"),
    ],
)
def test_maximo_semanal_y_plazas_del_mismo_puesto(plazas):
    mes = Mes((persona(1, *(PUESTO[p] for p in plazas)),), (plazas,))
    assert len(optimo(mes).plan) == len(plazas) - 1
    bloqueos = tuple((1, p, 1) for p in plazas)
    r = resolver(replace(mes, bloqueos=bloqueos))
    assert r.estado == "INFEASIBLE" and r.plan is None
    assert "combinación prohibida" in " ".join(r.diagnostico)


def test_bloqueo_valido_y_bloqueos_incompatibles():
    mes = Mes(
        (persona(1, "audio"), persona(2, "audio")), (("audio",),), bloqueos=((1, "audio", 2),)
    )
    assert optimo(mes).plan == mes.bloqueos
    for fila, motivo in [
        ((1, "audio", 1), "más de una vez"),
        ((2, "audio", 2), "no requerida"),
        ((1, "audio", 99), "desconocido"),
    ]:
        r = resolver(replace(mes, bloqueos=mes.bloqueos + (fila,)))
        assert r.etapas[0].estado == "INFEASIBLE"
        assert motivo in " ".join(r.diagnostico)


def test_persona_bloqueada_pierde_disponibilidad():
    p = persona(4, "audio", ausencias={1})
    mes = Mes((p,), (("audio",),), bloqueos=((1, "audio", 4),))
    r = resolver(mes)
    assert r.estado == "INFEASIBLE" and r.plan is None
    assert "Semana 1, audio, ID 4: ausente" in r.diagnostico


def test_equidad_y_descanso_ceden_ante_cobertura_y_dobletes():
    lector = persona(1, "lector_martes", "plataforma", historial=((0, 0, 0, 0), (), ()))
    cargado = persona(2, "plataforma", historial=((), (), (2, 2, 2, 2)))
    mes = Mes((lector, cargado), (("lector_martes", "plataforma"),))
    r = optimo(mes)
    alternativa = ((1, "lector_martes", 1), (1, "plataforma", 1))
    assert not infracciones(mes, alternativa)
    assert metricas(mes, alternativa)["equidad"] < metricas(mes, r.plan)["equidad"]
    assert len(r.plan) == 2 and metricas(mes, r.plan)["dobletes"] == 0
    escaso = replace(mes, personas=(lector,))
    assert len(optimo(escaso).plan) == 2
    assert metricas(escaso, alternativa)["equidad"] > metricas(escaso, alternativa[:1])["equidad"]


def test_equidad_mejora_sin_incentivo_por_mas_capacitaciones():
    p = persona(1, "audio", "video", "presidente", historial=((1, 1), (1,), (1,)))
    q = persona(2, "audio", historial=((0, 0), (0,), (0,)))
    mes = Mes((p, q), (("audio",),) * 2)
    r = optimo(mes)
    alternativa = ((1, "audio", 1), (2, "audio", 2))
    assert metricas(mes, r.plan)["equidad"] < metricas(mes, alternativa)["equidad"]
    assert all(i == 2 for _, _, i in r.plan)


def test_ausencias_desconocidos_cancelaciones_y_doblete():
    p = persona(
        1,
        "lector_martes",
        "presidente",
        ausencias={3},
        historial=((2, None), ("ausente",), ("cancelada", 0)),
    )
    mes = Mes((p,), (("lector_martes", "presidente"), ("presidente",), ("presidente",)), {2})
    r = optimo(mes)
    assert mes.oportunidades(p) == 3  # dos históricas y una del mes
    m = metricas(mes, r.plan)
    assert (m["carga"], m["frecuencia"]) == (533, 133)  # cuatro asignaciones, dos semanas
    sin_ausencias = replace(p, historial=((2,), (), (0,)))
    reducido = Mes((sin_ausencias,), (mes.semanas[0],))
    assert metricas(reducido, r.plan)["equidad"] == m["equidad"]


def test_oportunidades_cero():
    p = persona(1, "audio", historial=((None,), ("ausente",), (None,)))
    mes = Mes((p,), (("audio",),), {1})
    r = optimo(mes)
    assert r.plan == () and mes.oportunidades(p) == 0
    assert metricas(mes, r.plan)["equidad"] == 0


def test_equidad_tiene_prioridad_sobre_racha():
    p = persona(1, "audio", historial=((), (), (0, 0, 1, 1)))
    q = persona(2, "audio", historial=((), (), (2, 2, 0, 0)))
    mes = Mes((p, q), (("audio",),))
    elegido = metricas(mes, optimo(mes).plan)
    alterno = metricas(mes, ((1, "audio", 2),))
    assert elegido["equidad"] < alterno["equidad"]
    assert elegido["rachas"] == 1 and alterno["rachas"] == 0


def test_descanso_tras_dos_semanas_consecutivas():
    p = persona(1, "audio", historial=((), (), (0, 0, 1, 1)))
    q = persona(2, "audio", historial=((), (), (1, 1, 0, 0)))
    mes = Mes((p, q), (("audio",),))
    r = optimo(mes)
    excluido = metricas(mes, ((1, "audio", 1),))
    m = metricas(mes, r.plan)
    assert m["equidad"] == excluido["equidad"]
    assert m["rachas"] == 0 < excluido["rachas"]


@pytest.mark.parametrize("historial", [((1,), (), (1,)), ((), (1, 1), ())])
def test_mes_historico_desconocido_interrumpe_racha(historial):
    p = persona(1, "audio", historial=historial)
    mes = Mes((p,), (("audio",),))
    r = optimo(mes)
    assert r.plan == ((1, "audio", 1),)
    assert mes.oportunidades(p) == 3
    assert metricas(mes, r.plan)["rachas"] == r.etapas[-1].valor == 0


def test_rotan_puestos():
    mes = Mes(tuple(persona(i, "audio", "video") for i in (1, 2)), (("audio", "video"),) * 2)
    assert metricas(mes, optimo(mes).plan)["puestos"] == 0


@pytest.mark.parametrize("rol", ["acomodador", "microfonos"])
def test_rotan_parejas_sin_importar_orden(rol):
    plazas = (rol + "_1", rol + "_2")
    mes = Mes(tuple(persona(i, rol) for i in range(4)), (plazas,) * 4)
    m = metricas(mes, optimo(mes).plan)
    assert m["cobertura"] == 8 and m[rol] == 0
    repetida = ((1, plazas[0], 1), (1, plazas[1], 2), (2, plazas[0], 2), (2, plazas[1], 1))
    assert metricas(mes, repetida)[rol] == 1


def test_unknown_real_sin_plan():
    mes = Mes((persona(1, "audio"),), (("audio",),))
    r = resolver(mes, segundos=0)
    assert r.estado == "UNKNOWN" and r.plan is None
    assert len(r.etapas) == 1 and r.etapas[0].valor is None


def test_oraculo_exhaustivo_de_las_cuatro_prioridades():
    mes = Mes(
        (
            persona(1, "lector_martes", "plataforma", historial=((1,), (), (0,))),
            persona(2, "plataforma", ausencias={2}),
        ),
        (("lector_martes", "plataforma"),) * 2,
    )

    def prioridades(plan):
        m = metricas(mes, plan)
        rotacion = sum(m[k] for k in ("rachas", "puestos", "microfonos", "acomodador"))
        return -m["cobertura"], m["dobletes"], m["equidad"], rotacion

    alternativas = []
    for ids in product([None, 1, 2], repeat=4):
        plan = tuple(
            (s, plaza, i)
            for (s, plaza), i in zip(mes.requeridas(), ids, strict=True)
            if i is not None
        )
        if not infracciones(mes, plan):
            alternativas.append(prioridades(plan))
    assert prioridades(optimo(mes).plan) == min(alternativas)


def test_validador_detecta_plan_corrupto_sin_consultar_solver():
    mes = Mes(
        (persona(1, "audio", "video"), persona(2, "video", ausencias={1}, activa=False)),
        (("audio", "video"),),
        bloqueos=((1, "video", 1),),
    )
    errores = infracciones(mes, ((1, "audio", 1), (1, "audio", 2), (2, "audio", 42)))
    for motivo in (
        "más de una vez",
        "inactivo",
        "ausente",
        "sin capacitación",
        "no requerida",
        "ID desconocido",
        "Bloqueo incumplido",
    ):
        assert motivo in " ".join(errores)


@pytest.mark.parametrize(
    "modo", ["factible", "tiempo_en_segunda", "modelo_invalido", "modelo_invalido_en_segunda"]
)
def test_interrupcion_lexicografica_con_estados_reales(monkeypatch, modo):
    original = cp.CpSolver.solve
    llamadas = []

    def controlado(solver, modelo):
        llamadas.append(None)
        if modo == "modelo_invalido" or (
            modo == "modelo_invalido_en_segunda" and len(llamadas) == 2
        ):
            modelo.new_int_var(2, 1, "dominio_vacio")
        elif modo == "tiempo_en_segunda" and len(llamadas) == 2:
            solver.parameters.max_time_in_seconds = 0
        elif modo == "factible":
            solver.parameters.cp_model_presolve = False
            solver.parameters.stop_after_first_solution = True
            for indice in range(len(modelo.proto.variables)):
                modelo.add_hint(modelo.get_int_var_from_proto_index(indice), 0)
        return original(solver, modelo)

    monkeypatch.setattr(cp.CpSolver, "solve", controlado)
    mes = Mes((persona(1, "audio"),), (("audio",),))
    r = resolver(mes)
    estados = [e.estado for e in r.etapas]
    if modo == "modelo_invalido":
        assert estados == ["MODEL_INVALID"] and r.diagnostico and r.plan is None
    elif modo == "modelo_invalido_en_segunda":
        assert estados == ["OPTIMAL", "MODEL_INVALID"]
        assert r.estado == "MODEL_INVALID" and r.diagnostico and r.plan is None
        assert r.vacantes == ()
    elif modo == "factible":
        assert estados == ["FEASIBLE"] and r.estado == "FEASIBLE"
        assert r.plan is not None and not infracciones(mes, r.plan)
    else:
        assert estados == ["OPTIMAL", "UNKNOWN"] and r.estado == "FEASIBLE"
        assert r.plan == ((1, "audio", 1),)
