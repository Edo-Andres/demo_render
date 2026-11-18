"""API e interfaz de la demo, servidas por la misma aplicacion."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from google.adk.cli.utils.envs import load_dotenv_for_agent

from .schemas import ConsultaEntrada, ConsultaSalida
from .seguridad import cargar_acceso, verificar_acceso
from .servicio import ErrorConsulta, TiempoConsultaAgotado, consultar

RAIZ = Path(__file__).resolve().parents[1]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Lee soporte/.env en desarrollo; respeta variables definidas por el servidor.
    load_dotenv_for_agent(agent_name="soporte", agent_parent_folder=str(RAIZ))
    app.state.acceso = cargar_acceso()
    yield


def crear_app(servicio_consulta=consultar) -> FastAPI:
    """La fabrica permite probar HTTP con un servicio controlado y sin Gemini."""
    api = FastAPI(title="Demo de soporte", version="0.1.0", lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)
    protegida = [Depends(verificar_acceso)]
    carpeta_app = Path(__file__).resolve().parent
    # Los recursos estaticos son publicos; no contienen HTML privado ni secretos.
    api.mount("/static", StaticFiles(directory=carpeta_app / "static"), name="static")

    @api.get("/", include_in_schema=False, dependencies=protegida)
    async def inicio():
        return FileResponse(carpeta_app / "index.html", headers={"Cache-Control": "no-store"})

    @api.get("/docs", include_in_schema=False, dependencies=protegida)
    async def documentacion():
        return get_swagger_ui_html(openapi_url="/openapi.json", title="Demo de soporte - API")

    @api.get("/openapi.json", include_in_schema=False, dependencies=protegida)
    async def esquema():
        return JSONResponse(api.openapi())

    @api.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        return FileResponse(carpeta_app / "static/favicon.svg", media_type="image/svg+xml")

    @api.get("/health", summary="Comprueba que la API esta ejecutandose")
    async def health():
        # Liveness: no consume Gemini ni asegura que el proveedor este disponible.
        return {"status": "ok"}

    @api.post(
        "/consultas", response_model=ConsultaSalida, dependencies=protegida,
        summary="Consulta al asistente con una sesion temporal independiente",
        responses={503: {"description": "No se pudo completar la consulta"},
                   504: {"description": "Tiempo de espera agotado"}},
    )
    async def crear_consulta(entrada: ConsultaEntrada):
        try:
            return await servicio_consulta(entrada.pregunta)
        except TiempoConsultaAgotado:
            raise HTTPException(status_code=504, detail="La consulta tardo demasiado. Intentalo de nuevo.") from None
        except ErrorConsulta:
            raise HTTPException(status_code=503, detail="No se pudo completar la consulta en este momento.") from None

    return api


app = crear_app()
