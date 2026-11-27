"""Coordina la generación de un borrador y la exportación de una publicación."""

from contextlib import closing
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from generador_asignaciones_v2.dominio.programa import Borrador
from generador_asignaciones_v2.dominio.puestos import Puesto
from generador_asignaciones_v2.impresion import convertir_a_pdf, renderizar_paginas
from generador_asignaciones_v2.optimizador import Resultado
from generador_asignaciones_v2.persistencia.programas import Programas, VistaMes
from generador_asignaciones_v2.plantilla_excel import crear_libro
from generador_asignaciones_v2.regeneracion import Alcance, regenerar


def generar(
    programas: Programas,
    vista: VistaMes,
    borrador: Borrador,
    *,
    alcance: Alcance = None,
) -> Resultado:
    if vista.historico:
        raise ValueError("El historial importado se conserva para consulta.")
    if not vista.contexto.personas:
        raise ValueError("Agrega o importa el padrón antes de generar.")
    resultado = regenerar(
        replace(vista.contexto, semanas=borrador.semanas),
        borrador.plan,
        borrador.bloqueos,
        alcance,
    )
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
    try:
        with closing(crear_libro(anio, mes, celdas_publicadas(contenido))) as libro:
            libro.save(temporal)
        temporal.rename(ruta)
    finally:
        temporal.unlink(missing_ok=True)
    return ruta


def exportar_imprimibles(programas: Programas, anio: int, mes: int) -> Path:
    """Publica el Excel, el PDF y sus páginas PNG de una sola versión, juntos."""
    version, contenido = programas.leer_publicacion(anio, mes)
    carpeta = programas.base.ruta.parent / "exportaciones"
    carpeta.mkdir(parents=True, exist_ok=True)
    nombre = f"Programa-{anio}-{mes:02d}-v{version}-{uuid4().hex[:10]}"
    destino = carpeta / nombre
    with TemporaryDirectory(prefix=".impresion-", dir=carpeta) as temporal:
        preparado = Path(temporal) / nombre
        preparado.mkdir()
        excel = preparado / f"{nombre}.xlsx"
        with closing(crear_libro(anio, mes, celdas_publicadas(contenido))) as libro:
            libro.save(excel)
        pdf = convertir_a_pdf(excel)
        renderizar_paginas(pdf)
        preparado.rename(destino)
    return destino
