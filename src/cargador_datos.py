from pathlib import Path
from typing import Dict, List, Set

from configuracion import BASE_DIR
from repositorio import DatosInvalidosError, Repositorio

# Mantenemos las firmas originales para retrocompatibilidad
# con los módulos que aún no han sido refactorizados.

def cargar_roles_validos(ruta_roles: str | Path) -> Set[str]:
    repo = Repositorio(data_dir=Path(ruta_roles).parent)
    return repo.cargar_roles_validos()

def cargar_hermanos(ruta_archivo: str | Path) -> List[Dict]:
    """Retorna la lista de diccionarios por compatibilidad temporal
    (hasta refactorizar motor_asignacion.py en la Fase 3).
    """
    repo = Repositorio(data_dir=Path(ruta_archivo).parent)
    hermanos_pydantic = repo.cargar_hermanos()

    # Exportamos a dict para que el motor viejo no se rompa
    return [h.model_dump() for h in hermanos_pydantic]

if __name__ == "__main__":
    try:
        datos = cargar_hermanos(BASE_DIR / "data/hermanos.json")
        print(f"Total cargados (validación Pydantic exitosa): {len(datos)}")
    except DatosInvalidosError as e:
        print(f"Error de validación: {e}")
