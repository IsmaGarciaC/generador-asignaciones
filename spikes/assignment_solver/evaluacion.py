"""Verificación y puntuación del plan materializado, sin importar OR-Tools."""

from collections import Counter, defaultdict
from collections.abc import Iterable

from datos import COMPATIBLES, PUESTO, Asignacion, Mes


def infracciones(mes: Mes, plan: Iterable[Asignacion]) -> list[str]:
    filas = tuple(plan)
    requeridas = set(mes.requeridas())
    personas = {p.id: p for p in mes.personas}
    ocupadas = set()
    servicios = defaultdict(list)
    errores = []
    for semana, plaza, id_persona in filas:
        clave = semana, plaza
        quien = f"Semana {semana}, {plaza}, ID {id_persona}"
        if clave not in requeridas:
            errores.append(f"{quien}: plaza no requerida")
        if clave in ocupadas:
            errores.append(f"{quien}: plaza ocupada más de una vez")
        ocupadas.add(clave)
        persona = personas.get(id_persona)
        if persona is None:
            errores.append(f"{quien}: ID desconocido")
            continue
        if not persona.activa:
            errores.append(f"{quien}: inactivo")
        if semana in persona.ausencias:
            errores.append(f"{quien}: ausente")
        if PUESTO.get(plaza) not in persona.puestos:
            errores.append(f"{quien}: sin capacitación")
        servicios[semana, id_persona].append(PUESTO.get(plaza, plaza))
    for (semana, id_persona), roles in servicios.items():
        valido = len(roles) == 1 or (
            len(roles) == 2 and "lector_martes" in roles and bool(COMPATIBLES.intersection(roles))
        )
        if not valido:
            errores.append(f"Semana {semana}, ID {id_persona}: combinación prohibida {roles}")
    for bloqueo in set(mes.bloqueos) - set(filas):
        errores.append(f"Bloqueo incumplido {bloqueo}")
    return errores


def coste_carga(cantidad: int, oportunidades: int) -> int:
    """Centésimas del coste cuadrático, redondeadas al entero más cercano."""
    return (100 * cantidad**2 + oportunidades // 2) // oportunidades if oportunidades else 0


def metricas(mes: Mes, plan: Iterable[Asignacion]) -> dict[str, int]:
    filas = tuple(plan)
    servicios = Counter((persona, semana) for semana, _, persona in filas)
    roles = Counter((persona, PUESTO[plaza]) for _, plaza, persona in filas)
    equipos = defaultdict(list)
    for semana, plaza, persona in filas:
        if PUESTO[plaza] in ("microfonos", "acomodador"):
            equipos[semana, PUESTO[plaza]].append(persona)
    parejas = Counter(
        (rol, tuple(sorted(ids))) for (_, rol), ids in equipos.items() if len(ids) == 2
    )
    equidad_a = equidad_s = rachas = 0
    for p in mes.personas:
        if not p.activa:
            continue
        pasado = p.pasado()
        conocidas = [x for x in pasado if isinstance(x, int)]
        actual = [servicios[p.id, s] for s in range(1, len(mes.semanas) + 1)]
        total = sum(conocidas) + sum(actual)
        trabajadas = sum(x > 0 for x in conocidas) + sum(x > 0 for x in actual)
        oportunidades = mes.oportunidades(p)
        equidad_a += coste_carga(total, oportunidades)
        equidad_s += coste_carga(trabajadas, oportunidades)
        previas = [isinstance(x, int) and x > 0 for x in pasado[-2:]]
        secuencia = previas + [bool(n) for n in actual]
        rachas += sum(all(secuencia[i : i + 3]) for i in range(len(secuencia) - 2))
    return {
        "cobertura": len(filas),
        "dobletes": sum(n == 2 for n in servicios.values()),
        "carga": equidad_a,
        "frecuencia": equidad_s,
        "equidad": equidad_a + equidad_s,
        "rachas": rachas,
        "puestos": sum(n - 1 for n in roles.values()),
        **{
            rol: sum(n - 1 for (puesto, _), n in parejas.items() if puesto == rol)
            for rol in ("microfonos", "acomodador")
        },
    }
