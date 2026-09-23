import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Set

from pydantic import ValidationError

from configuracion import BASE_DIR, logger
from modelos import EstadoMes, Hermano


class DatosInvalidosError(ValueError):
    """Excepción lanzada cuando hay un error semántico o de formato en los datos."""

    pass


class Repositorio:
    def __init__(self, data_dir: Path = None):
        self.data_dir = data_dir or (BASE_DIR / "data")
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.ruta_hermanos = self.data_dir / "hermanos.json"
        self.ruta_roles = self.data_dir / "roles.txt"
        self.ruta_estado = self.data_dir / "estado.json"
        self.ruta_ausencias = self.data_dir / "ausencias.json"

    def cargar_roles_validos(self) -> Set[str]:
        if not self.ruta_roles.exists():
            logger.error("No se encontró el catálogo de roles: %s", self.ruta_roles)
            raise DatosInvalidosError(
                f"No se encontró el catálogo de roles: {self.ruta_roles.name}"
            )

        roles = set()
        for linea in self.ruta_roles.read_text(encoding="utf-8").splitlines():
            token = linea.strip()
            if not token:
                continue
            if all(c.islower() or c == "_" for c in token):
                roles.add(token)
            else:
                raise DatosInvalidosError(f"Formato de rol inválido en roles.txt: '{token}'. Solo se permiten minúsculas y guiones bajos.")

        if not roles:
            raise DatosInvalidosError("El catálogo de roles está vacío.")
        return roles

    def cargar_hermanos(self) -> List[Hermano]:
        if not self.ruta_hermanos.exists():
            raise DatosInvalidosError(
                f"No se encontró {self.ruta_hermanos.name}. "
                "Copia hermanos.example.json a hermanos.json."
            )

        try:
            datos_raw = json.loads(self.ruta_hermanos.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            logger.error("Error decodificando hermanos.json: %s", e)
            raise DatosInvalidosError(f"hermanos.json no es un JSON válido: {e.msg}") from e

        if not isinstance(datos_raw, list):
            raise DatosInvalidosError("hermanos.json debe ser una lista de personas.")

        roles_validos = self.cargar_roles_validos()

        hermanos = []
        ids_vistos = set()
        nombres_vistos = set()

        for idx, item in enumerate(datos_raw):
            try:
                if not isinstance(item, dict):
                    raise DatosInvalidosError(f"Persona #{idx + 1}: el elemento no es un objeto JSON.")
                hermano = Hermano(**item)
            except ValidationError as e:
                logger.error("Error de validación Pydantic en persona #%d: %s", idx + 1, e)
                raise DatosInvalidosError(
                    f"Persona #{idx + 1}: Error de formato. Revisa los campos requeridos."
                ) from e

            if hermano.id in ids_vistos:
                raise DatosInvalidosError(f"Persona #{idx + 1}: el id {hermano.id} está duplicado.")
            ids_vistos.add(hermano.id)

            if hermano.nombre in nombres_vistos:
                raise DatosInvalidosError(
                    f"Persona #{idx + 1}: el nombre '{hermano.nombre}' está duplicado."
                )
            nombres_vistos.add(hermano.nombre)

            for rol in hermano.roles:
                if rol not in roles_validos:
                    lista_roles = ", ".join(sorted(roles_validos))
                    raise DatosInvalidosError(
                        f"{hermano.nombre}: rol desconocido '{rol}'. Válidos: {lista_roles}."
                    )

            hermanos.append(hermano)

        if not hermanos:
            raise DatosInvalidosError("hermanos.json no contiene ninguna persona.")

        return hermanos

    def leer_estado(self) -> Optional[EstadoMes]:
        if not self.ruta_estado.exists():
            return None
        try:
            datos = json.loads(self.ruta_estado.read_text(encoding="utf-8"))
            return EstadoMes(**datos)
        except (OSError, json.JSONDecodeError, ValidationError) as e:
            logger.warning("No se pudo leer o validar el estado anterior: %s", e)
            return None

    def guardar_estado(self, estado: EstadoMes):
        try:
            ruta_tmp = self.ruta_estado.with_suffix('.tmp')
            ruta_tmp.write_text(estado.model_dump_json(indent=4), encoding="utf-8")
            os.replace(ruta_tmp, self.ruta_estado)
        except OSError as e:
            logger.error("Error guardando estado: %s", e)

    def leer_todas_ausencias(self) -> Dict[str, Dict[str, List[int]]]:
        if not self.ruta_ausencias.exists():
            return {}
        try:
            datos = json.loads(self.ruta_ausencias.read_text(encoding="utf-8"))
            return datos if isinstance(datos, dict) else {}
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("No se pudo leer las ausencias: %s", e)
            return {}

    def guardar_todas_ausencias(self, ausencias: Dict[str, Dict[str, List[int]]]):
        try:
            contenido = json.dumps(ausencias, indent=4, ensure_ascii=False)
            ruta_tmp = self.ruta_ausencias.with_suffix('.tmp')
            ruta_tmp.write_text(contenido, encoding="utf-8")
            os.replace(ruta_tmp, self.ruta_ausencias)
        except OSError as e:
            logger.error("Error guardando ausencias: %s", e)

    def leer_ausencias_mes(self, anio: int, mes: int) -> Dict[str, List[int]]:
        clave = f"{anio}-{mes:02d}"
        todas = self.leer_todas_ausencias()
        return todas.get(clave, {})

    def guardar_ausencias_mes(self, anio: int, mes: int, ausencias_mes: Dict[str, List[int]]):
        clave = f"{anio}-{mes:02d}"
        todas = self.leer_todas_ausencias()
        if ausencias_mes:
            todas[clave] = ausencias_mes
        elif clave in todas:
            del todas[clave]
        self.guardar_todas_ausencias(todas)
