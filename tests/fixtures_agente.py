"""Apoyos de pruebas sin evaluadores ni llamadas a servicios externos."""

from collections.abc import AsyncGenerator
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch

from google.adk.models import LlmCapabilities
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from soporte.documentos import cargar_fragmentos
from soporte.recuperacion import CONFIGURACION_INDICE
from soporte.semantica import DIMENSIONES


class ModeloSimulado(BaseLlm):
    model: str = "simulado"
    modo: str = "politicas"

    @property
    def capabilities(self):
        return LlmCapabilities(output_schema_and_tools=False)

    async def generate_content_async(self, llm_request, stream=False) -> AsyncGenerator[LlmResponse, None]:
        ultimo = llm_request.contents[-1]
        if self.modo == "error":
            raise RuntimeError("Fallo simulado.")
        if self.modo == "aclarar":
            parte = types.Part(text="Buscas seguimiento o caracteristicas?")
        elif any(p.function_response is not None for p in ultimo.parts):
            parte = types.Part(text="Respuesta simulada para revision.")
        elif self.modo == "pedido":
            argumentos = {"pedido_id": "PED-1001"} if "PED-1001" in ultimo.parts[0].text else {}
            parte = types.Part.from_function_call(name="consultar_pedido", args=argumentos)
        else:
            parte = types.Part.from_function_call(
                name="buscar_politicas", args={"consulta": "horario de atencion"},
            )
        yield LlmResponse(content=types.Content(role="model", parts=[parte]))


def preparar_recuperacion(caso):
    temporal = TemporaryDirectory()
    caso.addCleanup(temporal.cleanup)
    caso.carpeta = Path(temporal.name)
    caso.ruta = caso.carpeta / "indice.json"
    caso.fragmentos = cargar_fragmentos()
    caso.vectores = [[float(i == j) for j in range(DIMENSIONES)]
                     for i in range(len(caso.fragmentos))]
    caso.indice = {"configuracion": CONFIGURACION_INDICE,
                   "fragmentos": [f.model_dump() for f in caso.fragmentos],
                   "vectores_documentos": caso.vectores}
    caso.ruta.write_text(json.dumps(caso.indice), encoding="utf-8")
    caso.enterContext(patch("soporte.recuperacion.RUTA_INDICE", caso.ruta))
    horario = next(i for i, f in enumerate(caso.fragmentos) if f.seccion == "Horario de atencion")
    caso.cliente = Mock()
    caso.cliente.models.embed_content.return_value = SimpleNamespace(
        embeddings=[SimpleNamespace(values=caso.vectores[horario])])
    caso.crear_cliente = caso.enterContext(patch("soporte.recuperacion.crear_cliente", return_value=caso.cliente))

