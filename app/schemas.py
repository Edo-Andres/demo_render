"""Contratos HTTP: entrada validada y respuesta sin trazas internas."""

from pydantic import BaseModel, ConfigDict, Field

from soporte.schemas import FragmentoPolitica


class ConsultaEntrada(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    pregunta: str = Field(strict=True, min_length=1, max_length=2000)


class ConsultaSalida(BaseModel):
    consulta_id: str
    respuesta: str
    fuentes_consultadas: list[FragmentoPolitica] = Field(
        default_factory=list,
        description="Fragmentos recuperados por las herramientas; no implica que todos se citen o respondan la pregunta.",
    )
