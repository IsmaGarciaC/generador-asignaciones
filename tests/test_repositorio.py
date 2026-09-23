import json
from pathlib import Path

import pytest

from modelos import EstadoMes
from repositorio import DatosInvalidosError, Repositorio


@pytest.fixture
def tmp_repo(tmp_path: Path):
    """Crea una instancia de Repositorio en un directorio temporal aislado."""
    repo = Repositorio(data_dir=tmp_path)

    # Crear roles.txt válido
    roles_contenido = (
        "audio\nvideo\nacomodador\nmicrofonos\nplataforma\nlector_martes\n"
        "lector_domingo\npresidente\n"
    )
    repo.ruta_roles.write_text(roles_contenido, encoding="utf-8")
    return repo


def test_cargar_roles_validos(tmp_repo: Repositorio):
    roles = tmp_repo.cargar_roles_validos()
    assert "audio" in roles
    assert "video" in roles
    assert "presidente" in roles


def test_cargar_roles_archivo_inexistente(tmp_path: Path):
    repo = Repositorio(data_dir=tmp_path / "vacio")
    with pytest.raises(DatosInvalidosError, match="No se encontró el catálogo de roles"):
        repo.cargar_roles_validos()


def test_cargar_hermanos_valido(tmp_repo: Repositorio):
    datos = [
        {"id": 1, "nombre": "Juan Pérez", "telefono": "+123", "roles": ["audio", "video"]},
        {"id": 2, "nombre": " Carlos Gómez ", "telefono": "+456", "roles": ["acomodador"]},
    ]
    tmp_repo.ruta_hermanos.write_text(json.dumps(datos), encoding="utf-8")

    hermanos = tmp_repo.cargar_hermanos()
    assert len(hermanos) == 2
    assert hermanos[0].nombre == "Juan Pérez"
    assert hermanos[1].nombre == "Carlos Gómez"  # El strip automático funciona


def test_cargar_hermanos_id_duplicado(tmp_repo: Repositorio):
    datos = [
        {"id": 1, "nombre": "Persona Uno", "telefono": "+1", "roles": ["audio"]},
        {"id": 1, "nombre": "Persona Dos", "telefono": "+2", "roles": ["video"]},
    ]
    tmp_repo.ruta_hermanos.write_text(json.dumps(datos), encoding="utf-8")

    with pytest.raises(DatosInvalidosError, match="el id 1 está duplicado"):
        tmp_repo.cargar_hermanos()


def test_cargar_hermanos_nombre_duplicado(tmp_repo: Repositorio):
    datos = [
        {"id": 1, "nombre": "Persona Misma", "telefono": "+1", "roles": ["audio"]},
        {"id": 2, "nombre": "Persona Misma", "telefono": "+2", "roles": ["video"]},
    ]
    tmp_repo.ruta_hermanos.write_text(json.dumps(datos), encoding="utf-8")

    with pytest.raises(DatosInvalidosError, match="el nombre 'Persona Misma' está duplicado"):
        tmp_repo.cargar_hermanos()


def test_cargar_hermanos_rol_desconocido(tmp_repo: Repositorio):
    datos = [
        {"id": 1, "nombre": "Persona", "telefono": "+1", "roles": ["rol_inexistente"]},
    ]
    tmp_repo.ruta_hermanos.write_text(json.dumps(datos), encoding="utf-8")

    with pytest.raises(DatosInvalidosError, match="rol desconocido 'rol_inexistente'"):
        tmp_repo.cargar_hermanos()


def test_guardar_y_leer_estado(tmp_repo: Repositorio):
    estado = EstadoMes(
        ultimo_anio=2026,
        ultimo_mes=9,
        ultimo_grupo_limpieza=2,
        siguiente_grupo_limpieza=3,
    )
    tmp_repo.guardar_estado(estado)
    leido = tmp_repo.leer_estado()

    assert leido is not None
    assert leido.ultimo_anio == 2026
    assert leido.ultimo_mes == 9
    assert leido.siguiente_grupo_limpieza == 3


def test_guardar_y_leer_ausencias_mes(tmp_repo: Repositorio):
    ausencias_oct = {"Juan Pérez": [1, 2], "Carlos Gómez": [3]}
    tmp_repo.guardar_ausencias_mes(anio=2026, mes=10, ausencias_mes=ausencias_oct)

    leidas = tmp_repo.leer_ausencias_mes(anio=2026, mes=10)
    assert leidas == ausencias_oct

    # Otro mes debe retornar diccionario vacío
    assert tmp_repo.leer_ausencias_mes(anio=2026, mes=11) == {}
