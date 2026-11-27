"""Restricciones de edición que se aplican antes de ejecutar el motor mensual."""

from collections import defaultdict
from dataclasses import replace
from datetime import date
from secrets import randbelow

from ortools.sat.python import cp_model as cp

from generador_asignaciones_v2.dominio.programa import Asignaciones, Contexto, Plaza
from generador_asignaciones_v2.dominio.puestos import Puesto
from generador_asignaciones_v2.optimizador import Modelo, Resultado, _optimizar, _turnos, resolver

type Alcance = date | Puesto | None
type Fijas = dict[Plaza, int | None]


def _modelo_con_fijas(contexto: Contexto, fijas: Fijas) -> Modelo:
    modelo = Modelo(contexto)
    variables_por_puesto = defaultdict(list)
    for (plaza, persona), variable in modelo.asigna.items():
        variables_por_puesto[plaza[:2]].append((persona, variable))
    vacantes = defaultdict(int)
    for plaza, persona in fijas.items():
        grupo = plaza[:2]
        if persona is None:
            vacantes[grupo] += 1
        else:
            # Los cupos son equivalentes para calcular el reparto. Se colocan al final.
            modelo.cp.add(
                sum(v for candidato, v in variables_por_puesto[grupo] if candidato == persona) == 1
            )
    if vacantes:
        cupos = defaultdict(int)
        for plaza in contexto.plazas():
            cupos[plaza[:2]] += 1
        for grupo, cantidad in vacantes.items():
            modelo.cp.add(sum(v for _, v in variables_por_puesto[grupo]) <= cupos[grupo] - cantidad)
    return modelo


def _restituir_cupos(contexto: Contexto, plan: Asignaciones, fijas: Fijas) -> Asignaciones:
    if not fijas:
        return plan
    grupos = {plaza[:2] for plaza in fijas}
    ocupadas_fijas = {(plaza[:2], persona) for plaza, persona in fijas.items()}
    restantes = defaultdict(list)
    salida = {}
    for plaza, persona in sorted(plan.items()):
        grupo = plaza[:2]
        if grupo not in grupos:
            salida[plaza] = persona
        elif (grupo, persona) not in ocupadas_fijas:
            restantes[grupo].append(persona)
    for plaza in contexto.plazas():
        grupo = plaza[:2]
        if plaza in fijas:
            if (persona := fijas[plaza]) is not None:
                salida[plaza] = persona
        elif grupo in grupos and restantes[grupo]:
            salida[plaza] = restantes[grupo].pop(0)
    return salida


def _alternativa(
    contexto: Contexto,
    fijas: Fijas,
    resultado: Resultado,
    plan: Asignaciones,
) -> Resultado:
    modelo = _modelo_con_fijas(contexto, fijas)
    objetivos = [objetivo for _, objetivo in modelo.objetivos()]
    referencia = modelo.cp.clone()
    for (plaza, persona), variable in modelo.asigna.items():
        ref = referencia.get_bool_var_from_proto_index(variable.index)
        referencia.add(ref == int(plan.get(plaza) == persona))
    referencia.minimize(sum(objetivos))
    solver = cp.CpSolver()
    solver.parameters.max_time_in_seconds = 5
    solver.parameters.num_search_workers = 1
    if solver.solve(referencia) != cp.OPTIMAL:
        return replace(resultado, aviso_variacion="sin_resultado")
    for objetivo in objetivos:
        modelo.cp.add(objetivo <= solver.value(objetivo))
    turnos = _turnos(plan)
    compartidos = sum(
        variable
        for ((fecha, puesto, _), persona), variable in modelo.asigna.items()
        if (fecha, puesto, persona) in turnos
    )
    modelo.cp.add(compartidos < len(turnos))
    modelo.cp.minimize(compartidos)
    solver.parameters.num_search_workers = 4
    solver.parameters.random_seed = randbelow(2**31 - 1)
    solver.parameters.randomize_search = True
    estado = solver.solve(modelo.cp)
    if estado in (cp.OPTIMAL, cp.FEASIBLE):
        return replace(resultado, plan=modelo.leer_plan(solver))
    aviso = "única" if estado == cp.INFEASIBLE else "sin_resultado"
    return replace(resultado, aviso_variacion=aviso)


def regenerar(
    contexto: Contexto,
    anterior: Asignaciones,
    bloqueos: frozenset[Plaza],
    alcance: Alcance,
) -> Resultado:
    def dentro(plaza: Plaza) -> bool:
        return alcance is None or alcance == plaza[0] or alcance == plaza[1]

    requeridas = contexto.plazas()
    if alcance is not None and not any(dentro(plaza) for plaza in requeridas):
        raise ValueError("El alcance elegido no tiene plazas requeridas.")

    conservadas = {
        plaza: persona
        for plaza, persona in anterior.items()
        if plaza in bloqueos or not dentro(plaza)
    }
    if errores := contexto.validar(conservadas, bloqueos=bloqueos):
        raise ValueError("\n".join(errores))
    fijas = {
        plaza: anterior.get(plaza) for plaza in requeridas if plaza in bloqueos or not dentro(plaza)
    }
    if not fijas:
        return resolver(contexto, anterior=anterior)

    resultado = _optimizar(_modelo_con_fijas(contexto, fijas), 5)
    if resultado.plan is None:
        return resultado
    if resultado.plan and _turnos(resultado.plan) == _turnos(anterior):
        resultado = _alternativa(contexto, fijas, resultado, resultado.plan)
    if resultado.plan is None:
        return resultado
    return replace(resultado, plan=_restituir_cupos(contexto, resultado.plan, fijas))
