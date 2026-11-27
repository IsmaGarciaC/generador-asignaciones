"""Importación explícita del padrón y del historial JSON reciente de V1."""

import hashlib
import json
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

from generador_asignaciones_v2.dominio.programa import (
    Asignaciones,
    Persona,
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
    LoteImportado,
    Programa,
    SemanaPrograma,
)

PUESTOS_VALIDOS = frozenset(p.value for p in Puesto)


@dataclass(frozen=True)
class VistaImportacion:
    huella: str
    archivos: dict[str, bytes]
    personas: dict[int, Persona]
    ausencias: frozenset[tuple[int, date]]
    historial: dict[tuple[int, int], Asignaciones]
    pendientes: tuple[str, ...]
    grupo_sugerido: int | None


def _nombre(nombre: str) -> str:
    return " ".join(unicodedata.normalize("NFC", nombre).casefold().split())


def _sin_claves_repetidas(pares: list[tuple[str, object]]) -> dict:
    valores = dict(pares)
    if len(valores) != len(pares):
        raise ValueError("hay claves JSON repetidas")
    return valores


def _leer_archivos(
    origen: Path, nombres: tuple[str, ...], pendientes: list[str]
) -> tuple[dict[str, bytes], dict[str, object]]:
    archivos = {}
    documentos = {}
    for nombre in nombres:
        ruta = origen / nombre
        if not ruta.exists():
            continue
        datos = ruta.read_bytes()
        archivos[nombre] = datos
        try:
            documentos[nombre] = json.loads(
                datos.decode("utf-8-sig"), object_pairs_hook=_sin_claves_repetidas
            )
        except ValueError as error:
            pendientes.append(f"{nombre}: {error}.")
    return archivos, documentos


def _padron(documento: object, pendientes: list[str]) -> dict[int, Persona]:
    if not isinstance(documento, list):
        return {}
    ids = Counter(
        item["id"] for item in documento if isinstance(item, dict) and type(item.get("id")) is int
    )
    personas = {}
    for numero, fila in enumerate(documento, 1):
        if not isinstance(fila, dict):
            pendientes.append(f"Padrón, fila {numero}: registro inválido.")
            continue
        ident, nombre, roles = fila.get("id"), fila.get("nombre"), fila.get("roles")
        if (
            type(ident) is not int
            or not 1 <= ident <= 2**63 - 1
            or ids[ident] != 1
            or not isinstance(nombre, str)
            or not nombre.strip()
            or not isinstance(roles, list)
        ):
            pendientes.append(f"Padrón, fila {numero}: ID o datos de persona inválidos o ambiguos.")
            continue
        puestos = frozenset(
            Puesto(rol) for rol in roles if isinstance(rol, str) and rol in PUESTOS_VALIDOS
        )
        if any(not isinstance(rol, str) or rol not in PUESTOS_VALIDOS for rol in roles):
            pendientes.append(f"Padrón, fila {numero}: hay capacitaciones desconocidas.")
        telefono = fila.get("telefono")
        if telefono is not None and not isinstance(telefono, str):
            pendientes.append(f"Padrón, fila {numero}: teléfono con formato desconocido.")
            telefono = None
        estado = fila.get("activo", True)
        if type(estado) is not bool:
            pendientes.append(f"Padrón, fila {numero}: estado activo inválido.")
            continue
        personas[ident] = Persona(ident, nombre.strip(), puestos, estado, telefono)
    return personas


def previsualizar(origen: Path, anio: int, mes: int) -> VistaImportacion:
    martes_del_mes(anio, mes)
    anteriores = meses_anteriores(anio, mes)
    nombres = ("hermanos.json", "ausencias.json", "estado.json") + tuple(
        f"asignaciones_{a}_{m:02d}.json" for a, m in anteriores
    )
    pendientes: list[str] = []
    archivos, documentos = _leer_archivos(origen, nombres, pendientes)
    if "hermanos.json" not in archivos:
        raise ValueError("Elige la carpeta del respaldo V1 que contiene hermanos.json.")
    if not isinstance(documentos.get("hermanos.json"), list):
        raise ValueError("hermanos.json debe contener una lista JSON válida.")
    personas = _padron(documentos["hermanos.json"], pendientes)
    por_nombre = defaultdict(list)
    for persona in personas.values():
        por_nombre[_nombre(persona.nombre)].append(persona.id)

    def identidad(valor: object, ubicacion: str) -> int | None:
        if type(valor) is int and valor in personas:
            return valor
        if isinstance(valor, str):
            coincidencias = por_nombre[_nombre(valor)]
            if len(coincidencias) == 1:
                return coincidencias[0]
        pendientes.append(f"{ubicacion}: identidad desconocida o ambigua ({valor!s}).")
        return None

    ausencias = set()
    historial: dict[tuple[int, int], Asignaciones] = {}
    registro = documentos.get("ausencias.json", {})
    if not isinstance(registro, dict):
        pendientes.append("ausencias.json: se esperaba un objeto por mes.")
        registro = {}
    for a, m in (*anteriores, (anio, mes)):
        clave = f"{a}-{m:02d}"
        fechas = dict(enumerate(martes_del_mes(a, m), 1))
        ausencias_mes = registro.get(clave, {})
        if not isinstance(ausencias_mes, dict):
            pendientes.append(f"{clave}: ausencias con formato inválido.")
        else:
            for nombre, semanas in ausencias_mes.items():
                ident = identidad(nombre, f"{clave} · ausencias")
                if not isinstance(semanas, list) or any(
                    type(numero) is not int or numero not in fechas for numero in semanas
                ):
                    pendientes.append(f"{clave}: semanas de ausencia inválidas ({nombre}).")
                elif ident is not None:
                    ausencias.update((ident, fechas[numero]) for numero in semanas)
        if (a, m) == (anio, mes):
            continue
        archivo = f"asignaciones_{a}_{m:02d}.json"
        if archivo not in documentos:
            continue
        datos = documentos[archivo]
        if not isinstance(datos, dict):
            pendientes.append(f"{archivo}: se esperaba un objeto con claves de semana.")
            continue
        plan = {}
        for indice, filas in datos.items():
            semana = fechas.get(int(indice)) if indice in {"1", "2", "3", "4", "5"} else None
            if semana is None or not isinstance(filas, dict):
                pendientes.append(f"{archivo}: semana {indice} inválida.")
                continue
            for rol, nombres_puesto in filas.items():
                if rol not in PUESTOS_VALIDOS or not isinstance(nombres_puesto, list):
                    pendientes.append(f"{archivo}, semana {indice}: puesto {rol} inválido.")
                    continue
                for cupo, nombre in enumerate(nombres_puesto, 1):
                    if nombre in (None, "", "—"):
                        continue
                    ident = identidad(nombre, f"{archivo}, semana {indice}, {rol}")
                    if ident is not None:
                        plan[semana, Puesto(rol), cupo] = ident
        if plan:
            historial[a, m] = plan

    estado = documentos.get("estado.json")
    grupo = None
    if (
        anteriores
        and isinstance(estado, dict)
        and (estado.get("ultimo_anio"), estado.get("ultimo_mes")) == anteriores[-1]
    ):
        candidato = estado.get("siguiente_grupo_limpieza")
        if type(candidato) is int and candidato > 0:
            grupo = candidato
    huella = hashlib.sha256(
        json.dumps(
            [anio, mes, [(n, hashlib.sha256(b).hexdigest()) for n, b in archivos.items()]]
        ).encode("utf-8")
    ).hexdigest()
    return VistaImportacion(
        huella, archivos, personas, frozenset(ausencias), historial, tuple(pendientes), grupo
    )


def aplicar(base: BaseDatos, vista: VistaImportacion) -> dict:
    """Conserva la evidencia leída y aplica una vista previa en una transacción."""
    with base.escritura() as sesion:
        registrado = sesion.get(LoteImportado, vista.huella)
        if registrado is not None:
            return {**registrado.resumen, "repetido": True}
        base.respaldar(prefijo="antes-de-importar")
        archivo_privado = base.ruta.parent / "importaciones" / vista.huella
        archivo_privado.mkdir(parents=True, exist_ok=True)
        for nombre, datos in vista.archivos.items():
            destino = archivo_privado / nombre
            if destino.exists():
                if destino.read_bytes() != datos:
                    raise ValueError(f"La evidencia privada de {nombre} ya existe y difiere.")
            else:
                temporal = destino.with_suffix(f".{uuid4().hex}.tmp")
                try:
                    temporal.write_bytes(datos)
                    temporal.rename(destino)
                finally:
                    temporal.unlink(missing_ok=True)

        pendientes = list(vista.pendientes)
        admitidos = set()
        altas = 0
        for persona in vista.personas.values():
            actual = sesion.get(Hermano, persona.id)
            if actual is None:
                sesion.add(
                    Hermano(
                        id=persona.id,
                        nombre=persona.nombre,
                        telefono=persona.telefono,
                        activo=persona.activa,
                    )
                )
                sesion.flush()
                sesion.add_all(
                    Capacitacion(hermano_id=persona.id, puesto=p) for p in persona.puestos
                )
                altas += 1
            elif _nombre(actual.nombre) != _nombre(persona.nombre):
                pendientes.append(f"ID {persona.id}: el nombre del padrón V2 difiere.")
                continue
            admitidos.add(persona.id)

        total_ausencias = 0
        for ident, semana in sorted(vista.ausencias):
            if ident not in admitidos:
                pendientes.append(f"{semana:%Y-%m-%d}: ausencia del ID {ident} sin conciliar.")
            elif sesion.get(Ausencia, (ident, semana)) is None:
                sesion.add(Ausencia(hermano_id=ident, inicio_semana=semana))
                total_ausencias += 1

        total_asignaciones = 0
        for (anio, mes), plan in sorted(vista.historial.items()):
            if sesion.scalar(select(Programa.id).where(Programa.anio == anio, Programa.mes == mes)):
                pendientes.append(f"{anio}-{mes:02d}: ya hay un programa guardado para este mes.")
                continue
            admitidas = [(plaza, ident) for plaza, ident in plan.items() if ident in admitidos]
            for (semana, puesto, _), ident in plan.items():
                if ident not in admitidos:
                    pendientes.append(f"{semana:%Y-%m-%d} · {puesto}: ID {ident} sin conciliar.")
                elif (ident, semana) in vista.ausencias:
                    pendientes.append(f"{semana:%Y-%m-%d} · {puesto}: también consta una ausencia.")
            if not admitidas:
                continue
            programa = Programa(anio=anio, mes=mes, historico=True)
            sesion.add(programa)
            sesion.flush()
            sesion.add_all(
                SemanaPrograma(programa_id=programa.id, inicio_semana=semana)
                for semana in sorted({plaza[0] for plaza, _ in admitidas})
            )
            sesion.flush()
            sesion.add_all(
                Asignacion(
                    programa_id=programa.id,
                    inicio_semana=semana,
                    puesto=puesto,
                    plaza=cupo,
                    hermano_id=ident,
                )
                for (semana, puesto, cupo), ident in admitidas
            )
            total_asignaciones += len(admitidas)
        resumen = {
            "personas_nuevas": altas,
            "ausencias_nuevas": total_ausencias,
            "asignaciones_historicas": total_asignaciones,
            "pendientes": pendientes,
        }
        sesion.add(LoteImportado(huella=vista.huella, resumen=resumen))
        return {**resumen, "repetido": False}
