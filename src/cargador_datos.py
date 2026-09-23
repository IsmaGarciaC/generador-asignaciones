import json
from pathlib import Path


class DatosInvalidosError(ValueError):
    """El JSON de hermanos o el catálogo de roles no se puede usar."""


def cargar_roles_validos(ruta_roles: str | Path) -> set[str]:
    archivo = Path(ruta_roles)
    if not archivo.exists():
        raise DatosInvalidosError(f"No se encontró el catálogo de roles: {archivo}")

    roles: set[str] = set()
    for linea in archivo.read_text(encoding="utf-8").splitlines():
        token = linea.strip()
        if token and all(c.islower() or c == "_" for c in token):
            roles.add(token)

    if not roles:
        raise DatosInvalidosError(f"El catálogo de roles está vacío: {archivo}")
    return roles


def cargar_hermanos(ruta_archivo: str | Path) -> list[dict]:
    ruta = Path(ruta_archivo)
    if not ruta.exists():
        raise DatosInvalidosError(
            f"No se encontró {ruta.name}. Copia data/hermanos.example.json a data/hermanos.json."
        )

    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise DatosInvalidosError(f"hermanos.json no es un JSON válido: {e.msg}") from e
    except OSError as e:
        raise DatosInvalidosError(f"No se pudo leer {ruta.name}: {e}") from e

    if not isinstance(datos, list):
        raise DatosInvalidosError("hermanos.json debe ser una lista de personas.")

    roles_validos = cargar_roles_validos(ruta.parent / "roles.txt")
    campos_requeridos = ("id", "nombre", "telefono", "roles")
    ids_vistos: set = set()
    nombres_vistos: set[str] = set()
    hermanos: list[dict] = []

    for indice, hermano in enumerate(datos, start=1):
        prefijo = f"Persona #{indice}"
        if not isinstance(hermano, dict):
            raise DatosInvalidosError(f"{prefijo}: debe ser un objeto JSON.")

        for campo in campos_requeridos:
            if campo not in hermano:
                raise DatosInvalidosError(f"{prefijo}: falta el campo '{campo}'.")

        identificador = hermano["id"]
        if identificador in ids_vistos:
            raise DatosInvalidosError(f"{prefijo}: el id {identificador} está duplicado.")
        ids_vistos.add(identificador)

        nombre = hermano["nombre"]
        if not isinstance(nombre, str) or not nombre.strip():
            raise DatosInvalidosError(f"{prefijo}: el nombre está vacío.")
        nombre = nombre.strip()
        if nombre in nombres_vistos:
            raise DatosInvalidosError(f"{prefijo}: el nombre '{nombre}' está duplicado.")
        nombres_vistos.add(nombre)

        lista_roles = hermano["roles"]
        if not isinstance(lista_roles, list) or not lista_roles:
            raise DatosInvalidosError(f"{nombre}: la lista de roles está vacía.")

        for rol in lista_roles:
            if rol not in roles_validos:
                raise DatosInvalidosError(
                    f"{nombre}: rol desconocido '{rol}'. Válidos: {', '.join(sorted(roles_validos))}."
                )

        hermano_normalizado = dict(hermano)
        hermano_normalizado["nombre"] = nombre
        hermanos.append(hermano_normalizado)

    if not hermanos:
        raise DatosInvalidosError("hermanos.json no contiene ninguna persona.")

    return hermanos


if __name__ == "__main__":
    datos = cargar_hermanos("data/hermanos.json")
    print(f"Total cargados: {len(datos)}")
