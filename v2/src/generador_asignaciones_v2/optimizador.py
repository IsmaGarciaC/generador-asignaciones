"""Optimización mensual lexicográfica con CP-SAT."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from itertools import combinations

from ortools.sat.python import cp_model as cp

from generador_asignaciones_v2.dominio.programa import Asignaciones, Contexto, Plaza
from generador_asignaciones_v2.dominio.puestos import PUESTOS_COMPATIBLES_CON_LECTOR, Puesto


@dataclass(frozen=True)
class Resultado:
    estado: str
    plan: Asignaciones | None
    objetivos_probados: tuple[str, ...]


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

    def equidad(self) -> cp.LinearExpr | int:
        costes = []
        semanas = self.contexto.semanas
        for persona in self.contexto.personas.values():
            if not persona.activa:
                continue
            pasado = [
                cantidad
                for (persona_id, _), cantidad in self.contexto.historial.items()
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
                incremento = self.cp.new_int_var(0, limite, "incremento")
                self.cp.add(incremento == sum(variables))
                tabla = [
                    (100 * (anteriores + i) ** 2 + oportunidades // 2) // oportunidades
                    for i in range(limite + 1)
                ]
                coste = self.cp.new_int_var(tabla[0], tabla[-1], "coste")
                self.cp.add_element(incremento, tabla, coste)
                costes.append(coste)
        return sum(costes)

    def repeticiones(self, variables: list) -> cp.IntVar:
        extra = self.cp.new_int_var(0, len(variables) - 1, "repeticiones")
        self.cp.add_max_equality(extra, [0, sum(variables) - 1])
        return extra

    def rotacion(self) -> cp.LinearExpr | int:
        semanas = self.contexto.semanas
        if not semanas:
            return 0
        penas = []
        equipos = defaultdict(list)
        for persona in self.contexto.personas.values():
            if not persona.activa:
                continue
            previas = [
                int(self.contexto.historial.get((persona.id, semanas[0].inicio - distancia), 0) > 0)
                for distancia in (timedelta(weeks=2), timedelta(weeks=1))
            ]
            servicio = previas + [self.trabaja[persona.id, s.inicio] for s in semanas]
            for i in range(len(semanas)):
                racha = self.cp.new_bool_var("tres_seguidas")
                self.cp.add_min_equality(racha, servicio[i : i + 3])
                penas.append(3 * racha)
                seguida = self.cp.new_bool_var("servicio_consecutivo")
                self.cp.add_min_equality(seguida, servicio[i + 1 : i + 3])
                penas.append(seguida)
            for puesto in sorted(persona.puestos):
                veces = []
                anterior = int(
                    (persona.id, semanas[0].inicio - timedelta(weeks=1), puesto)
                    in self.contexto.puestos_historicos
                )
                for semana in semanas:
                    variables = self.por_rol[persona.id, semana.inicio, puesto]
                    veces.extend(variables)
                    presente = sum(variables)
                    if variables:
                        consecutiva = self.cp.new_bool_var("puesto_consecutivo")
                        self.cp.add_min_equality(consecutiva, [anterior, presente])
                        penas.append(2 * consecutiva)
                    anterior = presente
                    if variables and puesto in (Puesto.MICROFONOS, Puesto.ACOMODADOR):
                        equipos[semana.inicio, puesto].append((persona.id, presente))
                if len(veces) > 1:
                    penas.append(self.repeticiones(veces))
        encuentros = defaultdict(list)
        for (_, puesto), personas in equipos.items():
            for (a, uno), (b, otro) in combinations(personas, 2):
                juntos = self.cp.new_bool_var("pareja")
                self.cp.add_min_equality(juntos, [uno, otro])
                encuentros[puesto, min(a, b), max(a, b)].append(juntos)
        penas.extend(self.repeticiones(veces) for veces in encuentros.values() if len(veces) > 1)
        return sum(penas)


def resolver(contexto: Contexto, segundos: float = 5.0) -> Resultado:
    modelo = Modelo(contexto)
    plan = None
    probados = []
    for nombre in ("cobertura", "dobletes", "equidad", "rotación"):
        if nombre == "cobertura":
            objetivo = sum(modelo.asigna.values())
            modelo.cp.maximize(objetivo)
        else:
            if nombre == "dobletes":
                objetivo = sum(modelo.dobles)
            elif nombre == "equidad":
                objetivo = modelo.equidad()
            else:
                objetivo = modelo.rotacion()
            modelo.cp.minimize(objetivo)
        solver = cp.CpSolver()
        # La rotación tiene más combinaciones y se ejecuta sobre los objetivos ya fijados.
        es_rotacion = nombre == "rotación"
        solver.parameters.max_time_in_seconds = segundos * (2 if es_rotacion else 1)
        solver.parameters.num_search_workers = 4 if es_rotacion else 1
        solver.parameters.random_seed = 73
        estado = solver.solve(modelo.cp)
        if estado == cp.UNKNOWN and plan is not None:
            return Resultado("FEASIBLE", plan, tuple(probados))
        if estado not in (cp.OPTIMAL, cp.FEASIBLE):
            return Resultado(solver.status_name(estado), None, tuple(probados))
        plan = {
            plaza: persona for (plaza, persona), var in modelo.asigna.items() if solver.value(var)
        }
        if estado == cp.FEASIBLE:
            return Resultado("FEASIBLE", plan, tuple(probados))
        probados.append(nombre)
        modelo.cp.add(objetivo == solver.value(objetivo))
        modelo.cp.clear_hints()
        for variable in modelo.asigna.values():
            modelo.cp.add_hint(variable, solver.value(variable))
    return Resultado("OPTIMAL", plan, tuple(probados))
