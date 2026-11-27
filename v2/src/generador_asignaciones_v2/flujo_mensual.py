"""Coordina la generación de un borrador y la exportación de una publicación."""

from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from generador_asignaciones_v2.dominio.programa import Borrador
from generador_asignaciones_v2.dominio.puestos import Puesto
from generador_asignaciones_v2.optimizador import Resultado, resolver
from generador_asignaciones_v2.persistencia.programas import Programas, VistaMes
from generador_asignaciones_v2.plantilla_excel import crear_libro


def generar(programas: Programas, vista: VistaMes, borrador: Borrador) -> Resultado:
    if vista.historico:
        raise ValueError("El historial importado se conserva para consulta.")
    if not vista.contexto.personas:
        raise ValueError("Agrega o importa el padrón antes de generar.")
    resultado = resolver(replace(vista.contexto, semanas=borrador.semanas), anterior=borrador.plan)
    if resultado.plan is not None:
        programas.guardar(vista, replace(borrador, plan=resultado.plan))
    return resultado


def celdas_publicadas(contenido: dict) -> dict[int, dict[str, str]]:
    celdas = {}
    for indice, semana in enumerate(contenido["semanas"], 1):
        if semana["cancelada"]:
            celdas[indice] = dict.fromkeys([*Puesto, "limpieza", "hospitalidad"], "Cancelada")
            continue
        valores = {puesto.value: "No requerido" for puesto in Puesto}
        for puesto in Puesto:
            plazas = [p for p in semana["plazas"] if p["puesto"] == puesto]
            if plazas:
                valores[puesto.value] = "\n".join(
                    p["nombre"] or "—" for p in sorted(plazas, key=lambda p: p["cupo"])
                )
        for clave in ("limpieza", "hospitalidad"):
            valores[clave] = f"Grupo # {semana[clave]}"
        celdas[indice] = valores
    return celdas


def exportar(programas: Programas, anio: int, mes: int) -> Path:
    version, contenido = programas.leer_publicacion(anio, mes)
    carpeta = programas.base.ruta.parent / "exportaciones"
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / f"Programa-{anio}-{mes:02d}-v{version}-{uuid4().hex[:10]}.xlsx"
    temporal = ruta.with_suffix(".tmp")
    libro = crear_libro(anio, mes, celdas_publicadas(contenido))
    try:
        libro.save(temporal)
        temporal.rename(ruta)
    finally:
        libro.close()
        temporal.unlink(missing_ok=True)
    return ruta
