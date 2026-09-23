from typing import Dict, List, Set

from pydantic import BaseModel, Field, field_validator


class Hermano(BaseModel):
    id: int = Field(..., ge=1)
    nombre: str = Field(..., min_length=1)
    telefono: str = ""
    roles: Set[str] = Field(..., min_length=1)

    @field_validator("nombre", mode="before")
    @classmethod
    def strip_nombre(cls, v: str) -> str:
        return v.strip() if isinstance(v, str) else v


class EstadoMes(BaseModel):
    ultimo_anio: int = Field(..., ge=2000)
    ultimo_mes: int = Field(..., ge=1, le=12)
    ultimo_grupo_limpieza: int = Field(..., ge=0)
    siguiente_grupo_limpieza: int = Field(..., ge=0)


class AusenciasMes(BaseModel):
    # Clave: nombre del hermano, Valor: lista de semanas en las que está ausente
    ausencias: Dict[str, List[int]] = Field(default_factory=dict)


class ReglasAsignacion(BaseModel):
    """Reglas y penalizaciones configurables para el motor heurístico."""

    penalizacion_rol_repetido_mes: int = Field(16, ge=0)
    penalizacion_semana_anterior: int = Field(3, ge=0)
    penalizacion_mismo_rol_semana_anterior: int = Field(10, ge=0)
    penalizacion_fatiga: int = Field(12, ge=0)
    penalizacion_pareja_repetida: int = Field(14, ge=0)
    penalizacion_doblete_emergencia: int = Field(35, ge=0)
    limite_semanas_fatiga: int = Field(2, ge=1)
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
