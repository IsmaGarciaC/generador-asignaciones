import asyncio
import json
from contextlib import closing
from datetime import date
from functools import partial
from pathlib import Path

import pytest
from nicegui import ui
from nicegui.testing import user_simulation
from pypdfium2 import PdfDocument

from generador_asignaciones_v2 import flujo_mensual
from generador_asignaciones_v2.dominio.puestos import Puesto
from generador_asignaciones_v2.escritorio import mostrar_inicio
from generador_asignaciones_v2.persistencia.base_datos import BaseDatos
from generador_asignaciones_v2.persistencia.programas import Programas


def test_boton_crea_y_confirma_un_respaldo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    with closing(BaseDatos(tmp_path / "programa.sqlite3")) as base:
        base.preparar()

        async def probar_boton() -> None:
            async with user_simulation(root=partial(mostrar_inicio, Programas(base))) as usuario:
                await usuario.open("/")
                usuario.find("Crear respaldo").click()
                await usuario.should_see("Respaldo guardado en", retries=20)

        asyncio.run(probar_boton())
    assert len(list((tmp_path / "respaldos").glob("manual-*.sqlite3"))) == 1


def test_ventana_importa_genera_publica_con_vacantes_y_exporta(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    def conversion_de_prueba(excel: Path) -> Path:
        pdf = excel.with_suffix(".pdf")
        with closing(PdfDocument.new()) as documento:
            documento.new_page(842, 595).close()
            documento.new_page(595, 842).close()
            documento.save(pdf)
        return pdf

    monkeypatch.setattr(flujo_mensual, "convertir_a_pdf", conversion_de_prueba)
    respaldo = tmp_path / "Copia V1"
    respaldo.mkdir()
    (respaldo / "hermanos.json").write_text(
        json.dumps(
            [
                {"id": 1, "nombre": "Persona Uno", "roles": ["audio"]},
                {"id": 2, "nombre": "Persona Dos", "roles": ["audio"]},
            ]
        ),
        encoding="utf-8",
    )
    with closing(BaseDatos(tmp_path / "privado" / "programa.sqlite3")) as base:
        base.preparar()
        programas = Programas(base)

        async def recorrer_ventana() -> None:
            async with user_simulation(root=partial(mostrar_inicio, programas)) as usuario:
                await usuario.open("/")
                usuario.find("Importar V1").click()
                usuario.find("Carpeta del respaldo V1").type(str(respaldo))
                usuario.find("Revisar copia").click()
                await usuario.should_see("Aplicar importación", retries=20)
                usuario.find("Aplicar importación").click()
                await usuario.should_see("Importadas 2 personas", retries=20)
                usuario.find("Programa mensual").click()
                await usuario.should_not_see("Agrega o importa el padrón antes de generar.")
                usuario.find("Generar mes").click()
                await usuario.should_see("Programa generado", retries=30)
                hoy = date.today()
                generado = programas.leer(hoy.year, hoy.month)
                semanas = len(generado.borrador.semanas)
                await usuario.should_see(f"{semanas} de {semanas * 10} plazas cubiertas")
                fecha = generado.borrador.semanas[0].inicio
                plaza = fecha, Puesto.AUDIO, 1
                otra = {1, 2}.difference({generado.borrador.plan[plaza]}).pop()
                nombre = generado.contexto.personas[otra].nombre
                usuario.find(kind=ui.select, marker=f"plaza-{fecha}-audio-1").click()
                usuario.find(nombre).click()
                usuario.find("Carga y descanso").click()
                await usuario.should_see(kind=ui.table)
                esperado = tuple(generado.borrador.plan.values()).count(otra) + 1
                for _ in range(20):
                    (tabla,) = usuario.find(kind=ui.table).elements
                    if any(f["id"] == otra and f["total"] == esperado for f in tabla.rows):
                        break
                    await asyncio.sleep(0.1)
                else:
                    pytest.fail("El resumen no reflejó la edición antes del guardado.")
                usuario.find(kind=ui.button, marker=f"bloqueo-{fecha}-audio-1").click()
                await usuario.should_see("Plazas bloqueadas: 1")
                usuario.find("Guardar borrador").click()
                await usuario.should_see("Borrador guardado")
                guardado = programas.leer(hoy.year, hoy.month).borrador
                assert guardado.plan[plaza] == otra
                assert guardado.bloqueos == frozenset({plaza})
                usuario.find("Publicar").click()
                await usuario.should_see("Confirmar publicación")
                usuario.find("Confirmar publicación").click()
                await usuario.should_see("Programa publicado · versión 1", retries=20)
                await usuario.open("/")
                await usuario.should_see("Publicado · versión 1")
                usuario.find("Exportar Excel").click()
                await usuario.should_see("Excel guardado en", retries=20)
                usuario.find("Exportar PDF y PNG").click()
                await usuario.should_see("Excel, PDF y PNG guardados en", retries=20)
                usuario.find("Alcance").click()
                usuario.find("Una semana").click()
                await usuario.should_see("Regenerar semana")
                usuario.find("Regenerar semana").click()
                await usuario.should_see("El programa se repite", retries=30)
                vigente = programas.leer(hoy.year, hoy.month).borrador
                assert vigente == guardado
                programas.guardar_ausencias(hoy.year, hoy.month, otra, frozenset({fecha}))
                await usuario.open("/")
                await usuario.should_see(
                    f"{fecha:%d/%m} · audio 1: bloqueo inválido, {nombre} "
                    "tiene una ausencia registrada."
                )

        asyncio.run(recorrer_ventana())
    exportaciones = tmp_path / "privado" / "exportaciones"
    assert len(list(exportaciones.glob("*.xlsx"))) == 1
    (carpeta,) = (ruta for ruta in exportaciones.iterdir() if ruta.is_dir())
    assert sorted(r.suffix for r in carpeta.iterdir()) == [".pdf", ".png", ".png", ".xlsx"]
