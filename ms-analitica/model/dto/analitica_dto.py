# ms-analitica/model/dto/analitica_dto.py
# Esquemas de openapi.yaml: Resumen, MetricaVentas, Recomendaciones, Interaccion…
from datetime import datetime
from enum import Enum
from uuid import UUID
from pydantic import BaseModel, Field


class AgruparPor(str, Enum):
    DIA = "DIA"
    SEMANA = "SEMANA"
    TIPO_PASE = "TIPO_PASE"


class ResumenDTO(BaseModel):
    entradas_vendidas: int
    ingresos_entradas: float
    ingresos_alquileres: float
    ingresos_tienda: float
    usuarios_registrados: int
    ocupacion_espacios: float = Field(ge=0, le=1)
    asistentes_hoy: int
    actualizado_en: datetime


class MetricaVentasDTO(BaseModel):
    evento_id: str | None = None
    periodo: str
    tipo_pase: str | None = None
    entradas: int
    ingresos: float
    cancelaciones: int


class MetricaOcupacionDTO(BaseModel):
    evento_id: str
    tipo_espacio: str
    total: int
    alquilados: int
    ingresos_alquiler: float


class FranjaAfluenciaDTO(BaseModel):
    inicio: datetime
    fin: datetime
    artista: str
    asistentes_estimados: int
    porcentaje_aforo: float | None = None


class PrevisionAfluenciaDTO(BaseModel):
    espacio_id: str
    escenario: str
    franjas: list[FranjaAfluenciaDTO]


class VentaTiendaDTO(BaseModel):
    producto_id: str | None
    talla: str | None
    unidades: int
    ingresos: float


class StockBajoDTO(BaseModel):
    producto_id: str
    talla: str
    stock: int


class EstadisticasTiendaDTO(BaseModel):
    ventas: list[VentaTiendaDTO]
    stock_bajo: list[StockBajoDTO]


class PopularidadArtistaDTO(BaseModel):
    artista_id: str
    artista: str | None = None
    favoritos: int
    visitas: int
    tendencia_7d: float


class EventoRecomendadoDTO(BaseModel):
    evento_id: str
    titulo: str | None = None
    puntuacion: float = Field(ge=0, le=1)
    motivo: str


class ArtistaRecomendadoDTO(BaseModel):
    artista_id: str
    artista: str | None = None
    puntuacion: float
    motivo: str


class PaseMiEscaletaDTO(BaseModel):
    pase_id: str
    artista: str
    escenario: str
    inicio: datetime
    fin: datetime
    solapa_con: list[str] = []


class RecomendacionesClienteDTO(BaseModel):
    generadas_en: datetime
    eventos: list[EventoRecomendadoDTO]
    artistas: list[ArtistaRecomendadoDTO]
    mi_escaleta: list[PaseMiEscaletaDTO]


class RecomendacionesPopularesDTO(BaseModel):
    eventos: list[EventoRecomendadoDTO]
    artistas: list[PopularidadArtistaDTO]


class EspacioRecomendadoDTO(BaseModel):
    espacio_id: str
    evento_id: str
    tipo: str
    precio_alquiler: float | None = None
    afluencia_estimada: int
    puntuacion: float
    motivo: str


class AccionInteraccion(str, Enum):
    VER_EVENTO = "VER_EVENTO"
    VER_ARTISTA = "VER_ARTISTA"
    VER_PRODUCTO = "VER_PRODUCTO"
    BUSCAR = "BUSCAR"


class InteraccionDTO(BaseModel):
    accion: AccionInteraccion
    objetivo_id: str = Field(min_length=1)
    fecha: datetime


class LoteInteraccionesDTO(BaseModel):
    sesion_id: UUID | None = None
    interacciones: list[InteraccionDTO] = Field(min_length=1, max_length=100)
