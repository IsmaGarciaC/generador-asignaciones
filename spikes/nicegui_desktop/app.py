"""Prueba de escritorio con un programa ficticio en memoria."""

import webbrowser
from functools import partial

from nicegui import app, html, ui
from nicegui.events import ValueChangeEventArguments

TITULO = 'Programa mensual de asignaciones'
PLAZAS = (
    'Audio', 'Video', 'Micrófonos 1', 'Micrófonos 2', 'Acomodador 1', 'Acomodador 2',
    'Plataforma', 'Lector del martes', 'Presidente', 'Lector de La Atalaya',
)
SEMANAS = range(1, 6)
PERSONAS = [f'Persona {numero:02d}' for numero in range(1, 13)]
asignaciones = {
    (plaza, semana): PERSONAS[(fila + semana - 1) % len(PERSONAS)]
    for fila, plaza in enumerate(PLAZAS)
    for semana in SEMANAS
}


def abrir_whatsapp() -> None:
    if not webbrowser.open('https://wa.me/', new=2):
        ui.notify('Windows no pudo abrir el navegador predeterminado.')


@ui.page('/')
def mostrar_programa() -> None:
    ui.add_css("""
        body { background: #f5f7f8; color: #193631; font-family: 'Segoe UI', sans-serif; }
        .nicegui-content { margin: auto; width: 100%; max-width: 1400px; padding: 1rem; }
        .cabecera { display: flex; flex-wrap: wrap; align-items: center;
                    justify-content: space-between; gap: .75rem; width: 100%; }
        h1 { font: 600 1.65rem/1.2 'Segoe UI', sans-serif; margin: 0; }
        .contenedor { width: 100%; overflow-x: auto; border: 1px solid #cbd6d3; }
        table { width: 100%; min-width: 52rem; border-spacing: 0; background: white; }
        th, td { padding: .2rem .55rem; text-align: left; border-bottom: 1px solid #dce4e2; }
        thead th { padding-block: .6rem; background: #22594f; color: white; }
        tbody th { background: #f0f5f3; }
        th:first-child { position: sticky; left: 0; z-index: 1; }
    """)
    with html.header().classes('cabecera'):
        html.h1(TITULO)
        ui.button('Probar enlace de WhatsApp', on_click=abrir_whatsapp).props('outline')
    estado = ui.label('Datos ficticios · Los cambios duran hasta cerrar la aplicación.')

    def editar(plaza: str, semana: int, evento: ValueChangeEventArguments) -> None:
        asignaciones[plaza, semana] = evento.value
        estado.set_text(f'Semana {semana} · {plaza} · {asignaciones[plaza, semana]}')

    with html.div().classes('contenedor'), html.table():
        with html.thead(), html.tr():
            html.th('Plaza', scope='col')
            for semana in SEMANAS:
                html.th(f'Semana {semana}', scope='col')
        with html.tbody():
            for plaza in PLAZAS:
                with html.tr():
                    html.th(plaza, scope='row')
                    for semana in SEMANAS:
                        with html.td():
                            ui.select(
                                PERSONAS,
                                value=asignaciones[plaza, semana],
                                on_change=partial(editar, plaza, semana),
                            ).props(f'dense borderless aria-label="{plaza}, semana {semana}"')


def iniciar() -> None:
    app.native.start_args['gui'] = 'edgechromium'
    ui.run(
        native=True, host='127.0.0.1', reload=False, show=False,
        window_size=(1140, 800), title=TITULO, show_welcome_message=False,
    )


if __name__ == '__main__':
    iniciar()
