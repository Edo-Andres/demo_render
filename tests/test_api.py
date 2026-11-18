"""Contratos HTTP y servicio ADK con modelos externos simulados."""

from unittest.mock import AsyncMock, Mock, patch
import unittest

from fastapi.testclient import TestClient
from google.adk.agents import Agent
from google.adk.events import Event
from google.genai import types

from app.main import crear_app
from app.schemas import ConsultaSalida
from app.servicio import ErrorConsulta, TiempoConsultaAgotado, consultar
from soporte.agent import root_agent
from fixtures_agente import ModeloSimulado, preparar_recuperacion


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.servicio = AsyncMock(return_value=ConsultaSalida(consulta_id="prueba", respuesta="Respuesta de prueba"))
        self.enterContext(patch.dict("os.environ", {"RENDER": "", "DEMO_USUARIO": "", "DEMO_CLAVE": ""}))
        self.enterContext(patch("app.main.load_dotenv_for_agent"))
        self.cliente = self.enterContext(TestClient(crear_app(self.servicio)))

    def test_health_no_invoca_al_agente(self):
        respuesta = self.cliente.get("/health")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json(), {"status": "ok"})
        self.servicio.assert_not_awaited()

    def test_consulta_valida_y_normaliza_espacios(self):
        respuesta = self.cliente.post("/consultas", json={"pregunta": "  Cuando atienden?  "})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(set(respuesta.json()), {"consulta_id", "respuesta", "fuentes_consultadas"})
        self.servicio.assert_awaited_once_with("Cuando atienden?")

    def test_entradas_invalidas_no_consumen_modelo(self):
        for cuerpo in ({}, {"pregunta": ""}, {"pregunta": "   "}, {"pregunta": "x" * 2001},
                       {"pregunta": 123}, {"pregunta": True}, [],
                       {"pregunta": "Hola", "session_id": "otro"}):
            with self.subTest(cuerpo=cuerpo):
                self.assertEqual(self.cliente.post("/consultas", json=cuerpo).status_code, 422)
        self.servicio.assert_not_awaited()

    def test_json_incompleto_no_invoca_servicio(self):
        respuesta = self.cliente.post("/consultas", content="{", headers={"Content-Type": "application/json"})
        self.assertEqual(respuesta.status_code, 422)
        self.servicio.assert_not_awaited()

    def test_error_no_expone_detalles_del_proveedor(self):
        self.servicio.side_effect = ErrorConsulta("Detalle interno de prueba")
        respuesta = self.cliente.post("/consultas", json={"pregunta": "Hola"})
        self.assertEqual(respuesta.status_code, 503)
        self.assertNotIn("Detalle interno", respuesta.text)

    def test_timeout_tiene_status_diferenciado(self):
        self.servicio.side_effect = TiempoConsultaAgotado("Detalle interno de prueba")
        respuesta = self.cliente.post("/consultas", json={"pregunta": "Hola"})
        self.assertEqual(respuesta.status_code, 504)
        self.assertNotIn("Detalle interno", respuesta.text)

    def test_documentacion_y_contrato_openapi_disponibles(self):
        self.assertEqual(self.cliente.get("/docs").status_code, 200)
        esquema = self.cliente.get("/openapi.json").json()
        self.assertIn("/consultas", esquema["paths"])
        entrada = esquema["components"]["schemas"]["ConsultaEntrada"]
        self.assertEqual(entrada["properties"]["pregunta"]["maxLength"], 2000)
        self.assertEqual(entrada["required"], ["pregunta"])
        self.servicio.assert_not_awaited()


class ServicioTests(unittest.IsolatedAsyncioTestCase):
    def agente(self, modo="aclarar"):
        return Agent(name="soporte", model=ModeloSimulado(modo=modo), tools=root_agent.tools)

    async def test_sesion_independiente_y_respuesta_sin_herramientas(self):
        agente = self.agente()
        primera = await consultar("Que hago?", agente)
        segunda = await consultar("Otra pregunta", agente)
        self.assertNotEqual(primera.consulta_id, segunda.consulta_id)
        self.assertEqual(primera.fuentes_consultadas, [])
        self.assertIn("caracteristicas", primera.respuesta)

    async def test_error_del_modelo_se_traduce_a_error_de_servicio(self):
        with self.assertRaises(ErrorConsulta) as error:
            await consultar("Hola", self.agente("error"))
        self.assertNotIn("Fallo simulado", str(error.exception))

    async def test_limite_de_tiempo_se_distingue(self):
        with self.assertRaises(TiempoConsultaAgotado):
            await consultar("Hola", self.agente(), timeout=0)

    def runner_con_eventos(self, eventos):
        runner = Mock()
        runner.close = AsyncMock()
        async def emitir(**kwargs):
            for evento in eventos:
                yield evento
        runner.run_async = emitir
        return runner

    async def test_sin_respuesta_final_no_se_devuelve_exito(self):
        runner = self.runner_con_eventos([])
        with patch("app.servicio.Runner", return_value=runner):
            with self.assertRaises(ErrorConsulta):
                await consultar("Hola", self.agente())
        runner.close.assert_awaited_once()

    async def test_fuentes_vienen_de_herramientas_y_se_eliminan_duplicados(self):
        fragmento = {"archivo": "documentos/prueba.md", "seccion": "Horario", "texto": "Texto recuperado."}
        evento_fuente = Event(author="soporte", content=types.Content(role="user", parts=[
            types.Part.from_function_response(name="buscar_politicas", response={
                "status": "success", "fragmentos": [fragmento],
            })]))
        evento_final = Event(author="soporte", content=types.Content(role="model", parts=[
            types.Part(text="Respuesta sin citas textuales."),
        ]))
        runner = self.runner_con_eventos([evento_fuente, evento_fuente, evento_final])
        with patch("app.servicio.Runner", return_value=runner):
            respuesta = await consultar("Horario?", self.agente())
        self.assertEqual(len(respuesta.fuentes_consultadas), 1)
        self.assertEqual(respuesta.fuentes_consultadas[0].texto, "Texto recuperado.")
        self.assertEqual(respuesta.respuesta, "Respuesta sin citas textuales.")
        runner.close.assert_awaited_once()


class ApiRunnerTests(unittest.TestCase):
    def setUp(self):
        preparar_recuperacion(self)
        agente = Agent(name="soporte", model=ModeloSimulado(), tools=root_agent.tools)
        async def servicio(pregunta):
            return await consultar(pregunta, agente)
        self.enterContext(patch.dict("os.environ", {"RENDER": "", "DEMO_USUARIO": "", "DEMO_CLAVE": ""}))
        self.enterContext(patch("app.main.load_dotenv_for_agent"))
        self.http = self.enterContext(TestClient(crear_app(servicio)))

    def test_http_runner_y_recuperacion_con_api_externa_simulada(self):
        respuesta = self.http.post("/consultas", json={"pregunta": "Cuando atienden?"})
        self.assertEqual(respuesta.status_code, 200)
        fuente = respuesta.json()["fuentes_consultadas"][0]
        self.assertEqual(fuente["seccion"], "Horario de atencion")
        self.assertEqual(self.cliente.models.embed_content.call_count, 1)

    def test_error_de_herramienta_no_se_disfraza_de_exito_http(self):
        self.cliente.models.embed_content.side_effect = ConnectionError("Fallo de prueba")
        respuesta = self.http.post("/consultas", json={"pregunta": "Cuando atienden?"})
        self.assertEqual(respuesta.status_code, 503)
        self.assertNotIn("fuentes_consultadas", respuesta.json())


if __name__ == "__main__":
    unittest.main()
