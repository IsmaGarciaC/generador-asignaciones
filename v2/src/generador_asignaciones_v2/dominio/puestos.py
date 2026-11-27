"""Puestos, cupos habituales y combinaciones semanales permitidas."""

from collections.abc import Iterable, Mapping
from enum import StrEnum
from types import MappingProxyType


class Puesto(StrEnum):
    AUDIO = "audio"
    VIDEO = "video"
    ACOMODADOR = "acomodador"
    MICROFONOS = "microfonos"
    PLATAFORMA = "plataforma"
    LECTOR_MARTES = "lector_martes"
    PRESIDENTE = "presidente"
    LECTOR_DOMINGO = "lector_domingo"


ETIQUETAS_PUESTOS = {
    Puesto.AUDIO: "Audio",
    Puesto.VIDEO: "Video",
    Puesto.ACOMODADOR: "Acomodadores",
    Puesto.MICROFONOS: "Micrófonos",
    Puesto.PLATAFORMA: "Plataforma",
    Puesto.LECTOR_MARTES: "Lector del martes",
    Puesto.PRESIDENTE: "Presidente",
    Puesto.LECTOR_DOMINGO: "Lector de La Atalaya",
}


CUPOS_HABITUALES: Mapping[Puesto, int] = MappingProxyType({
    Puesto.AUDIO: 1,
    Puesto.VIDEO: 1,
    Puesto.ACOMODADOR: 2,
    Puesto.MICROFONOS: 2,
    Puesto.PLATAFORMA: 1,
    Puesto.LECTOR_MARTES: 1,
    Puesto.PRESIDENTE: 1,
    Puesto.LECTOR_DOMINGO: 1,
})

PUESTOS_COMPATIBLES_CON_LECTOR = frozenset({
    Puesto.MICROFONOS,
    Puesto.PLATAFORMA,
    Puesto.PRESIDENTE,
})


def combinacion_semanal_valida(puestos: Iterable[Puesto]) -> bool:
    """Comprueba los puestos asignados a una misma persona en una semana."""
    asignados = tuple(puestos)
    if len(asignados) <= 1:
        return True
    return (
        len(asignados) == 2
        and Puesto.LECTOR_MARTES in asignados
        and any(puesto in PUESTOS_COMPATIBLES_CON_LECTOR for puesto in asignados)
    )
