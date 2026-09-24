from typing import Dict, List, Set

from pydantic import BaseModel, Field, field_validator


class Hermano(BaseModel):
    id: int = Field(..., ge=1)
    nombre: str = Field(..., min_length=1)
    telefono: str = Field(default="", pattern=r"^\+?[\d\s\-()]*$")
    roles: Set[str] = Field(..., min_length=1)

    @field_validator("nombre", mode="before")
    @classmethod
    def strip_nombre(cls, v: str) -> str:
        if isinstance(v, str):
            v = v.strip()
            if v.startswith(("=", "+", "-", "@")):
                v = f"'{v}"
            return v
        return v


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
    num_grupos_limpieza: int = Field(4, ge=1)
    estructura_programa: List[dict] = Field(
        default_factory=lambda: [
            {"es_seccion": True, "label": "AUDITORIO Y PLATAFORMA", "key": None, "alto": 24},
            {"es_seccion": False, "label": "Acomodadores", "key": "acomodador", "alto": 45},
            {"es_seccion": False, "label": "Plataforma", "key": "plataforma", "alto": 30},
            {"es_seccion": False, "label": "Micrófonos", "key": "microfonos", "alto": 45},
            {"es_seccion": False, "label": "Limpieza del Salón", "key": "limpieza", "alto": 30},
            {"es_seccion": False, "label": "Hospitalidad", "key": "hospitalidad", "alto": 30},
            {"es_seccion": True, "label": "PRESIDENCIA Y LECTURAS", "key": None, "alto": 24},
            {
                "es_seccion": False,
                "label": "Lector Estudio Bíblico",
                "key": "lector_martes",
                "alto": 30,
            },
            {"es_seccion": False, "label": "Presidente", "key": "presidente", "alto": 30},
            {
                "es_seccion": False,
                "label": "Lector de La Atalaya",
                "key": "lector_domingo",
                "alto": 30,
            },
        ]
    )
