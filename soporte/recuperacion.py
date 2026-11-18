"""Recuperacion semantica de politicas para las herramientas del agente."""

from pathlib import Path

from google import genai
from google.genai import types

from .documentos import cargar_fragmentos
from .schemas import IndicePoliticas
from .semantica import BuscadorSemantico, DIMENSIONES, MODELO_EMBEDDINGS, generar_embeddings

RUTA_INDICE = Path(__file__).resolve().parent / "data" / "indice_politicas.json"
CONFIGURACION_INDICE = {
    "modelo_embeddings": MODELO_EMBEDDINGS, "dimensiones": DIMENSIONES,
    "tarea_documentos": "RETRIEVAL_DOCUMENT", "tarea_consultas": "RETRIEVAL_QUERY",
    "top_k": 3, "umbral_semantico": None,
}


class ErrorEmbeddings(Exception):
    """No se pudo generar el vector de consulta; no equivale a falta de evidencia."""


def validar_indice(indice: IndicePoliticas) -> BuscadorSemantico:
    if indice.configuracion != CONFIGURACION_INDICE:
        raise ValueError("El indice no corresponde a la configuracion de recuperacion.")
    if indice.fragmentos != cargar_fragmentos():
        raise ValueError("El corpus cambio desde la preparacion del indice.")
    if any(len(vector) != DIMENSIONES for vector in indice.vectores_documentos):
        raise ValueError("Dimension de documentos inesperada.")
    return BuscadorSemantico(indice.fragmentos, indice.vectores_documentos)


def cargar_indice() -> BuscadorSemantico:
    # Lectura local por consulta: detecta cambios sin mantener una cache obsoleta.
    indice = IndicePoliticas.model_validate_json(RUTA_INDICE.read_text(encoding="utf-8"))
    return validar_indice(indice)


def crear_cliente():
    """Frontera de construccion del SDK, sustituible en pruebas sin alterar sus tipos."""
    return genai.Client(http_options=types.HttpOptions(timeout=60000))


def recuperar_politicas(consulta: str):
    buscador = cargar_indice()
    try:
        cliente = crear_cliente()
        try:
            vector = generar_embeddings(cliente, [consulta], "RETRIEVAL_QUERY")[0]
        finally:
            cliente.close()
    except Exception as error:
        # Frontera con el proveedor: engloba errores SDK, transporte y configuracion.
        # La carga y validacion del indice quedan fuera para distinguir fallos locales.
        raise ErrorEmbeddings("No se pudo generar el embedding de consulta.") from error
    return [fragmento for fragmento, _ in buscador.buscar(vector)]
