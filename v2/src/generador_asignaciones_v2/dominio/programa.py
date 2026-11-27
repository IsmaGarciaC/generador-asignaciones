"""Calendario, rotación y validez de un borrador mensual."""

from calendar import monthrange
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from generador_asignaciones_v2.dominio.puestos import (
    CUPOS_HABITUALES,
    Puesto,
    combinacion_semanal_valida,
)

type Plaza = tuple[date, Puesto, int]
type Asignaciones = dict[Plaza, int]

PUESTOS_MARTES = frozenset({Puesto.LECTOR_MARTES})
PUESTOS_DOMINGO = frozenset({Puesto.PRESIDENTE, Puesto.LECTOR_DOMINGO})


def martes_del_mes(anio: int, mes: int) -> tuple[date, ...]:
    if not 1 <= anio <= 9998:
        raise ValueError("El año está fuera del intervalo admitido.")
    primer_dia, dias = monthrange(anio, mes)
    return tuple(date(anio, mes, dia) for dia in range(1 + (1 - primer_dia) % 7, dias + 1, 7))


def meses_anteriores(anio: int, mes: int) -> tuple[tuple[int, int], ...]:
    indice = anio * 12 + mes - 1
    return tuple((i // 12, i % 12 + 1) for i in range(max(12, indice - 3), indice))


@dataclass(frozen=True)
class Semana:
    inicio: date
    martes: bool = True
    domingo: bool = True
    desactivados: frozenset[Puesto] = frozenset()

    @property
    def cancelada(self) -> bool:
        return not (self.martes or self.domingo)

    def plazas(self) -> tuple[Plaza, ...]:
        if self.cancelada:
            return ()
        omitidos = self.desactivados
        if not self.martes:
            omitidos |= PUESTOS_MARTES
        if not self.domingo:
            omitidos |= PUESTOS_DOMINGO
        return tuple(
            (self.inicio, puesto, cupo)
            for puesto, cantidad in CUPOS_HABITUALES.items()
            if puesto not in omitidos
            for cupo in range(1, cantidad + 1)
        )


@dataclass(frozen=True)
class Persona:
    id: int
    nombre: str
    puestos: frozenset[Puesto] = frozenset()
    activa: bool = True
    telefono: str | None = None


@dataclass(frozen=True)
class Contexto:
    semanas: tuple[Semana, ...]
    personas: dict[int, Persona]
    ausencias: frozenset[tuple[int, date]] = frozenset()
    # Solo incluye semanas de disponibilidad conocida. El valor es el número de servicios.
    historial: dict[tuple[int, date], int] = field(default_factory=dict)

    def plazas(self) -> tuple[Plaza, ...]:
        return tuple(plaza for semana in self.semanas for plaza in semana.plazas())

    def candidatos(self, plaza: Plaza) -> tuple[int, ...]:
        inicio, puesto, _ = plaza
        return tuple(
            persona.id
            for persona in self.personas.values()
            if persona.activa
            and puesto in persona.puestos
            and (persona.id, inicio) not in self.ausencias
        )

    def validar(self, plan: Asignaciones) -> list[str]:
        requeridas = set(self.plazas())
        servicios = defaultdict(list)
        errores = []
        for plaza, persona_id in plan.items():
            inicio, puesto, numero = plaza
            if plaza not in requeridas or persona_id not in self.candidatos(plaza):
                errores.append(f"{inicio:%d/%m} · {puesto.value} {numero}: asignación inválida.")
            servicios[inicio, persona_id].append(puesto)
        for (inicio, persona_id), puestos in servicios.items():
            if not combinacion_semanal_valida(puestos):
                persona = self.personas.get(persona_id)
                nombre = persona.nombre if persona else str(persona_id)
                errores.append(f"{inicio:%d/%m} · {nombre}: combinación de puestos prohibida.")
        return errores


@dataclass(frozen=True)
class Borrador:
    anio: int
    mes: int
    semanas: tuple[Semana, ...]
    plan: Asignaciones = field(default_factory=dict)
    num_grupos: int = 4
    grupo_inicial: int = 1


def grupos_semanales(
    semanas: tuple[Semana, ...], num_grupos: int, inicial: int
) -> dict[date, tuple[int | None, int | None]]:
    if not 1 <= inicial <= num_grupos:
        raise ValueError("El grupo inicial debe estar entre 1 y el número de grupos.")
    grupos = {}
    grupo = inicial
    for semana in semanas:
        if semana.cancelada:
            grupos[semana.inicio] = (None, None)
        else:
            grupos[semana.inicio] = (grupo, (grupo - 2) % num_grupos + 1)
            grupo = grupo % num_grupos + 1
    return grupos
