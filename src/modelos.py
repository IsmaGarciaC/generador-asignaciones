from typing import Dict, List, Set

from pydantic import BaseModel, Field, field_validator


class Hermano(BaseModel):
    id: int
    nombre: str = Field(..., min_length=1)
    telefono: str = ""
    roles: List[str] = Field(..., min_length=1)

    @field_validator("nombre")
    @classmethod
    def strip_nombre(cls, v: str) -> str:
        return v.strip()

class EstadoMes(BaseModel):
    ultimo_anio: int
    ultimo_mes: int
    ultimo_grupo_limpieza: int
    siguiente_grupo_limpieza: int

class AusenciasMes(BaseModel):
    # Clave: nombre del hermano, Valor: lista de semanas en las que está ausente
    ausencias: Dict[str, List[int]] = Field(default_factory=dict)

class ReglasAsignacion(BaseModel):
    """Reglas y penalizaciones configurables para el motor heurístico."""
    penalizacion_rol_repetido_mes: int = 16
    penalizacion_semana_anterior: int = 3
    penalizacion_mismo_rol_semana_anterior: int = 10
    penalizacion_fatiga: int = 12
    penalizacion_pareja_repetida: int = 14
    penalizacion_doblete_emergencia: int = 35
    limite_semanas_fatiga: int = 2
    puestos_requeridos: Dict[str, int] = Field(
        default_factory=lambda: {
            "presidente": 1,
            "lector_domingo": 1,
            "audio": 1,
            "video": 1,
            "plataforma": 1,
            "lector_martes": 1,
            "microfonos": 2,
            "acomodador": 2,
        }
    )
    puestos_emergencia_compatibles: Set[str] = Field(
        default_factory=lambda: {"microfonos", "audio", "video"}
    )
