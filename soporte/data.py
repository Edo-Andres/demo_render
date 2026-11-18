"""Lectura y validacion de los pedidos ficticios del curso."""

from pathlib import Path

import pandas as pd

from .schemas import ESTADOS_VALIDOS

RUTA_PEDIDOS = Path(__file__).resolve().parent / "data" / "pedidos.csv"


def cargar_pedidos() -> pd.DataFrame:
    """Lee el CSV y rechaza datos incompletos, duplicados o importes invalidos.

    Los errores de lectura o validacion se propagan a la herramienta.
    """
    pedidos = pd.read_csv(
        RUTA_PEDIDOS,
        encoding="utf-8",
        dtype={"pedido_id": "string", "estado": "string", "total_clp": "int64"},
        keep_default_na=False,
    )
    columnas_requeridas = {"pedido_id", "estado", "total_clp"}
    if not columnas_requeridas.issubset(pedidos.columns):
        raise ValueError("El CSV debe incluir pedido_id, estado y total_clp.")

    pedidos["pedido_id"] = pedidos["pedido_id"].str.strip().str.upper()
    pedidos["estado"] = pedidos["estado"].str.strip().str.lower()

    if (pedidos["pedido_id"] == "").any() or (pedidos["estado"] == "").any():
        raise ValueError("Los identificadores y estados no pueden estar vacios.")
    if pedidos["pedido_id"].duplicated().any():
        raise ValueError("Los identificadores de pedido deben ser unicos.")
    if (pedidos["total_clp"] < 0).any():
        raise ValueError("Los importes no pueden ser negativos.")

    if not pedidos["estado"].isin(ESTADOS_VALIDOS).all():
        raise ValueError("Estado de pedido no reconocido en el CSV.")

    return pedidos
