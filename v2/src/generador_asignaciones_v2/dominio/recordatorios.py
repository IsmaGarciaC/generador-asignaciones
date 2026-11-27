"""Preparación de mensajes y enlaces de la ronda semanal."""

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from string import Formatter
from urllib.parse import quote

from generador_asignaciones_v2.dominio.puestos import ETIQUETAS_PUESTOS, Puesto

PUESTOS_PREDETERMINADOS = frozenset(Puesto) - {Puesto.PRESIDENTE, Puesto.LECTOR_DOMINGO}
PLANTILLA_PREDETERMINADA = (
    "Hola, {nombre}. Te recordamos tus asignaciones para la semana {semana}:\n"
    "{puestos}\n¡Gracias por tu disposición!"
)
CAMPOS = frozenset({"nombre", "semana", "puestos"})


@dataclass(frozen=True)
class Configuracion:
    puestos: frozenset[Puesto] = PUESTOS_PREDETERMINADOS
    plantilla: str = PLANTILLA_PREDETERMINADA

    def validar(self) -> None:
        if not self.plantilla.strip():
            raise ValueError("Escribe el texto del recordatorio.")
        try:
            for _, campo, formato, conversion in Formatter().parse(self.plantilla):
                if campo is not None and (campo not in CAMPOS or formato or conversion):
                    raise ValueError
        except ValueError as error:
            raise ValueError("Usa solo los campos {nombre}, {semana} y {puestos}.") from error


@dataclass(frozen=True)
class Recordatorio:
    inicio: date
    persona: int
    nombre: str
    puestos: tuple[Puesto, ...]
    telefono: str | None
    mensaje: str
    version: int
    confirmaciones: int
    ultima_version: int | None

    @property
    def enlace(self) -> str:
        if not self.telefono:
            raise ValueError("Registra un teléfono internacional válido en Padrón.")
        return f"https://wa.me/{self.telefono}?text={quote(self.mensaje, safe='')}"


def semana_actual(hoy: date) -> date:
    return hoy - timedelta(days=(hoy.weekday() - 1) % 7)


def periodo_semana(inicio: date) -> str:
    return f"{inicio:%d/%m/%Y} – {inicio + timedelta(days=5):%d/%m/%Y}"


def telefono_internacional(valor: str | None) -> str | None:
    numero = re.sub(r"[\s()-]", "", valor or "").removeprefix("+")
    return numero if re.fullmatch(r"[1-9][0-9]{7,14}", numero) else None


def preparar(
    inicio: date,
    semana: dict,
    version: int,
    configuracion: Configuracion,
    telefonos: dict[int, str | None],
    confirmaciones: dict[int, tuple[int, int]],
) -> tuple[Recordatorio, ...]:
    if semana["cancelada"]:
        return ()
    nombres: dict[int, str] = {}
    asignaciones: dict[int, set[Puesto]] = defaultdict(set)
    for plaza in semana["plazas"]:
        persona, puesto = plaza["persona"], Puesto(plaza["puesto"])
        if persona is not None and puesto in configuracion.puestos:
            nombres[persona] = plaza["nombre"]
            asignaciones[persona].add(puesto)

    lista = []
    for persona in sorted(nombres, key=lambda ident: (nombres[ident].casefold(), ident)):
        puestos = tuple(p for p in Puesto if p in asignaciones[persona])
        cantidad, ultima_version = confirmaciones.get(persona, (0, None))
        mensaje = configuracion.plantilla.format(
            nombre=nombres[persona],
            semana=periodo_semana(inicio),
            puestos="\n".join(f"• {ETIQUETAS_PUESTOS[p]}" for p in puestos),
        )
        lista.append(
            Recordatorio(
                inicio,
                persona,
                nombres[persona],
                puestos,
                telefono_internacional(telefonos.get(persona)),
                mensaje,
                version,
                cantidad,
                ultima_version,
            )
        )
    return tuple(lista)
