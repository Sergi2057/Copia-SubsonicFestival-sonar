# ms-espacios/model/dto/espacio_dto.py
# Esquemas TipoEspacio, Espacio, EspacioEntrada, Alquiler y AlquilerEntrada de openapi.yaml
from datetime import datetime
from enum import Enum
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator


class CodigoTipoEspacio(str, Enum):
    ESCENARIO = "ESCENARIO"
    FOOD_BEVERAGE = "FOOD_BEVERAGE"
    MERCHANDISING = "MERCHANDISING"
    ACAMPADA = "ACAMPADA"
    VIP = "VIP"
    SERVICIOS = "SERVICIOS"


class EstadoAlquiler(str, Enum):
    PENDIENTE = "PENDIENTE"
    APROBADO = "APROBADO"
    RECHAZADO = "RECHAZADO"
    CANCELADO = "CANCELADO"
    ACTIVO = "ACTIVO"
    FINALIZADO = "FINALIZADO"


class TipoEspacioDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    codigo: CodigoTipoEspacio
    nombre: str
    alquilable: bool


# ── Espacios ────────────────────────────────────────────────

class EspacioEntradaDTO(BaseModel):
    evento_id: str
    tipo: CodigoTipoEspacio
    nombre: str = Field(min_length=1, max_length=200)
    zona: str | None = None
    tamano: str | None = None
    dimensiones: str | None = None
    aforo: int | None = Field(default=None, ge=0)
    precio_alquiler: float | None = Field(default=None, ge=0)
    servicios: list[str] = []
    descripcion: str | None = None
    disponible: bool


class EspacioDTO(EspacioEntradaDTO):
    model_config = ConfigDict(from_attributes=True)

    id: str


# ── Alquileres ──────────────────────────────────────────────

class AlquilerEntradaDTO(BaseModel):
    fecha_inicio: datetime
    fecha_fin: datetime
    comentarios: str | None = None

    @model_validator(mode="after")
    def comprobar_fechas(self):
        if self.fecha_inicio.tzinfo is None or self.fecha_fin.tzinfo is None:
            raise ValueError("Las fechas deben incluir zona horaria (p. ej. 2026-07-16T08:00:00+02:00)")
        if self.fecha_fin <= self.fecha_inicio:
            raise ValueError("fecha_fin debe ser posterior a fecha_inicio")
        return self


class CambioEstadoAlquilerDTO(BaseModel):
    estado: EstadoAlquiler
    comentarios: str | None = None


class AlquilerDTO(BaseModel):
    id: UUID
    espacio_id: str
    evento_id: str
    proveedor_id: str
    proveedor_nombre: str | None = None
    fecha_inicio: datetime
    fecha_fin: datetime
    importe: float
    estado: EstadoAlquiler
    comentarios: str | None = None
    creado_en: datetime
