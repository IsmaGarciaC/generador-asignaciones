"""Optimización mensual lexicográfica con CP-SAT."""

from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass, replace
from datetime import date, timedelta
from itertools import combinations, pairwise
from secrets import randbelow
from typing import Literal

from ortools.sat.python import cp_model as cp

from generador_asignaciones_v2.dominio.programa import Asignaciones, Contexto, Plaza
from generador_asignaciones_v2.dominio.puestos import PUESTOS_COMPATIBLES_CON_LECTOR, Puesto


@dataclass(frozen=True)
class Resultado:
    estado: str
    plan: Asignaciones | None
    objetivos_probados: tuple[str, ...]
    aviso_variacion: Literal["única", "sin_resultado"] | None = None


class Modelo:
    def __init__(self, contexto: Contexto) -> None:
        self.contexto = contexto
        self.cp = cp.CpModel()
        self.asigna: dict[tuple[Plaza, int], cp.IntVar] = {}
        self.servicios = defaultdict(list)
        self.por_rol = defaultdict(list)
        self.trabaja = {}
        self.dobles = []
        rangos = {persona: i for i, persona in enumerate(sorted(contexto.personas), 1)}
        orden = {}
        for plaza in contexto.plazas():
            inicio, puesto, cupo = plaza
            variables = []
            candidatos = contexto.candidatos(plaza)
            for persona in candidatos:
                variable = self.cp.new_bool_var(f"{inicio}_{puesto}_{cupo}_{persona}")
                self.asigna[plaza, persona] = variable
                self.servicios[persona].append(variable)
                self.por_rol[persona, inicio, puesto].append(variable)
                variables.append(variable)
            self.cp.add_at_most_one(variables)
            # Las dos plazas de un puesto son equivalentes. Coloca los huecos al final.
            orden[plaza] = sum(
                (rangos[persona] - len(rangos) - 1) * self.asigna[plaza, persona]
                for persona in candidatos
            )
            if cupo > 1:
                self.cp.add(orden[inicio, puesto, cupo - 1] <= orden[plaza])

        for persona in contexto.personas.values():
            for semana in contexto.semanas:
                inicio = semana.inicio
                lector = self.por_rol[persona.id, inicio, Puesto.LECTOR_MARTES]
                otros = []
                incompatibles = []
                for puesto in sorted(persona.puestos - {Puesto.LECTOR_MARTES}):
                    variables = self.por_rol[persona.id, inicio, puesto]
                    otros.extend(variables)
                    if puesto not in PUESTOS_COMPATIBLES_CON_LECTOR:
                        incompatibles.extend(variables)
                self.cp.add_at_most_one(otros)
                self.cp.add_at_most_one(lector + incompatibles)
                trabaja = self.cp.new_bool_var("trabaja")
                doble = self.cp.new_bool_var("doblete")
                self.cp.add(sum(lector + otros) == trabaja + doble)
                self.cp.add(doble <= trabaja)
                self.trabaja[persona.id, inicio] = trabaja
                self.dobles.append(doble)

    def equidad(self, *, incluir_historial: bool) -> cp.LinearExpr | int:
        costes = []
        semanas = self.contexto.semanas
        historial = self.contexto.historial if incluir_historial else {}
        for persona in self.contexto.personas.values():
            if not persona.activa:
                continue
            pasado = [
                cantidad
                for (persona_id, _), cantidad in historial.items()
                if persona_id == persona.id
            ]
            oportunidades = len(pasado) + sum(
                not semana.cancelada and (persona.id, semana.inicio) not in self.contexto.ausencias
                for semana in semanas
            )
            if not oportunidades:
                continue
            trabajadas = [self.trabaja[persona.id, semana.inicio] for semana in semanas]
            for anteriores, variables, limite in (
                (sum(pasado), self.servicios[persona.id], 2 * len(semanas)),
                (sum(n > 0 for n in pasado), trabajadas, len(semanas)),
            ):
                if not variables:
                    continue
                incremento = self.cp.new_int_var(0, limite, "incremento")
                self.cp.add(incremento == sum(variables))
                tabla = [
                    (100 * (anteriores + i) ** 2 + oportunidades // 2) // oportunidades
                    for i in range(limite + 1)
                ]
                coste = self.cp.new_int_var(tabla[0], tabla[-1], "coste")
                # Las pendientes crecen. Esta formulación evita una restricción de
                # selección para cada valor de carga al continuar con la rotación.
                for i, (inferior, superior) in enumerate(pairwise(tabla)):
                    self.cp.add(coste >= inferior + (superior - inferior) * (incremento - i))
                costes.append(coste)
        return sum(costes)

    def repeticiones(self, variables: list) -> cp.IntVar:
        extra = self.cp.new_int_var(0, len(variables) - 1, "repeticiones")
        self.cp.add_max_equality(extra, [0, sum(variables) - 1])
        return extra

    def variedad_puestos(self) -> cp.LinearExpr | int:
        """Cada reasignación al mismo puesto cuesta más que la anterior."""
        costes = []
        for persona in self.contexto.personas.values():
            for puesto in sorted(persona.puestos):
                semanas = [
                    variables
                    for semana in self.contexto.semanas
                    if (variables := self.por_rol[persona.id, semana.inicio, puesto])
                ]
                limite = len(semanas)
                if limite <= 1:
                    continue
                usos = sum(v for variables in semanas for v in variables)
                coste = self.cp.new_int_var(0, limite * (limite - 1) // 2, "concentracion_puesto")
                for uso in range(1, limite):
                    # Envolvente lineal de n * (n - 1) / 2 para conteos enteros.
                    self.cp.add(coste >= uso * usos - uso * (uso + 1) // 2)
                costes.append(coste)
        return sum(costes)

    def _servicio_semanal(self, persona: int, previas: int) -> list[int | cp.IntVar]:
        semanas = self.contexto.semanas
        if not semanas:
            return []
        anteriores = [
            int(
                self.contexto.historial.get((persona, semanas[0].inicio - timedelta(weeks=i)), 0)
                > 0
            )
            for i in range(previas, 0, -1)
        ]
        return anteriores + [self.trabaja[persona, semana.inicio] for semana in semanas]

    def descanso(self) -> cp.LinearExpr | int:
        rachas = []
        for persona in self.contexto.personas.values():
            if not persona.activa:
                continue
            servicio = self._servicio_semanal(persona.id, previas=2)
            for i in range(len(servicio) - 2):
                racha = self.cp.new_bool_var("tres_seguidas")
                self.cp.add_min_equality(racha, servicio[i : i + 3])
                rachas.append(racha)
        return sum(rachas)

    def rotacion(self) -> cp.LinearExpr | int:
        semanas = self.contexto.semanas
        if not semanas:
            return 0
        penas = []
        equipos = defaultdict(list)
        for persona in self.contexto.personas.values():
            if not persona.activa:
                continue
            servicio = self._servicio_semanal(persona.id, previas=1)
            for i in range(len(servicio) - 1):
                seguida = self.cp.new_bool_var("servicio_consecutivo")
                self.cp.add_min_equality(seguida, servicio[i : i + 2])
                penas.append(seguida)
            for puesto in sorted(persona.puestos):
                anterior = int(
                    (persona.id, semanas[0].inicio - timedelta(weeks=1), puesto)
                    in self.contexto.puestos_historicos
                )
                for semana in semanas:
                    variables = self.por_rol[persona.id, semana.inicio, puesto]
                    presente = sum(variables)
                    if variables:
                        consecutiva = self.cp.new_bool_var("puesto_consecutivo")
                        self.cp.add_min_equality(consecutiva, [anterior, presente])
                        penas.append(2 * consecutiva)
                    anterior = presente
                    if variables and puesto in (Puesto.MICROFONOS, Puesto.ACOMODADOR):
                        equipos[semana.inicio, puesto].append((persona.id, presente))
        encuentros = defaultdict(list)
        for (_, puesto), personas in equipos.items():
            for (a, uno), (b, otro) in combinations(personas, 2):
                juntos = self.cp.new_bool_var("pareja")
                self.cp.add_min_equality(juntos, [uno, otro])
                encuentros[puesto, min(a, b), max(a, b)].append(juntos)
        penas.extend(self.repeticiones(veces) for veces in encuentros.values() if len(veces) > 1)
        return sum(penas)

    def objetivos(self) -> Iterator[tuple[str, cp.LinearExpr | int]]:
        yield "cobertura", -sum(self.asigna.values())
        yield "dobletes", sum(self.dobles)
        yield "variedad de puestos", self.variedad_puestos()
        yield "carga del mes", self.equidad(incluir_historial=False)
        yield "equidad histórica", self.equidad(incluir_historial=True)
        yield "descanso tras dos semanas", self.descanso()
        yield "rotación de parejas y puestos", self.rotacion()

    def leer_plan(self, solver: cp.CpSolver) -> Asignaciones:
        return {
            plaza: persona for (plaza, persona), var in self.asigna.items() if solver.value(var)
        }


def _optimizar(modelo: Modelo, segundos: float) -> Resultado:
    plan = None
    probados = []
    for nombre, objetivo in modelo.objetivos():
        modelo.cp.minimize(objetivo)
        solver = cp.CpSolver()
        # La variedad se resuelve antes de agregar las variables de las parejas.
        preferencias = nombre not in ("cobertura", "dobletes")
        solver.parameters.max_time_in_seconds = segundos * (
            2
            if nombre
            in ("variedad de puestos", "descanso tras dos semanas", "rotación de parejas y puestos")
            else 1
        )
        solver.parameters.num_search_workers = 4 if preferencias else 1
        solver.parameters.random_seed = 73
        estado = solver.solve(modelo.cp)
        if estado == cp.UNKNOWN and plan is not None:
            return Resultado("FEASIBLE", plan, tuple(probados))
        if estado not in (cp.OPTIMAL, cp.FEASIBLE):
            return Resultado(solver.status_name(estado), None, tuple(probados))
        plan = modelo.leer_plan(solver)
        if estado == cp.FEASIBLE:
            return Resultado("FEASIBLE", plan, tuple(probados))
        probados.append(nombre)
        modelo.cp.add(objetivo == solver.value(objetivo))
        modelo.cp.clear_hints()
        for variable in modelo.asigna.values():
            modelo.cp.add_hint(variable, solver.value(variable))
    return Resultado("OPTIMAL", plan, tuple(probados))


def _turnos(plan: Asignaciones) -> set[tuple[date, Puesto, int]]:
    return {(fecha, puesto, persona) for (fecha, puesto, _), persona in plan.items()}


def _buscar_alternativa(
    contexto: Contexto,
    resultado: Resultado,
    plan: Asignaciones,
    segundos: float,
) -> Resultado:
    modelo = Modelo(contexto)
    objetivos = [objetivo for _, objetivo in modelo.objetivos()]
    referencia = modelo.cp.clone()
    for (plaza, persona), variable in modelo.asigna.items():
        ref = referencia.get_bool_var_from_proto_index(variable.index)
        referencia.add(ref == int(plan.get(plaza) == persona))
    # Con las asignaciones fijas, cada término alcanza su coste real sin competir con otro.
    referencia.minimize(sum(objetivos))
    solver = cp.CpSolver()
    solver.parameters.max_time_in_seconds = segundos
    solver.parameters.num_search_workers = 1
    if solver.solve(referencia) != cp.OPTIMAL:
        return replace(resultado, aviso_variacion="sin_resultado")
    for objetivo in objetivos:
        modelo.cp.add(objetivo <= solver.value(objetivo))

    turnos = _turnos(plan)
    compartidos = sum(
        var
        for ((fecha, puesto, _), persona), var in modelo.asigna.items()
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


def resolver(
    contexto: Contexto,
    segundos: float = 5.0,
    *,
    anterior: Asignaciones | None = None,
) -> Resultado:
    resultado = _optimizar(Modelo(contexto), segundos)
    if resultado.plan and anterior and _turnos(resultado.plan) == _turnos(anterior):
        return _buscar_alternativa(contexto, resultado, resultado.plan, segundos)
    return resultado
