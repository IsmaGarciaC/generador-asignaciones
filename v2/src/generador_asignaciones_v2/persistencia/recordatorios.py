"""Lectura de rondas publicadas y registro transaccional de confirmaciones."""

from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from generador_asignaciones_v2.dominio.puestos import Puesto
from generador_asignaciones_v2.dominio.recordatorios import Configuracion, Recordatorio, preparar
from generador_asignaciones_v2.persistencia.base_datos import BaseDatos
from generador_asignaciones_v2.persistencia.modelos import (
    ConfiguracionRecordatorios,
    EnvioRecordatorio,
    Hermano,
    Publicacion,
)
from generador_asignaciones_v2.persistencia.programas import _buscar_programa, _publicacion


@dataclass(frozen=True)
class Ronda:
    version: int | None = None
    cancelada: bool = False
    recordatorios: tuple[Recordatorio, ...] = ()


def _configuracion(sesion: Session) -> Configuracion:
    fila = sesion.get(ConfiguracionRecordatorios, 1)
    if fila is None:
        return Configuracion()
    return Configuracion(frozenset(map(Puesto, fila.puestos)), fila.plantilla)


def _ronda(sesion: Session, inicio: date) -> tuple[int | None, Ronda]:
    programa = _buscar_programa(sesion, inicio.year, inicio.month)
    publicada = _publicacion(sesion, programa.id) if programa else None
    if publicada is None:
        return None, Ronda()
    semana = next(
        (s for s in publicada.contenido["semanas"] if s["inicio"] == inicio.isoformat()), None
    )
    if semana is None:
        return None, Ronda()
    if semana["cancelada"]:
        return programa.id, Ronda(publicada.version, True)
    personas = {plaza["persona"] for plaza in semana["plazas"] if plaza["persona"] is not None}
    telefonos = dict(
        sesion.execute(select(Hermano.id, Hermano.telefono).where(Hermano.id.in_(personas))).all()
    )
    ultimos = {}
    for envio in sesion.scalars(
        select(EnvioRecordatorio)
        .where(EnvioRecordatorio.inicio_semana == inicio)
        .order_by(EnvioRecordatorio.numero)
    ):
        ultimos[envio.hermano_id] = envio.numero, envio.version
    configuracion = _configuracion(sesion)
    mensajes = preparar(inicio, semana, publicada.version, configuracion, telefonos, ultimos)
    return programa.id, Ronda(publicada.version, False, mensajes)


class Recordatorios:
    def __init__(self, base: BaseDatos) -> None:
        self.base = base

    def semanas(self) -> tuple[date, ...]:
        publicacion = aliased(Publicacion)
        ultima = (
            select(Publicacion.version)
            .where(Publicacion.programa_id == publicacion.programa_id)
            .order_by(Publicacion.version.desc())
            .limit(1)
            .scalar_subquery()
        )
        with self.base.transaccion() as sesion:
            return tuple(
                sorted(
                    date.fromisoformat(s["inicio"])
                    for contenido in sesion.scalars(
                        select(publicacion.contenido).where(publicacion.version == ultima)
                    )
                    for s in contenido["semanas"]
                )
            )

    def configuracion(self) -> Configuracion:
        with self.base.transaccion() as sesion:
            return _configuracion(sesion)

    def guardar_configuracion(self, configuracion: Configuracion) -> None:
        configuracion.validar()
        with self.base.escritura() as sesion:
            sesion.merge(
                ConfiguracionRecordatorios(
                    id=1,
                    puestos=sorted(p.value for p in configuracion.puestos),
                    plantilla=configuracion.plantilla,
                )
            )

    def leer(self, inicio: date) -> Ronda:
        with self.base.transaccion() as sesion:
            return _ronda(sesion, inicio)[1]

    def verificar(self, recordatorio: Recordatorio, *, reenvio: bool) -> str:
        with self.base.transaccion() as sesion:
            self._verificar(sesion, recordatorio, reenvio)
        return recordatorio.enlace

    def confirmar(self, recordatorio: Recordatorio, *, reenvio: bool) -> None:
        with self.base.escritura() as sesion:
            programa_id = self._verificar(sesion, recordatorio, reenvio)
            sesion.add(
                EnvioRecordatorio(
                    inicio_semana=recordatorio.inicio,
                    hermano_id=recordatorio.persona,
                    numero=recordatorio.confirmaciones + 1,
                    programa_id=programa_id,
                    version=recordatorio.version,
                    confirmado_utc=datetime.now(UTC).isoformat(),
                )
            )

    @staticmethod
    def _verificar(sesion: Session, recordatorio: Recordatorio, reenvio: bool) -> int:
        programa_id, ronda = _ronda(sesion, recordatorio.inicio)
        if programa_id is None or recordatorio not in ronda.recordatorios:
            raise ValueError("La ronda cambió. Actualízala antes de continuar.")
        if bool(recordatorio.confirmaciones) != reenvio:
            raise ValueError("Usa la acción de reenvío para un recordatorio ya confirmado.")
        if not recordatorio.telefono:
            raise ValueError("Registra un teléfono internacional válido en Padrón.")
        return programa_id
