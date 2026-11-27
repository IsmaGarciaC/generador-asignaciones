"""Prototipo de optimización mensual por etapas CP-SAT."""

from collections import defaultdict
from dataclasses import dataclass, field
from itertools import combinations
from time import perf_counter

from datos import COMPATIBLES, PUESTO, Asignacion, Mes
from evaluacion import coste_carga, infracciones, metricas
from ortools.sat.python import cp_model as cp


@dataclass
class Etapa:
    nombre: str
    estado: str
    segundos: float
    valor: int | None
    cota: float | None


@dataclass
class Resultado:
    estado: str = "UNKNOWN"
    plan: tuple[Asignacion, ...] | None = None
    vacantes: tuple[tuple[int, str], ...] = ()
    etapas: list[Etapa] = field(default_factory=list)
    diagnostico: list[str] = field(default_factory=list)


class Modelo:
    def __init__(self, mes: Mes):
        self.mes = mes
        self.cp = cp.CpModel()
        self.x: dict[Asignacion, cp.IntVar] = {}
        self.trabaja = {}
        self.dobles = []
        self.por_persona = defaultdict(list)
        self.por_rol = defaultdict(list)
        for semana, plaza in mes.requeridas():
            candidatos = []
            rol = PUESTO[plaza]
            for p in mes.personas:
                if p.activa and rol in p.puestos and semana not in p.ausencias:
                    x = self.cp.new_bool_var(f"x_{semana}_{plaza}_{p.id}")
                    self.x[semana, plaza, p.id] = x
                    self.por_rol[p.id, semana, rol].append(x)
                    self.por_persona[p.id].append(x)
                    candidatos.append(x)
            self.cp.add_at_most_one(candidatos)
        for persona in mes.personas:
            for s in range(1, len(mes.semanas) + 1):
                roles = {
                    rol: variables
                    for rol in sorted(persona.puestos)
                    if (variables := self.por_rol.get((persona.id, s, rol)))
                }
                lectores = roles.pop("lector_martes", [])
                otros = [x for variables in roles.values() for x in variables]
                self.cp.add_at_most_one(otros)
                incompatibles = [
                    x
                    for rol, variables in roles.items()
                    if rol not in COMPATIBLES
                    for x in variables
                ]
                self.cp.add_at_most_one(lectores + incompatibles)
                trabaja = self.cp.new_bool_var("trabaja")
                doble = self.cp.new_bool_var("doblete")
                self.cp.add(sum(lectores + otros) == trabaja + doble)
                self.cp.add(doble <= trabaja)
                self.trabaja[persona.id, s] = trabaja
                self.dobles.append(doble)
        for bloqueo in mes.bloqueos:
            self.cp.add(self.x.get(bloqueo, 0) == 1)

    def equidad(self) -> cp.LinearExpr | int:
        costes = []
        n = len(self.mes.semanas)
        for p in self.mes.personas:
            d = self.mes.oportunidades(p)
            if not p.activa or not d:
                continue
            pasado = [x for x in p.pasado() if isinstance(x, int)]
            trabajadas = [self.trabaja[p.id, s] for s in range(1, n + 1)]
            for anteriores, variables, limite in (
                (sum(pasado), self.por_persona[p.id], 2 * n),
                (sum(x > 0 for x in pasado), trabajadas, n),
            ):
                indice = self.cp.new_int_var(0, limite, "incremento")
                self.cp.add(indice == sum(variables))
                tabla = [coste_carga(anteriores + i, d) for i in range(limite + 1)]
                coste = self.cp.new_int_var(tabla[0], tabla[-1], "coste")
                self.cp.add_element(indice, tabla, coste)
                costes.append(coste)
        return sum(costes)

    def rotacion(self) -> cp.LinearExpr | int:
        penas = []
        equipos = defaultdict(list)
        for p in self.mes.personas:
            previas = [int(isinstance(x, int) and x > 0) for x in p.pasado()[-2:]]
            servicio = previas + [
                self.trabaja[p.id, s] for s in range(1, len(self.mes.semanas) + 1)
            ]
            for i in range(len(servicio) - 2):
                racha = self.cp.new_bool_var("tres_seguidas")
                self.cp.add_min_equality(racha, servicio[i : i + 3])
                penas.append(racha)
            for rol in sorted(p.puestos):
                veces = []
                for s in range(1, len(self.mes.semanas) + 1):
                    variables = self.por_rol.get((p.id, s, rol), [])
                    veces.extend(variables)
                    if variables and rol in ("microfonos", "acomodador"):
                        equipos[s, rol].append((p.id, sum(variables)))
                if veces:
                    penas.append(self.repeticiones(veces))
        encuentros = defaultdict(list)
        for (_, rol), candidatos in equipos.items():
            for (a, presente_a), (b, presente_b) in combinations(candidatos, 2):
                juntos = self.cp.new_bool_var("juntos")
                self.cp.add_min_equality(juntos, [presente_a, presente_b])
                encuentros[rol, min(a, b), max(a, b)].append(juntos)
        for semanas in encuentros.values():
            if len(semanas) > 1:
                penas.append(self.repeticiones(semanas))
        return sum(penas)

    def repeticiones(self, apariciones: list) -> cp.IntVar:
        extra = self.cp.new_int_var(0, len(apariciones), "repeticiones")
        self.cp.add_max_equality(extra, [0, sum(apariciones) - 1])
        return extra


def resolver(mes: Mes, segundos: float = 5.0) -> Resultado:
    """Limita la búsqueda por etapa y conserva el plan anterior si el estado es UNKNOWN."""
    modelo = Modelo(mes)
    salida = Resultado()
    for nombre in ("cobertura", "dobletes", "equidad", "rotacion"):
        inicio = perf_counter()
        if nombre == "cobertura":
            objetivo = sum(modelo.x.values())
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
        solver.parameters.max_time_in_seconds = segundos
        solver.parameters.num_search_workers = 1
        solver.parameters.random_seed = 73
        estado = solver.solve(modelo.cp)
        hay_plan = estado in (cp.FEASIBLE, cp.OPTIMAL)
        valor = solver.value(objetivo) if hay_plan else None
        salida.etapas.append(
            Etapa(
                nombre,
                solver.status_name(estado),
                perf_counter() - inicio,
                valor,
                solver.best_objective_bound if hay_plan else None,
            )
        )
        if not hay_plan:
            if estado == cp.UNKNOWN and salida.plan is not None:
                salida.estado = "FEASIBLE"
            else:
                salida.estado = solver.status_name(estado)
                salida.plan = None
                salida.vacantes = ()
            if estado == cp.INFEASIBLE:
                salida.diagnostico = infracciones(mes, mes.bloqueos)
            elif estado == cp.MODEL_INVALID:
                salida.diagnostico = [modelo.cp.validate() or solver.solution_info()]
            break
        plan = tuple(clave for clave, x in modelo.x.items() if solver.value(x))
        errores = infracciones(mes, plan)
        if errores:
            raise AssertionError(errores)
        puntos = metricas(mes, plan)
        puntos["rotacion"] = sum(
            puntos[k] for k in ("rachas", "puestos", "microfonos", "acomodador")
        )
        for etapa in salida.etapas:
            if etapa.valor != puntos[etapa.nombre]:
                raise AssertionError(f"Discrepancia en {etapa.nombre}")
        salida.plan = plan
        ocupadas = {(s, plaza) for s, plaza, _ in plan}
        salida.vacantes = tuple(k for k in mes.requeridas() if k not in ocupadas)
        salida.estado = "FEASIBLE"
        if estado != cp.OPTIMAL:
            break
        if nombre == "rotacion":
            salida.estado = "OPTIMAL"
        else:
            modelo.cp.add(objetivo == valor)
            modelo.cp.clear_hints()
            for x in modelo.x.values():
                modelo.cp.add_hint(x, solver.value(x))
    return salida
