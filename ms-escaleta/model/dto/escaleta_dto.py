# ms-escaleta/model/dto/escaleta_dto.py
# Esquemas de openapi.yaml: Artista, Slot, Pase, Escaleta, Publicacion, Video…
from datetime import date, datetime
from enum import Enum
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator


class TipoSlot(str, Enum):
    ACTUACION = "ACTUACION"
    CAMBIO_ESCENARIO = "CAMBIO_ESCENARIO"
    DESCANSO = "DESCANSO"


class FormatoPase(str, Enum):
    DJ_SET = "DJ_SET"
    LIVE = "LIVE"
    B2B = "B2B"


class EstadoPase(str, Enum):
    PROGRAMADO = "PROGRAMADO"
    CONFIRMADO = "CONFIRMADO"
    EN_CURSO = "EN_CURSO"
    FINALIZADO = "FINALIZADO"
    CANCELADO = "CANCELADO"


def _con_zona(*fechas: datetime | None):
    for fecha in fechas:
        if fecha is not None and fecha.tzinfo is None:
            raise ValueError("Las fechas deben incluir zona horaria (p. ej. 2026-07-18T22:00:00+02:00)")


# ── Artistas ────────────────────────────────────────────────

class ArtistaEntradaDTO(BaseModel):
    nombre: str = Field(min_length=1, max_length=255)
    generos: list[str] = Field(min_length=1)
    pais: str | None = None
    biografia: str | None = None
    imagen_url: str | None = None
    youtube_channel_id: str | None = None
    redes: dict[str, str] = {}


class ArtistaDTO(ArtistaEntradaDTO):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    generos: list[str] = []


class PaseResumenDTO(BaseModel):
    pase_id: UUID
    artista_id: UUID
    artista: str
    escenario: str
    inicio: datetime
    fin: datetime
    estado: EstadoPase


class ArtistaDetalleDTO(ArtistaDTO):
    pases: list[PaseResumenDTO] = []


class VideoDTO(BaseModel):
    titulo: str
    url: str
    miniatura_url: str | None = None
    tipo: str  # VIDEO o PLAYLIST


# ── Slots y pases ───────────────────────────────────────────

class SlotEntradaDTO(BaseModel):
    espacio_id: str
    inicio: datetime
    fin: datetime
    tipo: TipoSlot

    @model_validator(mode="after")
    def comprobar_horas(self):
        _con_zona(self.inicio, self.fin)
        if self.fin <= self.inicio:
            raise ValueError("fin debe ser posterior a inicio")
        return self


class PaseDTO(BaseModel):
    id: UUID
    slot_id: UUID
    artista_id: UUID
    artista_nombre: str | None = None
    formato: FormatoPase
    estado: EstadoPase
    notas_tecnicas: str | None = None
    version: int


class SlotDTO(BaseModel):
    id: UUID
    evento_id: str
    espacio_id: str
    inicio: datetime
    fin: datetime
    tipo: TipoSlot
    pase: PaseDTO | None = None


class PaseEntradaDTO(BaseModel):
    artista_id: UUID
    formato: FormatoPase
    notas_tecnicas: str | None = None


class PaseCambioDTO(BaseModel):
    version: int = Field(ge=1, description="Versión actual del pase (control de concurrencia)")
    estado: EstadoPase | None = None
    inicio: datetime | None = None
    fin: datetime | None = None
    espacio_id: str | None = None
    formato: FormatoPase | None = None
    motivo: str | None = None

    @model_validator(mode="after")
    def comprobar_horas(self):
        _con_zona(self.inicio, self.fin)
        return self


# ── Escaleta publicada ──────────────────────────────────────

class EscaletaEscenarioDTO(BaseModel):
    espacio_id: str
    nombre: str
    pases: list[PaseResumenDTO]


class DiaEscaletaDTO(BaseModel):
    fecha: date
    escenarios: list[EscaletaEscenarioDTO]


class EscaletaDTO(BaseModel):
    evento_id: str
    version: int
    publicada_en: datetime
    dias: list[DiaEscaletaDTO]


class PublicacionDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    evento_id: str
    version: int
    publicada_en: datetime
    publicada_por: str
