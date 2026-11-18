"""Contratos de los resultados que devuelven las herramientas."""

from typing import Literal, get_args

from pydantic import BaseModel, Field

EstadoPedido = Literal["preparando", "en camino", "entregado"]
ESTADOS_VALIDOS = get_args(EstadoPedido)


class PedidoEncontrado(BaseModel):
    status: Literal["success"] = "success"
    pedido_id: str
    estado: EstadoPedido
    total_clp: int = Field(ge=0, strict=True)


class PedidoNoEncontrado(BaseModel):
    status: Literal["not_found"] = "not_found"
    pedido_id: str


class ErrorHerramienta(BaseModel):
    status: Literal["invalid_argument", "data_error"]
    mensaje: str


class ResumenVentas(BaseModel):
    status: Literal["success"] = "success"
    estado: EstadoPedido | None = None
    cantidad_pedidos: int = Field(ge=0, strict=True)
    total_clp: int = Field(ge=0, strict=True)


class FragmentoPolitica(BaseModel):
    archivo: str
    seccion: str
    texto: str


class ResultadoPoliticas(BaseModel):
    status: Literal["success", "not_found"]
    fragmentos: list[FragmentoPolitica] = Field(default_factory=list)


class IndicePoliticas(BaseModel):
    configuracion: dict
    fragmentos: list[FragmentoPolitica]
    vectores_documentos: list[list[float]]
