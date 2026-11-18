"""Herramientas de pedidos, resumenes y consulta de politicas ficticias."""

from google.adk.tools import ToolContext

from .data import cargar_pedidos
from .documentos import palabras
from .recuperacion import ErrorEmbeddings, recuperar_politicas
from .schemas import (
    ESTADOS_VALIDOS,
    ErrorHerramienta,
    PedidoEncontrado,
    PedidoNoEncontrado,
    ResumenVentas,
    ResultadoPoliticas,
)


def consultar_pedido(
    pedido_id: str = "", tool_context: ToolContext | None = None
) -> dict:
    """Consulta el estado y total de un pedido ficticio por su identificador.

    Args:
        pedido_id: Identificador del pedido, por ejemplo PED-1001.
            Si se omite, consulta el pedido activo de esta sesion.
        tool_context: Contexto de sesion inyectado por ADK, no por el modelo.

    Returns:
        Diccionario con status: success, not_found, invalid_argument o data_error.
        Un error de datos no significa que el pedido no exista.
    """
    identificador = pedido_id.strip().upper()
    if tool_context is not None:
        if identificador:
            # Evita reutilizar el pedido anterior si la nueva consulta falla.
            tool_context.state["pedido_activo"] = None
        else:
            identificador = tool_context.state.get("pedido_activo") or ""
    if not identificador:
        return ErrorHerramienta(
            status="invalid_argument", mensaje="Indica el identificador del pedido; no hay un pedido activo para consultar."
        ).model_dump()

    try:
        pedidos = cargar_pedidos()
    except (OSError, UnicodeError, ValueError):
        return ErrorHerramienta(
            status="data_error",
            mensaje="No se pudieron cargar los pedidos. Revisa el archivo CSV y su formato.",
        ).model_dump()

    coincidencias = pedidos.loc[pedidos["pedido_id"] == identificador]
    if coincidencias.empty:
        return PedidoNoEncontrado(pedido_id=identificador).model_dump()

    pedido = coincidencias.iloc[0]
    resultado = PedidoEncontrado(
        pedido_id=identificador,
        estado=str(pedido["estado"]),
        total_clp=int(pedido["total_clp"]),
    ).model_dump()
    if tool_context is not None:
        tool_context.state["pedido_activo"] = identificador
    return resultado


def resumir_ventas(estado: str = "") -> dict:
    """Cuenta pedidos y suma sus importes; no calcula ingresos cobrados.

    Args:
        estado: Filtro opcional: preparando, en camino o entregado.
            Omite el argumento o usa una cadena vacia para incluir todos los pedidos.

    Returns:
        Diccionario con cantidad_pedidos y total_clp si status es success.
        estado es null cuando se incluyen todos los pedidos.
        Un filtro valido sin coincidencias devuelve ceros, no un error.
        Un estado desconocido devuelve invalid_argument; un fallo de CSV, data_error.
    """
    filtro = estado.strip().lower()
    if filtro and filtro not in ESTADOS_VALIDOS:
        return ErrorHerramienta(
            status="invalid_argument",
            mensaje="Estado invalido. Usa preparando, en camino o entregado; omite el filtro para todos.",
        ).model_dump()

    try:
        pedidos = cargar_pedidos()
    except (OSError, UnicodeError, ValueError):
        return ErrorHerramienta(
            status="data_error",
            mensaje="No se pudieron cargar los pedidos. Revisa el archivo CSV y su formato.",
        ).model_dump()

    if filtro:
        pedidos = pedidos.loc[pedidos["estado"] == filtro]

    return ResumenVentas(
        estado=filtro or None,
        cantidad_pedidos=len(pedidos),
        total_clp=int(pedidos["total_clp"].sum()),
    ).model_dump()


def buscar_politicas(consulta: str) -> dict:
    """Busca fragmentos de politicas ficticias de envio, devolucion y atencion.

    Args:
        consulta: Pregunta concreta sobre una politica, incluyendo el tema.

    Returns:
        Hasta tres fragmentos con archivo, seccion y texto. success indica
        candidatos semanticos, no garantiza que respondan toda la pregunta.
        Sin umbral devuelve candidatos aunque falte evidencia; no inventes una politica.
        invalid_argument solicita una pregunta concreta; data_error indica
        problemas con documentos, indice o servicio de embeddings.
        Cita solo fuentes devueltas y afirma
        solo lo que sus textos sustentan.
    """
    if not palabras(consulta):
        return ErrorHerramienta(
            status="invalid_argument",
            mensaje="Indica una pregunta concreta sobre envios, devoluciones o atencion.",
        ).model_dump()
    try:
        fragmentos = recuperar_politicas(consulta)
    except (OSError, UnicodeError, ValueError, ErrorEmbeddings):
        return ErrorHerramienta(
            status="data_error",
            mensaje="No se pudieron consultar las politicas en este momento.",
        ).model_dump()
    return ResultadoPoliticas(
        status="success" if fragmentos else "not_found",
        fragmentos=fragmentos,
    ).model_dump()
