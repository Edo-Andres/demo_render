"""Adaptador de ADK para una consulta independiente, sin depender de evaluacion."""

import asyncio
from uuid import uuid4

from google.adk.agents.run_config import RunConfig
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from soporte.agent import root_agent
from soporte.schemas import FragmentoPolitica
from .schemas import ConsultaSalida

MAX_LLM_CALLS = 6
TIMEOUT_SEGUNDOS = 60


class ErrorConsulta(Exception):
    """El agente o sus herramientas no completaron la consulta."""


class TiempoConsultaAgotado(ErrorConsulta):
    """Se agoto el tiempo de espera del adaptador."""


async def consultar(pregunta: str, agente=root_agent, timeout=TIMEOUT_SEGUNDOS) -> ConsultaSalida:
    consulta_id = uuid4().hex
    sesiones = InMemorySessionService()
    runner = Runner(app_name="soporte", agent=agente, session_service=sesiones)
    respuesta_final = ""
    fuentes = {}
    hubo_error = False
    try:
        async with asyncio.timeout(timeout):
            await sesiones.create_session(
                app_name="soporte", user_id="demo", session_id=consulta_id,
            )
            mensaje = types.Content(role="user", parts=[types.Part(text=pregunta)])
            async for evento in runner.run_async(
                user_id="demo", session_id=consulta_id, new_message=mensaje,
                run_config=RunConfig(max_llm_calls=MAX_LLM_CALLS),
            ):
                hubo_error = hubo_error or bool(evento.error_code)
                for resultado in evento.get_function_responses():
                    datos = resultado.response or {}
                    if datos.get("status") == "data_error":
                        hubo_error = True
                    if resultado.name == "buscar_politicas" and datos.get("status") == "success":
                        for datos_fuente in datos.get("fragmentos", []):
                            fuente = FragmentoPolitica.model_validate(datos_fuente)
                            fuentes[(fuente.archivo, fuente.seccion)] = fuente
                if (evento.author == agente.name and evento.is_final_response()
                        and evento.content and not evento.partial):
                    texto = "".join(parte.text for parte in evento.content.parts or []
                                    if parte.text and not parte.thought)
                    if texto:
                        respuesta_final = texto
            if hubo_error or not respuesta_final:
                raise ErrorConsulta("La ejecucion no produjo una respuesta utilizable.")
            return ConsultaSalida(
                consulta_id=consulta_id, respuesta=respuesta_final,
                fuentes_consultadas=list(fuentes.values()),
            )
    except TimeoutError as error:
        raise TiempoConsultaAgotado("Tiempo de consulta agotado.") from error
    except ErrorConsulta:
        raise
    except Exception as error:
        # Frontera con ADK/proveedor: las excepciones internas no viajan al cliente.
        raise ErrorConsulta("No se pudo completar la consulta.") from error
    finally:
        await runner.close()
