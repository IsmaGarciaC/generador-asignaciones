"""Calendario, rotación y validez de un borrador mensual."""

from calendar import monthrange
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta

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
    puestos_historicos: frozenset[tuple[int, date, Puesto]] = frozenset()

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

    def validar(
        self,
        plan: Asignaciones,
        *,
        bloqueos: frozenset[Plaza] = frozenset(),
    ) -> list[str]:
        requeridas = set(self.plazas())
        servicios = defaultdict(list)
        errores = [
            f"{fecha:%d/%m} · {puesto.value} {numero}: el bloqueo requiere una persona."
            for fecha, puesto, numero in sorted(bloqueos - plan.keys())
        ]
        for plaza, persona_id in plan.items():
            inicio, puesto, numero = plaza
            persona = self.personas.get(persona_id)
            if plaza not in requeridas:
                motivo = "la plaza no es requerida"
            elif persona is None:
                motivo = "la persona no existe en el padrón"
            elif not persona.activa:
                motivo = f"{persona.nombre} está inactiva"
            elif puesto not in persona.puestos:
                motivo = f"{persona.nombre} no tiene capacitación para este puesto"
            elif (persona_id, inicio) in self.ausencias:
                motivo = f"{persona.nombre} tiene una ausencia registrada"
            else:
                servicios[inicio, persona_id].append(plaza)
                continue
            estado = "bloqueo inválido" if plaza in bloqueos else "asignación inválida"
            errores.append(f"{inicio:%d/%m} · {puesto.value} {numero}: {estado}, {motivo}.")
        for (inicio, persona_id), plazas in servicios.items():
            puestos = [plaza[1] for plaza in plazas]
            if not combinacion_semanal_valida(puestos):
                persona = self.personas.get(persona_id)
                nombre = persona.nombre if persona else str(persona_id)
                detalle = ", ".join(f"{puesto.value} {numero}" for _, puesto, numero in plazas)
                tipo = "bloqueo incompatible, " if any(p in bloqueos for p in plazas) else ""
                errores.append(
                    f"{inicio:%d/%m} · {nombre}: {tipo}"
                    f"combinación de puestos prohibida ({detalle})."
                )
        return errores


@dataclass(frozen=True)
class CargaPersona:
    asignaciones: int
    semanas: tuple[date, ...]
    racha_maxima: int


def resumir_carga(contexto: Contexto, plan: Asignaciones) -> dict[int, CargaPersona]:
    """Cuenta asignaciones y semanas de servicio, incluidas rachas que cruzan de mes."""
    asignaciones = Counter(plan.values())
    fechas_por_persona = defaultdict(set)
    for (fecha, _, _), persona in plan.items():
        fechas_por_persona[persona].add(fecha)
    anteriores = defaultdict(set)
    primer_martes = contexto.semanas[0].inicio if contexto.semanas else date.min
    for (persona, fecha), cantidad in contexto.historial.items():
        if cantidad and fecha < primer_martes:
            anteriores[persona].add(fecha)

    resumen = {}
    for persona in contexto.personas.values():
        if not persona.activa and persona.id not in asignaciones:
            continue
        fechas = fechas_por_persona[persona.id]
        ultima = None
        racha = maxima = 0
        for fecha in sorted(anteriores[persona.id] | fechas):
            racha = racha + 1 if ultima is not None and fecha - ultima == timedelta(weeks=1) else 1
            if fecha in fechas:
                maxima = max(maxima, racha)
            ultima = fecha
        resumen[persona.id] = CargaPersona(asignaciones[persona.id], tuple(sorted(fechas)), maxima)
    return resumen


@dataclass(frozen=True)
class Borrador:
    anio: int
    mes: int
    semanas: tuple[Semana, ...]
    plan: Asignaciones = field(default_factory=dict)
    num_grupos: int = 4
    grupo_inicial: int = 1
    bloqueos: frozenset[Plaza] = frozenset()


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
