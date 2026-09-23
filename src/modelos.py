from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Set

class Hermano(BaseModel):
    id: int
    nombre: str = Field(..., min_length=1)
    telefono: str
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
