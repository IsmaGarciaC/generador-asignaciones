"""Ventana nativa, catálogo semanal y acción de respaldo local."""

import sqlite3
from collections.abc import Callable
from pathlib import Path

from nicegui import app, html, run, ui

from generador_asignaciones_v2.dominio.puestos import CUPOS_HABITUALES, Puesto

TITULO = "Generador de Asignaciones"
NOMBRES_PUESTOS = {
    Puesto.AUDIO: "Audio",
    Puesto.VIDEO: "Video",
    Puesto.ACOMODADOR: "Acomodadores",
    Puesto.MICROFONOS: "Micrófonos",
    Puesto.PLATAFORMA: "Plataforma",
    Puesto.LECTOR_MARTES: "Lector del martes (Estudio Bíblico)",
    Puesto.PRESIDENTE: "Presidente",
    Puesto.LECTOR_DOMINGO: "Lector de La Atalaya",
}


def mostrar_inicio(crear_respaldo: Callable[[], Path]) -> None:
    async def respaldar() -> None:
        try:
            ruta = await run.io_bound(crear_respaldo)
        except (OSError, sqlite3.Error) as error:
            ui.notify(f"No se pudo crear el respaldo. {error}", type="negative")
        else:
            ui.notify(f"Respaldo guardado en {ruta}", type="positive", timeout=8000)

    ui.add_css("""
        body { background: #f4f6f5; color: #1c312d; font-family: "Segoe UI", sans-serif; }
        .nicegui-content { padding: 0; }
        .inicio { width: min(100%, 52rem); margin: 0 auto; padding: 2rem clamp(1rem, 5vw, 3rem); }
        .inicio h1 { margin: 0; font-size: clamp(1.65rem, 4vw, 2.35rem); font-weight: 650; }
        .inicio h2 { margin: 1.65rem 0 .7rem; font-size: 1.15rem; font-weight: 650; }
        .inicio table {
            width: 100%; table-layout: fixed; border-spacing: 0; overflow: hidden;
            background: white; border: 1px solid #c9d4d0; border-radius: .65rem;
        }
        .inicio th, .inicio td { padding: .6rem .9rem; text-align: left; }
        .inicio thead, .inicio tfoot { background: #e4ece8; }
        .inicio tbody td, .inicio tbody th, .inicio tfoot td, .inicio tfoot th {
            border-top: 1px solid #dbe4e0;
        }
        .inicio tbody th { font-weight: 400; }
        .inicio tr > :last-child { width: 5.5rem; text-align: right; }
        .inicio tfoot td { font-weight: 650; }
    """)
    with html.main().classes("inicio"):
        html.h1(TITULO)
        html.h2("Puestos de una semana habitual", id="titulo-catalogo")
        with html.table(**{"aria-labelledby": "titulo-catalogo"}):
            with html.thead(), html.tr():
                html.th("Puesto", scope="col")
                html.th("Plazas", scope="col")
            with html.tbody():
                for puesto, cupo in CUPOS_HABITUALES.items():
                    with html.tr():
                        html.th(NOMBRES_PUESTOS[puesto], scope="row")
                        html.td(str(cupo))
            with html.tfoot(), html.tr():
                html.th("Total semanal", scope="row")
                html.td(str(sum(CUPOS_HABITUALES.values())))
        ui.button("Crear respaldo", on_click=respaldar).props("outline").classes("mt-5")


def iniciar(crear_respaldo: Callable[[], Path]) -> None:
    @ui.page("/")
    def inicio() -> None:
        mostrar_inicio(crear_respaldo)

    app.native.start_args["gui"] = "edgechromium"
    ui.run(
        native=True,
        host="127.0.0.1",
        reload=False,
        show=False,
        title=TITULO,
        language="es",
        window_size=(920, 720),
        show_welcome_message=False,
    )
