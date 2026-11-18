"""Embeddings de texto y ordenacion por similitud coseno en memoria."""

import math

from google.genai import types

from .schemas import FragmentoPolitica

MODELO_EMBEDDINGS = "gemini-embedding-001"
DIMENSIONES = 768


def normalizar(vector: list[float]) -> list[float]:
    if not vector or any(not math.isfinite(valor) for valor in vector):
        raise ValueError("El vector debe contener numeros finitos.")
    norma = math.hypot(*vector)
    if norma == 0 or not math.isfinite(norma):
        raise ValueError("El vector debe tener una norma finita mayor que cero.")
    return [valor / norma for valor in vector]


def generar_embeddings(cliente, textos: list[str], tarea: str) -> list[list[float]]:
    """Usa contratos distintos para documentos y consultas del mismo modelo."""
    if tarea not in ("RETRIEVAL_DOCUMENT", "RETRIEVAL_QUERY"):
        raise ValueError("Tarea de recuperacion desconocida.")
    if not textos or any(not texto.strip() for texto in textos):
        raise ValueError("Se necesitan textos no vacios.")
    respuesta = cliente.models.embed_content(
        model=MODELO_EMBEDDINGS, contents=textos,
        config=types.EmbedContentConfig(task_type=tarea, output_dimensionality=DIMENSIONES),
    )
    embeddings = respuesta.embeddings or []
    if len(embeddings) != len(textos):
        raise ValueError("La API no devolvio un vector por texto.")
    vectores = []
    for embedding in embeddings:
        valores = embedding.values or []
        if len(valores) != DIMENSIONES:
            raise ValueError("Dimension del embedding inesperada.")
        vectores.append(normalizar(valores))
    return vectores


class BuscadorSemantico:
    """Compara todos los fragmentos: suficiente para las seis secciones del curso."""

    def __init__(self, fragmentos: list[FragmentoPolitica], vectores: list[list[float]]):
        if not fragmentos or len(fragmentos) != len(vectores):
            raise ValueError("Se necesita un vector por fragmento.")
        self.fragmentos = list(fragmentos)
        self.vectores = [normalizar(vector) for vector in vectores]
        self.dimension = len(self.vectores[0])
        if any(len(vector) != self.dimension for vector in self.vectores):
            raise ValueError("Todos los vectores deben tener la misma dimension.")

    def buscar(self, vector_consulta: list[float]) -> list[tuple[FragmentoPolitica, float]]:
        consulta = normalizar(vector_consulta)
        if len(consulta) != self.dimension:
            raise ValueError("La consulta y los documentos tienen dimensiones distintas.")
        resultados = [
            (fragmento, max(-1.0, min(1.0, math.fsum(a * b for a, b in zip(consulta, vector)))))
            for fragmento, vector in zip(self.fragmentos, self.vectores)
        ]
        resultados.sort(key=lambda elemento: elemento[1], reverse=True)
        # Sin umbral calibrado: devuelve candidatos incluso si no hay respuesta.
        return resultados[:3]
