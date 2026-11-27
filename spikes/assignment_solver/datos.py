"""Entradas ficticias. Cada semana recibe directamente las plazas solicitadas."""

from dataclasses import dataclass
from random import Random
from typing import Literal

PUESTO = {
    "audio": "audio",
    "video": "video",
    "microfonos_1": "microfonos",
    "microfonos_2": "microfonos",
    "acomodador_1": "acomodador",
    "acomodador_2": "acomodador",
    "plataforma": "plataforma",
    "lector_martes": "lector_martes",
    "presidente": "presidente",
    "lector_domingo": "lector_domingo",
}
COMPATIBLES = frozenset({"microfonos", "plataforma", "presidente"})
Asignacion = tuple[int, str, int]  # semana (desde 1), plaza, ID
Observacion = int | Literal["ausente", "cancelada"] | None
Historial = tuple[tuple[Observacion, ...], ...]  # meses en orden cronológico


@dataclass(frozen=True)
class Persona:
    id: int
    puestos: frozenset[str]
    ausencias: frozenset[int] = frozenset()
    activa: bool = True
    historial: Historial = ((), (), ())

    def pasado(self) -> list[Observacion]:
        # Un mes sin datos interrumpe la continuidad sin sumar oportunidades.
        return [semana for mes in self.historial for semana in (mes or (None,))]


@dataclass(frozen=True)
class Mes:
    personas: tuple[Persona, ...]
    semanas: tuple[tuple[str, ...], ...]
    canceladas: frozenset[int] = frozenset()
    bloqueos: tuple[Asignacion, ...] = ()

    def __post_init__(self) -> None:
        if len({p.id for p in self.personas}) != len(self.personas):
            raise ValueError("ID repetido")
        for plazas in self.semanas:
            if len(set(plazas)) != len(plazas) or not set(plazas) <= PUESTO.keys():
                raise ValueError("Plaza inválida o repetida en una semana")
        for persona in self.personas:
            if len(persona.historial) != 3:
                raise ValueError("Se esperan tres meses históricos")

    def requeridas(self) -> list[tuple[int, str]]:
        return [
            (s, plaza)
            for s, plazas in enumerate(self.semanas, 1)
            if s not in self.canceladas
            for plaza in plazas
        ]

    def oportunidades(self, persona: Persona) -> int:
        conocidas = sum(isinstance(dato, int) for dato in persona.pasado())
        actuales = sum(
            bool(plazas) and s not in self.canceladas and s not in persona.ausencias
            for s, plazas in enumerate(self.semanas, 1)
        )
        return conocidas + actuales * persona.activa


def escenario(cantidad: int, semanas: int, *, dificil: bool = False) -> Mes:
    rng = Random(73 + cantidad)
    personas = []
    roles = tuple(dict.fromkeys(PUESTO.values()))
    habituales = tuple(PUESTO.values())
    for indice in range(cantidad):
        puestos = {habituales[indice % len(habituales)], rng.choice(roles)}
        if dificil:
            puestos -= {"video", "lector_martes"}
            if indice == 0:
                puestos = {"video"}
            if indice == 1:
                puestos = {"lector_martes", "plataforma"}
        ausencias = {s for s in range(1, semanas + 1) if rng.random() < 0.12}
        if dificil and indice in (0, 1):
            ausencias = {2} if indice == 0 else set()
        historia = tuple(
            tuple(rng.choice([0, 0, 1, 1, 2, None, "ausente"]) for _ in range(n)) for n in (4, 5, 4)
        )
        personas.append(
            Persona(
                indice + 1,
                frozenset(puestos),
                frozenset(ausencias),
                activa=not (dificil and indice == cantidad - 1),
                historial=historia,
            )
        )
    plazas = [tuple(PUESTO) for _ in range(semanas)]
    if dificil:
        plazas[-1] = tuple(p for p in PUESTO if p != "presidente")
        return Mes(
            tuple(personas), tuple(plazas), frozenset({3}), ((1, "video", 1), (1, "plataforma", 2))
        )
    return Mes(tuple(personas), tuple(plazas))
