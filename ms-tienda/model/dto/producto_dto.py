# ms-tienda/model/dto/producto_dto.py
# Esquemas Producto, ProductoEntrada, Variante y Talla de openapi.yaml
from enum import Enum
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator


class Talla(str, Enum):
    XS = "XS"
    S = "S"
    M = "M"
    L = "L"
    XL = "XL"
    XXL = "XXL"
    UNICA = "UNICA"


class VarianteDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    talla: Talla
    stock: int = Field(ge=0)
    activa: bool = True


class VarianteEntradaDTO(BaseModel):
    talla: Talla
    stock: int = Field(ge=0)


class VarianteCambioDTO(BaseModel):
    """PATCH de una variante: talla, stock o los dos (al menos uno)."""
    talla: Talla | None = None
    stock: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def al_menos_un_campo(self):
        if self.talla is None and self.stock is None:
            raise ValueError("Hay que enviar talla, stock o los dos")
        return self


class ProductoDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nombre: str
    descripcion: str | None = None
    precio: float
    imagen_url: str | None = None
    evento_id: str | None = None
    activo: bool = True
    variantes: list[VarianteDTO] = []


class ProductoEntradaDTO(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9-]+$", max_length=50)
    nombre: str = Field(min_length=1, max_length=150)
    descripcion: str | None = None
    precio: float = Field(ge=0)
    imagen_url: str | None = Field(default=None, max_length=500)
    evento_id: str | None = None
    activo: bool = True
