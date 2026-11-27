import json
from collections import Counter
from collections.abc import Iterator
from contextlib import closing
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path
from zipfile import ZipFile

import pytest
from openpyxl import load_workbook
from sqlalchemy.exc import IntegrityError

from exportador_excel import exportar_programa_excel
from generador_asignaciones_v2.dominio.programa import (
    CargaPersona,
    Contexto,
    Persona,
    Semana,
    grupos_semanales,
    martes_del_mes,
    resumir_carga,
)
from generador_asignaciones_v2.dominio.puestos import CUPOS_HABITUALES, Puesto
from generador_asignaciones_v2.flujo_mensual import exportar, generar
from generador_asignaciones_v2.importacion_v1 import aplicar, previsualizar
from generador_asignaciones_v2.optimizador import resolver
from generador_asignaciones_v2.persistencia.base_datos import BaseDatos
from generador_asignaciones_v2.persistencia.programas import Programas


@pytest.fixture
def programas(tmp_path: Path) -> Iterator[Programas]:
    with closing(BaseDatos(tmp_path / "Perfil privado" / "programa.sqlite3")) as base:
        base.preparar()
        yield Programas(base)


def _json(carpeta: Path, nombre: str, contenido: object) -> None:
    (carpeta / nombre).write_text(json.dumps(contenido, ensure_ascii=False), encoding="utf-8")


def crear_copia(origen: Path) -> None:
    origen.mkdir()
    puestos = [p for p, cupos in CUPOS_HABITUALES.items() for _ in range(cupos)]
    _json(
        origen,
        "hermanos.json",
        [
            {"id": i, "nombre": f"Persona {i:02d}", "roles": [p.value]}
            for i, p in enumerate([*puestos, Puesto.AUDIO], 1)
        ],
    )
    _json(origen, "ausencias.json", {"2026-12": {"Persona 01": [1], "Persona 11": [1]}})
    _json(
        origen,
        "asignaciones_2026_11.json",
        {
            "1": {"audio": ["Persona 01"], "video": [1], "plataforma": ["Sin coincidencia"]},
            "2": {"audio": ["Persona 11"]},
        },
    )
    _json(
        origen,
        "estado.json",
        {
            "ultimo_anio": 2026,
            "ultimo_mes": 11,
            "siguiente_grupo_limpieza": 4,
        },
    )


def test_calendario_y_rotacion_no_consumen_grupo_en_semana_cancelada() -> None:
    fechas = martes_del_mes(2026, 12)
    assert len(fechas) == 5 and fechas[-1] + timedelta(days=5) == date(2027, 1, 3)
    semanas = (
        Semana(fechas[0], martes=False),
        Semana(fechas[1], martes=False, domingo=False),
        Semana(fechas[2], domingo=False, desactivados=frozenset({Puesto.VIDEO})),
    )
    assert [len(s.plazas()) for s in semanas] == [9, 0, 7]
    assert list(grupos_semanales(semanas, 4, 4).values()) == [(4, 3), (None, None), (1, 4)]
    assert list(grupos_semanales(semanas, 3, 3).values()) == [(3, 2), (None, None), (1, 3)]


def test_motor_maximiza_cobertura_y_distingue_incertidumbre() -> None:
    fechas = martes_del_mes(2026, 12)
    principales = {Puesto.AUDIO, Puesto.VIDEO}
    semana = Semana(fechas[0], desactivados=frozenset(set(Puesto) - principales))
    contexto = Contexto(
        (semana,),
        {
            1: Persona(1, "Persona 01", frozenset(principales)),
            2: Persona(2, "Persona 02", frozenset({Puesto.AUDIO})),
        },
    )
    resultado = resolver(contexto)
    assert resultado.estado == "OPTIMAL"
    assert resultado.plan == {
        (semana.inicio, Puesto.VIDEO, 1): 1,
        (semana.inicio, Puesto.AUDIO, 1): 2,
    }
    assert not contexto.validar(resultado.plan)
    assert resolver(contexto, segundos=0).estado == "UNKNOWN"


def test_motor_alterna_el_mismo_puesto_desde_la_ultima_semana_del_mes_anterior() -> None:
    fechas = martes_del_mes(2026, 12)[:4]
    anterior = fechas[0] - timedelta(weeks=1)
    semanas = tuple(
        Semana(fecha, desactivados=frozenset(set(Puesto) - {Puesto.AUDIO})) for fecha in fechas
    )
    contexto = Contexto(
        semanas,
        {i: Persona(i, f"Persona {i}", frozenset({Puesto.AUDIO})) for i in (1, 2)},
        historial={(1, anterior): 1, (2, anterior): 1},
        puestos_historicos=frozenset({(1, anterior, Puesto.AUDIO)}),
    )
    resultado = resolver(contexto)
    assert resultado.estado == "OPTIMAL"
    assert resultado.plan is not None
    assert [resultado.plan[fecha, Puesto.AUDIO, 1] for fecha in fechas] == [2, 1, 2, 1]


@pytest.mark.parametrize("personas, frecuencias", [(5, [2] * 5), (10, [1] * 10)])
def test_motor_reparte_las_diez_plazas_del_mismo_puesto_en_todo_el_mes(
    personas: int,
    frecuencias: list[int],
) -> None:
    puestos = frozenset({Puesto.MICROFONOS, Puesto.ACOMODADOR})
    contexto = Contexto(
        tuple(
            Semana(fecha, desactivados=frozenset(set(Puesto) - puestos))
            for fecha in martes_del_mes(2026, 12)
        ),
        {i: Persona(i, f"Persona {i}", puestos) for i in range(1, personas + 1)},
    )
    resultado = resolver(contexto)
    assert resultado.plan is not None
    assert len(resultado.plan) == 20
    assert not contexto.validar(resultado.plan)
    for puesto in puestos:
        conteos = Counter(i for (_, rol, _), i in resultado.plan.items() if rol == puesto)
        assert sorted(conteos.values()) == frecuencias


def test_historial_desempata_sin_concentrar_puestos_con_igual_carga_mensual() -> None:
    puestos = frozenset({Puesto.AUDIO, Puesto.VIDEO})
    fechas = martes_del_mes(2026, 12)[:3]
    contexto = Contexto(
        tuple(Semana(f, desactivados=frozenset(set(Puesto) - puestos)) for f in fechas),
        {
            1: Persona(1, "Persona 1", frozenset({Puesto.AUDIO})),
            2: Persona(2, "Persona 2", frozenset({Puesto.VIDEO})),
            3: Persona(3, "Persona 3", puestos),
            4: Persona(4, "Persona 4", puestos),
        },
        historial={(3, date(2026, 11, 24)): 2, (4, date(2026, 11, 24)): 2},
    )
    resultado = resolver(contexto)
    assert resultado.estado == "OPTIMAL"
    assert resultado.plan is not None
    assert sorted(Counter(resultado.plan.values()).values()) == [1, 1, 2, 2]
    usos = {(puesto, persona) for (_, puesto, _), persona in resultado.plan.items()}
    assert len(usos) == len(resultado.plan) == 6


def test_descanso_evitar_una_tercera_semana_consecutiva_al_cambiar_de_mes() -> None:
    fecha = date(2026, 12, 1)
    puestos = frozenset({Puesto.AUDIO})
    contexto = Contexto(
        (Semana(fecha, desactivados=frozenset(set(Puesto) - puestos)),),
        {i: Persona(i, f"Persona {i}", puestos) for i in (1, 2)},
        historial={
            (1, date(2026, 11, 17)): 1,
            (1, date(2026, 11, 24)): 1,
            (2, date(2026, 11, 3)): 1,
            (2, date(2026, 11, 10)): 1,
        },
    )
    resultado = resolver(contexto)
    assert resultado.plan == {(fecha, Puesto.AUDIO, 1): 2}
    assert resultado.objetivos_probados[-2:] == (
        "descanso tras dos semanas",
        "rotación de parejas y puestos",
    )


def test_resumen_cuenta_doblete_en_una_semana_y_racha_del_mes_anterior() -> None:
    fechas = martes_del_mes(2026, 12)[:3]
    contexto = Contexto(
        tuple(map(Semana, fechas)),
        {1: Persona(1, "Persona 1"), 2: Persona(2, "Persona 2")},
        historial={(1, date(2026, 11, 17)): 1, (1, date(2026, 11, 24)): 2},
    )
    plan = {
        (fechas[0], Puesto.LECTOR_MARTES, 1): 1,
        (fechas[0], Puesto.MICROFONOS, 1): 1,
        (fechas[2], Puesto.PRESIDENTE, 1): 1,
    }
    assert resumir_carga(contexto, plan) == {
        1: CargaPersona(3, (fechas[0], fechas[2]), 3),
        2: CargaPersona(0, (), 0),
    }


def test_motor_prioriza_no_repetir_puesto_aun_si_la_carga_total_es_distinta() -> None:
    roles = (Puesto.AUDIO, Puesto.VIDEO, Puesto.PLATAFORMA)
    puestos = frozenset(roles)
    semanas = tuple(
        Semana(fecha, desactivados=frozenset(set(Puesto) - puestos))
        for fecha in martes_del_mes(2026, 12)[:3]
    )
    personas = {
        i: Persona(i, f"Persona {i}", frozenset({puesto})) for i, puesto in enumerate(roles, 1)
    }
    personas.update({i: Persona(i, f"Persona {i}", puestos) for i in (4, 5)})
    contexto = Contexto(semanas, personas)
    resultado = resolver(contexto)
    assert resultado.plan is not None
    assert len(resultado.plan) == 9
    assert not contexto.validar(resultado.plan)
    usos = {(puesto, persona) for (_, puesto, _), persona in resultado.plan.items()}
    assert len(usos) == 9
    assert sorted(Counter(resultado.plan.values()).values()) == [1, 1, 1, 3, 3]


def test_regenerar_mes_guarda_un_reparto_distinto_con_igual_calidad(programas: Programas) -> None:
    puestos = frozenset({Puesto.AUDIO, Puesto.VIDEO})
    for i in (1, 2):
        programas.guardar_persona(None, f"Persona {i}", "", puestos, True)
    vista = programas.leer(2026, 12)
    semanas = tuple(
        Semana(s.inicio, martes=False, domingo=False)
        if i > 1
        else Semana(s.inicio, desactivados=frozenset(set(Puesto) - puestos))
        for i, s in enumerate(vista.borrador.semanas)
    )
    primero = generar(programas, vista, replace(vista.borrador, semanas=semanas))
    vista = programas.leer(2026, 12)
    siguiente = generar(programas, vista, vista.borrador)
    assert primero.plan is not None and siguiente.plan is not None
    assert primero.estado == siguiente.estado == "OPTIMAL"
    assert len(primero.plan) == len(siguiente.plan) == 4
    assert all(primero.plan[plaza] != i for plaza, i in siguiente.plan.items())
    assert len({(puesto, i) for (_, puesto, _), i in siguiente.plan.items()}) == 4
    assert programas.leer(2026, 12).borrador.plan == siguiente.plan


def test_intercambiar_cupos_equivalentes_no_cuenta_como_otra_propuesta() -> None:
    fecha = date(2026, 12, 1)
    puesto = Puesto.MICROFONOS
    contexto = Contexto(
        (Semana(fecha, desactivados=frozenset(set(Puesto) - {puesto})),),
        {i: Persona(i, f"Persona {i}", frozenset({puesto})) for i in (1, 2)},
    )
    anterior = {(fecha, puesto, 1): 2, (fecha, puesto, 2): 1}
    resultado = resolver(contexto, anterior=anterior)
    assert resultado.plan == {(fecha, puesto, 1): 1, (fecha, puesto, 2): 2}
    assert resultado.aviso_variacion == "única"


def test_editar_publicar_reabrir_y_exportar_con_historial(programas: Programas, tmp_path: Path):
    copia = tmp_path / "Copia V1"
    crear_copia(copia)
    originales = {r.name: r.read_bytes() for r in copia.iterdir()}
    previa = previsualizar(copia, 2026, 12)
    assert previa.grupo_sugerido == 4
    assert not programas.leer(2026, 12).contexto.personas
    resumen = aplicar(programas.base, previa)
    assert resumen["asignaciones_historicas"] == 3
    assert len(resumen["pendientes"]) == 1
    assert aplicar(programas.base, previa)["repetido"]
    assert {r.name: r.read_bytes() for r in copia.iterdir()} == originales
    assert programas.leer(2026, 11).historico
    vista = programas.leer(2026, 12)
    assert vista.contexto.historial[1, date(2026, 11, 3)] == 2
    assert (1, date(2026, 11, 3), Puesto.VIDEO) in vista.contexto.puestos_historicos
    assert (2, date(2026, 11, 3)) not in vista.contexto.historial

    semanas = list(vista.borrador.semanas)
    semanas[1] = replace(semanas[1], martes=False)
    semanas[2] = replace(semanas[2], martes=False, domingo=False)
    semanas[3] = replace(semanas[3], desactivados=frozenset({Puesto.VIDEO}))
    borrador = replace(vista.borrador, semanas=tuple(semanas), grupo_inicial=4)
    assert generar(programas, vista, borrador).plan is not None
    vista = programas.leer(2026, 12)
    assert len(vista.borrador.plan) == len(vista.contexto.plazas()) - 1
    vacante = semanas[0].inicio, Puesto.AUDIO, 1
    with pytest.raises(ValueError, match="inválida"):
        programas.guardar(vista, replace(vista.borrador, plan={**vista.borrador.plan, vacante: 1}))
    assert programas.leer(2026, 12).borrador == vista.borrador
    audio = semanas[1].inicio, Puesto.AUDIO, 1
    nuevo = 11 if vista.borrador.plan[audio] == 1 else 1
    programas.guardar(vista, replace(vista.borrador, plan={**vista.borrador.plan, audio: nuevo}))
    vista = programas.leer(2026, 12)
    with pytest.raises(ValueError, match="Confirma"):
        programas.publicar(vista)
    assert programas.publicar(vista, acepta_vacantes=True) == 1
    assert programas.publicar(programas.leer(2026, 12), acepta_vacantes=True) == 1
    activa = vista.contexto.personas[nuevo]
    programas.guardar_persona(nuevo, "Nombre actualizado", "", activa.puestos, True)
    vista = programas.leer(2026, 12)
    programas.guardar(
        vista,
        replace(vista.borrador, plan={**vista.borrador.plan, audio: 1 if nuevo == 11 else 11}),
    )

    with closing(BaseDatos(programas.base.ruta)) as reabierta:
        reabierta.preparar()
        reabiertos = Programas(reabierta)
        vigente = reabiertos.leer(2026, 12)
        assert vigente.version == 1 and not vigente.publicado_al_dia
        assert vigente.borrador.plan[audio] != nuevo
        archivo = exportar(reabiertos, 2026, 12)
        assert archivo.parent == reabierta.ruta.parent / "exportaciones"
        with closing(load_workbook(archivo)) as libro:
            assert libro.sheetnames == ["Programa General", "Audio y Video"]
            av = libro["Audio y Video"]
            assert av["B3"].value == "—"
            assert av["C3"].value == activa.nombre
            assert av["D3"].value == "Cancelada"
            assert av["E4"].value == "No requerido"
        enero = reabiertos.leer(2027, 1)
        assert enero.borrador.grupo_inicial == 4
        assert enero.contexto.historial[nuevo, semanas[1].inicio] == 1


@pytest.mark.parametrize("mes", [11, 12])
def test_excel_ordinario_conserva_xml_de_las_dos_hojas(
    mes: int,
    programas: Programas,
    tmp_path: Path,
) -> None:
    mes_v1 = {}
    vista = programas.leer(2026, mes)
    padron = {}
    for puesto, cupos in CUPOS_HABITUALES.items():
        for cupo in range(1, cupos + 1):
            nombre = f"Persona {puesto.value} {cupo}"
            ident = programas.guardar_persona(None, nombre, "", frozenset({puesto}), True)
            padron[puesto, cupo] = ident, nombre
    vista = programas.leer(2026, mes)
    plan = {}
    for indice, semana in enumerate(vista.borrador.semanas, 1):
        mes_v1[indice] = {}
        for fecha, puesto, cupo in semana.plazas():
            ident, nombre = padron[puesto, cupo]
            plan[fecha, puesto, cupo] = ident
            mes_v1[indice].setdefault(puesto.value, []).append(nombre)
    programas.guardar(vista, replace(vista.borrador, plan=plan, grupo_inicial=4))
    programas.publicar(programas.leer(2026, mes))
    referencia = tmp_path / "V1.xlsx"
    exportar_programa_excel(mes_v1, 2026, mes, 4, str(referencia))
    with ZipFile(referencia) as v1, ZipFile(exportar(programas, 2026, mes)) as v2:
        for xml in ("workbook.xml", "styles.xml", "worksheets/sheet1.xml", "worksheets/sheet2.xml"):
            assert v1.read(f"xl/{xml}") == v2.read(f"xl/{xml}")


def test_importacion_ambigua_y_reintento_tras_error(programas: Programas, tmp_path: Path):
    origen = tmp_path / "V1"
    origen.mkdir()
    _json(
        origen,
        "hermanos.json",
        [
            {"id": 1, "nombre": "Persona A", "roles": ["audio"]},
            {"id": 2, "nombre": "Persona A", "roles": ["video"]},
        ],
    )
    _json(origen, "asignaciones_2026_11.json", {"1": {"audio": ["Persona A"], "video": [2]}})
    previa = previsualizar(origen, 2026, 12)
    assert len(previa.pendientes) == 1
    with programas.base.motor.begin() as conexion:
        conexion.exec_driver_sql(
            "CREATE TRIGGER fallo BEFORE INSERT ON lotes_importados "
            "BEGIN SELECT RAISE(ABORT, 'interrupción'); END"
        )
    with pytest.raises(IntegrityError, match="interrupción"):
        aplicar(programas.base, previa)
    assert not programas.leer(2026, 12).contexto.personas
    assert not programas.leer(2026, 11).historico
    with programas.base.motor.begin() as conexion:
        conexion.exec_driver_sql("DROP TRIGGER fallo")
    assert aplicar(programas.base, previa)["asignaciones_historicas"] == 1
    assert aplicar(programas.base, previa)["repetido"]
