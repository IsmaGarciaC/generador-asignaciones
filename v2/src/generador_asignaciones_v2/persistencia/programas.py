"""Lectura y escritura atómica de borradores, padrón y publicaciones."""

from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from datetime import date

from sqlalchemy import delete, select, tuple_
from sqlalchemy.orm import Session

from generador_asignaciones_v2.dominio.programa import (
    Borrador,
    Contexto,
    Persona,
    Semana,
    grupos_semanales,
    martes_del_mes,
    meses_anteriores,
)
from generador_asignaciones_v2.dominio.puestos import Puesto
from generador_asignaciones_v2.persistencia.base_datos import BaseDatos
from generador_asignaciones_v2.persistencia.modelos import (
    Asignacion,
    Ausencia,
    Capacitacion,
    Hermano,
    Programa,
    Publicacion,
    SemanaPrograma,
)


@dataclass(frozen=True)
class VistaMes:
    borrador: Borrador
    contexto: Contexto
    revision: int | None
    version: int | None
    publicado_al_dia: bool
    historico: bool


def _buscar_programa(sesion: Session, anio: int, mes: int) -> Programa | None:
    return sesion.scalar(select(Programa).where(Programa.anio == anio, Programa.mes == mes))


def _publicacion(sesion: Session, programa_id: int) -> Publicacion | None:
    return sesion.scalar(
        select(Publicacion)
        .where(Publicacion.programa_id == programa_id)
        .order_by(Publicacion.version.desc())
        .limit(1)
    )


def _personas(sesion: Session) -> dict[int, Persona]:
    puestos = defaultdict(set)
    for fila in sesion.scalars(select(Capacitacion)):
        puestos[fila.hermano_id].add(fila.puesto)
    return {
        h.id: Persona(h.id, h.nombre, frozenset(puestos[h.id]), h.activo, h.telefono)
        for h in sesion.scalars(select(Hermano).order_by(Hermano.nombre, Hermano.id))
    }


def _historial(
    sesion: Session, anio: int, mes: int, ausencias: frozenset[tuple[int, date]]
) -> tuple[
    dict[tuple[int, date], int], frozenset[tuple[int, date, Puesto]], tuple[int, int] | None
]:
    meses = meses_anteriores(anio, mes)
    programas = sesion.scalars(
        select(Programa)
        .where(tuple_(Programa.anio, Programa.mes).in_(meses))
        .order_by(Programa.anio, Programa.mes)
    ).all()
    historial = {}
    puestos = set()
    rotacion = None
    for programa in programas:
        publicada = _publicacion(sesion, programa.id)
        if publicada:
            for semana in publicada.contenido["semanas"]:
                inicio = date.fromisoformat(semana["inicio"])
                servicios = Counter(plaza["persona"] for plaza in semana["plazas"])
                puestos.update(
                    (plaza["persona"], inicio, Puesto(plaza["puesto"]))
                    for plaza in semana["plazas"]
                    if plaza["persona"] is not None
                )
                for persona in semana["disponibles"]:
                    historial[persona, inicio] = servicios[persona]
                if semana["limpieza"] is not None:
                    cantidad = publicada.contenido["num_grupos"]
                    rotacion = (cantidad, semana["limpieza"] % cantidad + 1)
        elif programa.historico:
            filas = sesion.scalars(
                select(Asignacion).where(
                    Asignacion.programa_id == programa.id, Asignacion.hermano_id.is_not(None)
                )
            ).all()
            servicios = Counter((a.hermano_id, a.inicio_semana) for a in filas)
            puestos.update((a.hermano_id, a.inicio_semana, a.puesto) for a in filas)
            historial.update({clave: n for clave, n in servicios.items() if clave not in ausencias})
    return historial, frozenset(puestos), rotacion


def _vista(sesion: Session, anio: int, mes: int, programa: Programa | None) -> VistaMes:
    fechas = martes_del_mes(anio, mes)
    anteriores = meses_anteriores(anio, mes)
    anio_inicio, mes_inicio = anteriores[0] if anteriores else (anio, mes)
    ausencias = frozenset(
        (persona, fecha)
        for persona, fecha in sesion.execute(
            select(Ausencia.hermano_id, Ausencia.inicio_semana).where(
                Ausencia.inicio_semana >= date(anio_inicio, mes_inicio, 1),
                Ausencia.inicio_semana <= fechas[-1],
            )
        )
    )
    historial, puestos_historicos, rotacion = _historial(sesion, anio, mes, ausencias)
    personas = _personas(sesion)
    if programa is None:
        semanas = tuple(Semana(fecha) for fecha in fechas)
        cantidad, inicial = rotacion or (4, 1)
        borrador = Borrador(anio, mes, semanas, num_grupos=cantidad, grupo_inicial=inicial)
        return VistaMes(
            borrador,
            Contexto(semanas, personas, ausencias, historial, puestos_historicos),
            None,
            None,
            False,
            False,
        )

    filas = {
        s.inicio_semana: Semana(
            s.inicio_semana, s.martes, s.domingo, frozenset(map(Puesto, s.desactivados))
        )
        for s in sesion.scalars(
            select(SemanaPrograma).where(SemanaPrograma.programa_id == programa.id)
        )
    }
    semanas = tuple(filas.get(fecha, Semana(fecha)) for fecha in fechas)
    plan = {
        (a.inicio_semana, a.puesto, a.plaza): a.hermano_id
        for a in sesion.scalars(
            select(Asignacion).where(
                Asignacion.programa_id == programa.id, Asignacion.hermano_id.is_not(None)
            )
        )
    }
    borrador = Borrador(anio, mes, semanas, plan, programa.num_grupos, programa.grupo_inicial)
    publicada = _publicacion(sesion, programa.id)
    return VistaMes(
        borrador,
        Contexto(semanas, personas, ausencias, historial, puestos_historicos),
        programa.revision,
        publicada.version if publicada else None,
        publicada is not None and publicada.revision_borrador == programa.revision,
        programa.historico,
    )


class Programas:
    def __init__(self, base: BaseDatos) -> None:
        self.base = base

    def leer(self, anio: int, mes: int) -> VistaMes:
        with self.base.transaccion() as sesion:
            return _vista(sesion, anio, mes, _buscar_programa(sesion, anio, mes))

    def guardar(self, origen: VistaMes, borrador: Borrador) -> None:
        anio, mes = borrador.anio, borrador.mes
        if (anio, mes) != (origen.borrador.anio, origen.borrador.mes):
            raise ValueError("El borrador corresponde a otro mes.")
        if tuple(s.inicio for s in borrador.semanas) != martes_del_mes(anio, mes):
            raise ValueError("El calendario no corresponde a los martes del mes.")
        grupos = grupos_semanales(borrador.semanas, borrador.num_grupos, borrador.grupo_inicial)
        with self.base.escritura() as sesion:
            programa = _buscar_programa(sesion, anio, mes)
            actual = _vista(sesion, anio, mes, programa)
            if actual.historico:
                raise ValueError("El historial importado se conserva para consulta.")
            if actual.revision != origen.revision or actual.contexto != origen.contexto:
                raise ValueError("El mes o sus datos cambiaron. Vuelve a cargarlo.")
            contexto = replace(actual.contexto, semanas=borrador.semanas)
            if errores := contexto.validar(borrador.plan):
                raise ValueError("\n".join(errores))
            if programa is not None and actual.borrador == borrador:
                return
            if programa is None:
                programa = Programa(anio=anio, mes=mes, revision=0)
                sesion.add(programa)
                sesion.flush()
            programa.num_grupos = borrador.num_grupos
            programa.grupo_inicial = borrador.grupo_inicial
            programa.revision += 1
            sesion.execute(delete(Asignacion).where(Asignacion.programa_id == programa.id))
            for semana in borrador.semanas:
                fila = sesion.get(SemanaPrograma, (programa.id, semana.inicio))
                if fila is None:
                    fila = SemanaPrograma(programa_id=programa.id, inicio_semana=semana.inicio)
                    sesion.add(fila)
                fila.martes, fila.domingo = semana.martes, semana.domingo
                fila.desactivados = sorted(p.value for p in semana.desactivados)
                fila.limpieza, fila.hospitalidad = grupos[semana.inicio]
            sesion.flush()
            sesion.add_all(
                Asignacion(
                    programa_id=programa.id,
                    inicio_semana=inicio,
                    puesto=puesto,
                    plaza=cupo,
                    hermano_id=persona,
                )
                for (inicio, puesto, cupo), persona in borrador.plan.items()
            )

    def publicar(self, origen: VistaMes, *, acepta_vacantes: bool = False) -> int:
        anio, mes = origen.borrador.anio, origen.borrador.mes
        with self.base.escritura() as sesion:
            programa = _buscar_programa(sesion, anio, mes)
            if programa is None or programa.historico:
                raise ValueError("Primero guarda un borrador editable.")
            vista = _vista(sesion, anio, mes, programa)
            if (vista.revision, vista.contexto) != (origen.revision, origen.contexto):
                raise ValueError("El mes o sus datos cambiaron. Vuelve a cargarlo.")
            if errores := vista.contexto.validar(vista.borrador.plan):
                raise ValueError("\n".join(errores))
            if vista.publicado_al_dia and vista.version is not None:
                return vista.version
            if len(vista.borrador.plan) < len(vista.contexto.plazas()) and not acepta_vacantes:
                raise ValueError("Confirma la publicación con vacantes.")
            version = (vista.version or 0) + 1
            sesion.add(
                Publicacion(
                    programa_id=programa.id,
                    version=version,
                    revision_borrador=programa.revision,
                    contenido=_capturar_publicacion(vista),
                )
            )
            return version

    def leer_publicacion(self, anio: int, mes: int) -> tuple[int, dict]:
        with self.base.transaccion() as sesion:
            programa = _buscar_programa(sesion, anio, mes)
            publicada = _publicacion(sesion, programa.id) if programa else None
            if publicada is None:
                raise ValueError("Publica el programa antes de exportarlo.")
            return publicada.version, publicada.contenido

    def guardar_persona(
        self,
        persona_id: int | None,
        nombre: str,
        telefono: str,
        puestos: frozenset[Puesto],
        activa: bool,
    ) -> int:
        if not nombre.strip():
            raise ValueError("Escribe el nombre.")
        with self.base.escritura() as sesion:
            hermano = sesion.get(Hermano, persona_id) if persona_id is not None else Hermano()
            if hermano is None:
                raise ValueError("La persona ya no existe.")
            hermano.nombre = nombre.strip()
            hermano.telefono = telefono.strip() or None
            hermano.activo = activa
            sesion.add(hermano)
            sesion.flush()
            sesion.execute(delete(Capacitacion).where(Capacitacion.hermano_id == hermano.id))
            sesion.add_all(Capacitacion(hermano_id=hermano.id, puesto=p) for p in puestos)
            return hermano.id

    def guardar_ausencias(
        self,
        anio: int,
        mes: int,
        persona_id: int,
        semanas: frozenset[date],
    ) -> None:
        fechas = martes_del_mes(anio, mes)
        if not semanas.issubset(fechas):
            raise ValueError("Las ausencias deben corresponder a semanas completas de este mes.")
        with self.base.escritura() as sesion:
            programa = _buscar_programa(sesion, anio, mes)
            if programa and programa.historico:
                raise ValueError("Las ausencias históricas se conservan para consulta.")
            sesion.execute(
                delete(Ausencia).where(
                    Ausencia.hermano_id == persona_id, Ausencia.inicio_semana.in_(fechas)
                )
            )
            sesion.add_all(Ausencia(hermano_id=persona_id, inicio_semana=d) for d in semanas)


def _capturar_publicacion(vista: VistaMes) -> dict:
    borrador, contexto = vista.borrador, vista.contexto
    grupos = grupos_semanales(borrador.semanas, borrador.num_grupos, borrador.grupo_inicial)
    semanas = []
    for semana in borrador.semanas:
        plazas = []
        for plaza in semana.plazas():
            persona = borrador.plan.get(plaza)
            plazas.append(
                {
                    "puesto": plaza[1].value,
                    "cupo": plaza[2],
                    "persona": persona,
                    "nombre": contexto.personas[persona].nombre if persona is not None else None,
                }
            )
        limpieza, hospitalidad = grupos[semana.inicio]
        semanas.append(
            {
                "inicio": semana.inicio.isoformat(),
                "cancelada": semana.cancelada,
                "limpieza": limpieza,
                "hospitalidad": hospitalidad,
                "plazas": plazas,
                "disponibles": [
                    p.id
                    for p in contexto.personas.values()
                    if p.activa
                    and not semana.cancelada
                    and (p.id, semana.inicio) not in contexto.ausencias
                ],
            }
        )
    return {"num_grupos": borrador.num_grupos, "semanas": semanas}
