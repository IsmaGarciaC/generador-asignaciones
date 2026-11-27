"""Ventana local y acciones del programa mensual."""

import os
import sqlite3
from collections import Counter
from collections.abc import Callable
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

from nicegui import app, html, run, ui
from nicegui.events import ValueChangeEventArguments
from sqlalchemy.exc import SQLAlchemyError

from generador_asignaciones_v2.dominio.programa import Borrador, Semana, grupos_semanales
from generador_asignaciones_v2.dominio.puestos import CUPOS_HABITUALES, Puesto
from generador_asignaciones_v2.flujo_mensual import exportar, generar
from generador_asignaciones_v2.importacion_v1 import aplicar, previsualizar
from generador_asignaciones_v2.persistencia.programas import Programas, VistaMes

TITULO = "Generador de Asignaciones"
MESES = dict(
    enumerate(
        (
            "Enero",
            "Febrero",
            "Marzo",
            "Abril",
            "Mayo",
            "Junio",
            "Julio",
            "Agosto",
            "Septiembre",
            "Octubre",
            "Noviembre",
            "Diciembre",
        ),
        1,
    )
)
PUESTOS = {
    Puesto.AUDIO: "Audio",
    Puesto.VIDEO: "Video",
    Puesto.ACOMODADOR: "Acomodadores",
    Puesto.MICROFONOS: "Micrófonos",
    Puesto.PLATAFORMA: "Plataforma",
    Puesto.LECTOR_MARTES: "Lector del martes",
    Puesto.PRESIDENTE: "Presidente",
    Puesto.LECTOR_DOMINGO: "Lector de La Atalaya",
}


async def _operar[T](accion: Callable[[], T]) -> tuple[bool, T | None]:
    try:
        return True, await run.io_bound(accion)
    except ValueError as error:
        ui.notify(str(error), type="warning", timeout=9000)
    except (OSError, sqlite3.Error, SQLAlchemyError):
        ui.notify("No se pudo completar la operación local. Vuelve a intentarlo.", type="negative")
    return False, None


def _nombres(vista: VistaMes) -> dict[int, str]:
    personas = vista.contexto.personas.values()
    duplicados = Counter(p.nombre.casefold() for p in personas)
    return {
        p.id: f"{p.nombre} · #{p.id}" if duplicados[p.nombre.casefold()] > 1 else p.nombre
        for p in personas
    }


def _matriz(vista: VistaMes) -> dict:
    borrador = vista.borrador
    nombres = _nombres(vista)
    requeridas = set(vista.contexto.plazas())
    grupos = grupos_semanales(borrador.semanas, borrador.num_grupos, borrador.grupo_inicial)
    controles = {}
    with html.div().classes("matriz"), html.table(**{"aria-label": "Asignaciones por semana"}):
        with html.thead(), html.tr():
            html.th("Plaza", scope="col")
            for semana in borrador.semanas:
                domingo = semana.inicio + timedelta(days=5)
                html.th(f"{semana.inicio:%d/%m} – {domingo:%d/%m}", scope="col")
        with html.tbody():
            for puesto, cupos in CUPOS_HABITUALES.items():
                for numero in range(1, cupos + 1):
                    etiqueta = f"{PUESTOS[puesto]} {numero}" if cupos > 1 else PUESTOS[puesto]
                    with html.tr():
                        html.th(etiqueta, scope="row")
                        for semana in borrador.semanas:
                            plaza = semana.inicio, puesto, numero
                            persona = borrador.plan.get(plaza)
                            with html.td():
                                if vista.historico:
                                    html.span(nombres.get(persona, "Sin dato"))
                                elif plaza not in requeridas:
                                    html.span("Cancelada" if semana.cancelada else "No requerido")
                                else:
                                    candidatos = vista.contexto.candidatos(plaza)
                                    opciones = {i: nombres[i] for i in candidatos}
                                    if persona is not None and persona not in opciones:
                                        opciones[persona] = f"{nombres[persona]} · revisar"
                                    control = ui.select(
                                        opciones, value=persona, clearable=True
                                    )
                                    controles[plaza] = control
                                    control.mark(f"plaza-{semana.inicio}-{puesto.value}-{numero}")
                                    control.props(
                                        f'dense borderless placeholder="Pendiente" '
                                        f'aria-label="{etiqueta} {semana.inicio:%d/%m}"'
                                    ).classes("w-full")
                                    if persona is None:
                                        texto = "Pendiente" if opciones else "Sin candidatos"
                                        control.props(f'display-value="{texto}"')
                                    control.on_value_change(_mostrar_vacante)
            if not vista.historico:
                for indice, etiqueta in enumerate(("Limpieza", "Hospitalidad")):
                    with html.tr():
                        html.th(etiqueta, scope="row")
                        for semana in borrador.semanas:
                            grupo = grupos[semana.inicio][indice]
                            html.td(f"Grupo {grupo}" if grupo is not None else "Cancelada")
    return controles


def _mostrar_vacante(evento: ValueChangeEventArguments) -> None:
    if evento.value is None:
        evento.sender.props('display-value="Pendiente"')
    else:
        evento.sender.props(remove="display-value")


def _programa(programas: Programas, vista: VistaMes, refrescar: Callable[[], None]) -> None:
    borrador = vista.borrador
    plazas = set(vista.contexto.plazas())
    pendientes = plazas - borrador.plan.keys()
    html.h2(f"{MESES[borrador.mes]} {borrador.anio}")
    if vista.historico:
        ui.label("Historial importado")
        _matriz(vista)
        return
    if vista.publicado_al_dia:
        estado = f"Publicado · versión {vista.version}"
    elif vista.version:
        estado = f"Borrador · sigue vigente la versión {vista.version}"
    else:
        estado = "Borrador"
    ui.label(f"{estado} · {len(plazas) - len(pendientes)} de {len(plazas)} plazas cubiertas")
    calendario = {}
    with ui.expansion("Calendario y grupos", icon="event").classes("w-full bg-white"):
        with ui.row().classes("gap-4"):
            cantidad = ui.number("Número de grupos", value=borrador.num_grupos, min=1, step=1)
            inicial = ui.number("Grupo inicial", value=borrador.grupo_inicial, min=1, step=1)
        for semana in borrador.semanas:
            with ui.row().classes("items-center gap-3 w-full border-t border-slate-200"):
                ui.label(f"{semana.inicio:%d/%m}").classes("font-medium")
                martes = ui.checkbox("Martes", value=semana.martes)
                domingo = ui.checkbox("Domingo", value=semana.domingo)
                inactivos = ui.select(
                    PUESTOS,
                    label="Puestos desactivados",
                    multiple=True,
                    value=sorted(semana.desactivados),
                ).classes("min-w-56")
                calendario[semana.inicio] = (martes, domingo, inactivos)
    controles = _matriz(vista)

    def tomar() -> Borrador:
        if any(c.value is None or int(c.value) != c.value for c in (cantidad, inicial)):
            raise ValueError("Escribe números enteros para los grupos.")
        semanas = tuple(
            Semana(fecha, martes.value, domingo.value, frozenset(map(Puesto, desactivados.value)))
            for fecha, (martes, domingo, desactivados) in calendario.items()
        )
        requeridas = {plaza for semana in semanas for plaza in semana.plazas()}
        plan = {
            plaza: c.value
            for plaza, c in controles.items()
            if c.value is not None and plaza in requeridas
        }
        return replace(
            borrador,
            semanas=semanas,
            plan=plan,
            num_grupos=int(cantidad.value),
            grupo_inicial=int(inicial.value),
        )

    async def guardar() -> None:
        try:
            cambios = tomar()
        except ValueError as error:
            ui.notify(str(error), type="warning")
            return
        if (await _operar(lambda: programas.guardar(vista, cambios)))[0]:
            ui.notify("Borrador guardado", type="positive")
            refrescar()

    async def generar_mes() -> None:
        try:
            cambios = tomar()
            grupos_semanales(cambios.semanas, cambios.num_grupos, cambios.grupo_inicial)
        except ValueError as error:
            ui.notify(str(error), type="warning")
            return
        boton_generar.disable()
        boton_guardar.disable()
        boton_publicar.disable()
        resultado = None
        try:
            exito, resultado = await _operar(lambda: generar(programas, vista, cambios))
        finally:
            if resultado is None or resultado.plan is None:
                boton_generar.enable()
                boton_guardar.enable()
                boton_publicar.set_enabled(
                    vista.revision is not None and not vista.publicado_al_dia
                )
        if not exito or resultado is None:
            return
        if resultado.plan is None:
            ui.notify(
                {
                    "UNKNOWN": "Búsqueda agotada sin encontrar un programa.",
                    "INFEASIBLE": "Las restricciones son incompatibles.",
                    "MODEL_INVALID": "El motor detectó un error en el modelo.",
                }.get(resultado.estado, "El motor terminó sin producir un programa."),
                type="warning",
            )
            return
        mensaje = "Programa generado · óptimo demostrado"
        if resultado.estado != "OPTIMAL":
            probados = ", ".join(resultado.objetivos_probados)
            mensaje = "Programa factible · optimalidad pendiente"
            if probados:
                mensaje += f" · Objetivos demostrados: {probados}"
        ui.notify(mensaje, type="positive")
        refrescar()

    async def confirmar(aceptar: bool) -> None:
        exito, version = await _operar(lambda: programas.publicar(vista, acepta_vacantes=aceptar))
        if exito:
            ui.notify(f"Programa publicado · versión {version}", type="positive")
            refrescar()

    async def publicar() -> None:
        try:
            if tomar() != borrador:
                ui.notify("Guarda el borrador antes de publicar.", type="warning")
                return
        except ValueError as error:
            ui.notify(str(error), type="warning")
            return
        if not pendientes:
            await confirmar(False)
            return
        with ui.dialog() as dialogo, ui.card().classes("max-w-lg"):
            html.h3(f"Publicar con {len(pendientes)} plazas pendientes")
            with ui.column().classes("max-h-48 overflow-y-auto gap-1"):
                for fecha, puesto, numero in sorted(pendientes):
                    ui.label(f"{fecha:%d/%m} · {PUESTOS[puesto]} {numero}")

            async def aceptar() -> None:
                dialogo.close()
                await confirmar(True)

            with ui.row().classes("justify-end"):
                ui.button("Volver", on_click=dialogo.close).props("flat")
                ui.button("Confirmar publicación", on_click=aceptar)
        dialogo.open()

    ultimo_excel: Path | None = None

    async def excel() -> None:
        nonlocal ultimo_excel
        exito, archivo = await _operar(lambda: exportar(programas, borrador.anio, borrador.mes))
        if exito and archivo is not None:
            ultimo_excel = archivo
            destino.set_text(f"Excel guardado en {archivo}")
            abrir.set_visibility(os.name == "nt")

    async def abrir_excel() -> None:
        if ultimo_excel is not None:
            archivo = ultimo_excel
            await _operar(lambda: os.startfile(archivo))

    with ui.row().classes("items-center gap-2"):
        boton_generar = ui.button("Generar mes", on_click=generar_mes, icon="auto_awesome")
        boton_guardar = ui.button("Guardar borrador", on_click=guardar).props("outline")
        boton_publicar = ui.button("Publicar", on_click=publicar).props("outline")
        boton_publicar.set_enabled(vista.revision is not None and not vista.publicado_al_dia)
        boton = ui.button("Exportar Excel", on_click=excel, icon="download").props("outline")
        boton.set_enabled(vista.version is not None)
        abrir = ui.button("Abrir archivo", on_click=abrir_excel, icon="open_in_new").props("flat")
        abrir.set_visibility(False)
    destino = ui.label().classes("break-all")


def _padron(programas: Programas, vista: VistaMes, actualizar: Callable[[], None]) -> None:
    selector = ui.select({0: "Nueva persona", **_nombres(vista)}, value=0, label="Persona").classes(
        "w-72"
    )
    anio, mes = vista.borrador.anio, vista.borrador.mes

    def refrescar(ident: int) -> None:
        nonlocal vista
        vista = programas.leer(anio, mes)
        selector.set_options({0: "Nueva persona", **_nombres(vista)}, value=ident)
        formulario.refresh()
        actualizar()

    @ui.refreshable
    def formulario() -> None:
        ident = selector.value
        persona = vista.contexto.personas.get(ident)
        with ui.row().classes("gap-4"):
            nombre = ui.input("Nombre", value=persona.nombre if persona else "")
            telefono = ui.input("Teléfono", value=(persona.telefono or "") if persona else "")
            activa = ui.checkbox("Activa", value=persona.activa if persona else True)
        roles = ui.select(
            PUESTOS,
            value=sorted(persona.puestos) if persona else [],
            label="Capacitaciones",
            multiple=True,
        ).classes("w-full max-w-xl")

        async def guardar() -> None:
            exito, nueva = await _operar(
                lambda: programas.guardar_persona(
                    ident or None,
                    nombre.value,
                    telefono.value,
                    frozenset(map(Puesto, roles.value)),
                    activa.value,
                )
            )
            if exito:
                ui.notify("Persona guardada", type="positive")
                refrescar(nueva or 0)

        ui.button("Guardar persona", on_click=guardar)
        if persona and not vista.historico:
            html.h3("Ausencias del mes").classes("mt-4")
            fechas = {s.inicio.isoformat(): f"{s.inicio:%d/%m}" for s in vista.borrador.semanas}
            registradas = [
                f for f in fechas if (ident, date.fromisoformat(f)) in vista.contexto.ausencias
            ]
            ausencias = ui.select(
                fechas,
                label="Semanas completas",
                multiple=True,
                value=registradas,
            ).classes("w-72")

            async def guardar_ausencias() -> None:
                exito, _ = await _operar(
                    lambda: programas.guardar_ausencias(
                        anio,
                        mes,
                        ident,
                        frozenset(date.fromisoformat(d) for d in ausencias.value),
                    )
                )
                if exito:
                    ui.notify("Ausencias guardadas", type="positive")
                    refrescar(ident)

            ui.button("Guardar ausencias", on_click=guardar_ausencias).props("outline")

    selector.on_value_change(lambda: formulario.refresh())
    formulario()


def _importacion(programas: Programas, anio: int, mes: int, actualizar: Callable[[], None]) -> None:
    ui.label(f"Datos V1 para planificar {MESES[mes]} {anio}").classes("font-medium")
    origen = ui.input("Carpeta del respaldo V1", placeholder=r"C:\Copias\V1\data").classes(
        "w-full max-w-xl"
    )

    def mostrar_pendientes(pendientes: list[str] | tuple[str, ...]) -> None:
        if pendientes:
            with ui.expansion(f"{len(pendientes)} registros para revisar").classes("w-full"):
                for mensaje in pendientes:
                    ui.label(mensaje)

    async def revisar() -> None:
        ruta = Path(origen.value.strip().strip('"'))
        if not ruta.is_absolute():
            ui.notify("Escribe la ruta completa de la carpeta del respaldo.", type="warning")
            return
        resultados.clear()
        exito, vista = await _operar(lambda: previsualizar(ruta, anio, mes))
        if not exito or vista is None:
            return

        async def guardar() -> None:
            exito, resumen = await _operar(lambda: aplicar(programas.base, vista))
            if exito and resumen is not None:
                resultados.clear()
                with resultados:
                    if resumen["repetido"]:
                        ui.label("Esta copia ya se había importado.")
                    else:
                        ui.label(
                            f"Importadas {resumen['personas_nuevas']} personas, "
                            f"{resumen['ausencias_nuevas']} ausencias y "
                            f"{resumen['asignaciones_historicas']} asignaciones históricas."
                        )
                    mostrar_pendientes(resumen["pendientes"])
                    if vista.grupo_sugerido:
                        ui.label(f"Próximo grupo registrado en V1 · {vista.grupo_sugerido}")
                actualizar()

        with resultados:
            asignaciones = sum(map(len, vista.historial.values()))
            ui.label(
                f"{len(vista.personas)} personas · {len(vista.ausencias)} ausencias · "
                f"{asignaciones} asignaciones históricas verificables"
            )
            mostrar_pendientes(vista.pendientes)
            ui.button("Aplicar importación", on_click=guardar)

    ui.button("Revisar copia", on_click=revisar, icon="folder_open").props("outline")
    resultados = ui.column().classes("w-full")


def mostrar_inicio(programas: Programas) -> None:
    hoy = date.today()
    periodo = hoy.year, hoy.month

    @ui.refreshable
    def programa() -> None:
        _programa(programas, programas.leer(*periodo), programa.refresh)

    @ui.refreshable
    def padron() -> None:
        _padron(programas, programas.leer(*periodo), programa.refresh)

    def actualizar() -> None:
        programa.refresh()
        padron.refresh()

    @ui.refreshable
    def importar() -> None:
        _importacion(programas, *periodo, actualizar)

    def cargar() -> None:
        nonlocal periodo
        anio = campo_anio.value
        if anio is None or int(anio) != anio or not 1900 <= anio <= 9998:
            ui.notify("Escribe un año entre 1900 y 9998.", type="warning")
            return
        periodo = int(anio), campo_mes.value
        actualizar()
        importar.refresh()

    async def respaldar() -> None:
        exito, ruta = await _operar(programas.base.respaldar)
        if exito:
            ui.notify(f"Respaldo guardado en {ruta}", type="positive", timeout=8000)

    ui.colors(primary="#235648", positive="#235648")
    ui.add_css("""
        body { background: #f4f6f5; color: #19332c; font-family: "Segoe UI", sans-serif; }
        main { width: min(100%, 82rem); margin: auto; padding: .5rem clamp(.25rem, 2vw, 1.5rem); }
        h1, h2, h3 { margin: 0; font-weight: 650; }
        h1 { font-size: clamp(1.65rem, 4vw, 2.25rem); }
        h2 { font-size: 1.5rem; } h3 { font-size: 1.05rem; }
        .matriz { overflow-x: auto; width: 100%; border: 1px solid #cbd8d2; border-radius: .5rem; }
        .matriz table { background: white; border-spacing: 0; width: 100%; min-width: 55rem; }
        .matriz th, .matriz td { padding: .2rem .6rem; border-bottom: 1px solid #e2eae6; }
        .matriz thead th { padding-block: .65rem; color: white; background: #235648; }
        .matriz tbody th { text-align: left; background: #eef3f1; width: 12rem; }
        .matriz th:first-child { position: sticky; left: 0; z-index: 1; }
        .matriz td { min-width: 8rem; }
    """)
    with html.main():
        with ui.row().classes("w-full justify-between items-center gap-4"):
            html.h1(TITULO)
            ui.button("Crear respaldo", on_click=respaldar).props("flat")
        with ui.row().classes("items-center gap-3 my-3"):
            campo_mes = ui.select(MESES, value=hoy.month, label="Mes").classes("w-40")
            campo_anio = ui.number("Año", value=hoy.year, min=1900, max=9998).classes("w-24")
            ui.button("Cargar mes", on_click=cargar).props("outline")
        with ui.tabs().classes("self-start") as tabs:
            tab_programa = ui.tab("Programa mensual")
            tab_padron = ui.tab("Padrón")
            tab_importar = ui.tab("Importar V1")
        with ui.tab_panels(tabs, value=tab_programa).classes("w-full bg-transparent"):
            with ui.tab_panel(tab_programa).classes("px-0"):
                programa()
            with ui.tab_panel(tab_padron).classes("px-0"):
                padron()
            with ui.tab_panel(tab_importar).classes("px-0"):
                importar()


def iniciar(programas: Programas) -> None:
    @ui.page("/")
    def inicio() -> None:
        mostrar_inicio(programas)

    app.native.start_args["gui"] = "edgechromium"
    ui.run(
        native=True,
        host="127.0.0.1",
        reload=False,
        show=False,
        title=TITULO,
        language="es",
        window_size=(1080, 790),
        show_welcome_message=False,
    )
