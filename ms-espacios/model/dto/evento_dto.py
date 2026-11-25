# ms-espacios/model/dto/evento_dto.py
# Esquemas Evento, EventoDetalle, EventoEntrada, Recinto, Tarifa y ReservaAforo de openapi.yaml
from datetime import date, datetime
from enum import Enum
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator


class EstadoEvento(str, Enum):
    BORRADOR = "BORRADOR"
    PUBLICADO = "PUBLICADO"
    FINALIZADO = "FINALIZADO"
    CANCELADO = "CANCELADO"


class TipoPase(str, Enum):
    DAY = "DAY"
    WEEKEND = "WEEKEND"
    VIP = "VIP"


# ── Recintos ────────────────────────────────────────────────

class RecintoEntradaDTO(BaseModel):
    nombre: str = Field(min_length=1, max_length=255)
    direccion: str | None = None
    ciudad: str = Field(min_length=1)
    pais: str = Field(min_length=1)
    latitud: float | None = Field(default=None, ge=-90, le=90)
    longitud: float | None = Field(default=None, ge=-180, le=180)
    aforo_maximo: int = Field(ge=0)


class RecintoDTO(RecintoEntradaDTO):
    model_config = ConfigDict(from_attributes=True)

    id: UUID


# ── Eventos ─────────────────────────────────────────────────

class EventoEntradaDTO(BaseModel):
    id: str = Field(pattern=r"^evento-[a-z0-9-]+$", max_length=100)
    titulo: str = Field(min_length=1, max_length=200)
    pais: str = Field(min_length=1)
    recinto_id: UUID
    fecha_inicio: date
    fecha_fin: date
    descripcion: str | None = None
    imagen_url: str | None = None
    tags: list[str] = []
    servicios_generales: list[str] = []

    @model_validator(mode="after")
    def comprobar_fechas(self):
        if self.fecha_fin < self.fecha_inicio:
            raise ValueError("fecha_fin no puede ser anterior a fecha_inicio")
        return self


class EventoDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    titulo: str
    pais: str | None = None
    recinto_id: UUID
    fecha_inicio: date
    fecha_fin: date
    descripcion: str | None = None
    imagen_url: str | None = None
    tags: list[str] = []
    servicios_generales: list[str] = []
    estado: EstadoEvento


class EventoDetalleDTO(EventoDTO):
    recinto: RecintoDTO | None = None


class CambioEstadoEventoDTO(BaseModel):
    estado: EstadoEvento
    motivo: str | None = None

    @model_validator(mode="after")
    def motivo_al_cancelar(self):
        if self.estado == EstadoEvento.CANCELADO and not self.motivo:
            raise ValueError("motivo es obligatorio al cancelar")
        return self


# ── Tarifas y aforo ─────────────────────────────────────────

class TarifaEntradaDTO(BaseModel):
    tipo_pase: TipoPase
    precio: float = Field(ge=0)
    cupo_total: int = Field(ge=0)


class TarifaDTO(BaseModel):
    id: UUID
    evento_id: str
    tipo_pase: TipoPase
    precio: float
    cupo_total: int
    disponibles: int  # cupo_total - vendidas - reservas pendientes


class ReservaAforoEntradaDTO(BaseModel):
    tipo_pase: TipoPase
    usuario_id: str = Field(min_length=1)


class ReservaAforoDTO(BaseModel):
    reserva_id: UUID
    evento_id: str
    tipo_pase: TipoPase
    precio: float
    expira_en: datetime
    # Datos del evento que ms-usuarios copia en la entrada (así no necesita otra llamada síncrona)
    evento_titulo: str
    fecha_inicio: date
    fecha_fin: date
