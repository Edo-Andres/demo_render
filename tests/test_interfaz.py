"""Pantalla, recursos y control de acceso HTTP sin invocar modelos."""

import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import crear_app
from app.schemas import ConsultaSalida


class InterfazAccesoTests(unittest.TestCase):
    def setUp(self):
        self.servicio = AsyncMock(return_value=ConsultaSalida(consulta_id="prueba", respuesta="Respuesta de prueba"))
        self.enterContext(patch("app.main.load_dotenv_for_agent"))

    def iniciar(self, variables=None):
        entorno = {"RENDER": "", "DEMO_USUARIO": "", "DEMO_CLAVE": ""}
        entorno.update(variables or {})
        self.enterContext(patch.dict("os.environ", entorno))
        return self.enterContext(TestClient(crear_app(self.servicio)))

    def acceso(self):
        return {"DEMO_USUARIO": "demo-prueba", "DEMO_CLAVE": "clave-ficticia-pruebas"}

    def test_pantalla_local_se_sirve_sin_invocar_modelo(self):
        cliente = self.iniciar()
        respuesta = cliente.get("/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("text/html", respuesta.headers["content-type"])
        self.assertIn('id="consulta-form"', respuesta.text)
        self.assertEqual(respuesta.headers["cache-control"], "no-store")
        self.servicio.assert_not_awaited()

    def test_recursos_de_interfaz_y_favicon_disponibles(self):
        cliente = self.iniciar()
        for ruta in ("/static/app.js", "/static/styles.css", "/static/favicon.svg", "/favicon.ico"):
            with self.subTest(ruta=ruta):
                self.assertEqual(cliente.get(ruta).status_code, 200)
        self.servicio.assert_not_awaited()

    def test_static_no_expone_html_protegido_ni_archivos_del_proyecto(self):
        cliente = self.iniciar(self.acceso())
        for ruta in ("/static/index.html", "/static/%2e%2e/main.py", "/static/%2e%2e/%2e%2e/soporte/.env"):
            with self.subTest(ruta=ruta):
                self.assertEqual(cliente.get(ruta).status_code, 404)

    def test_sin_credenciales_se_protegen_pantalla_api_y_documentacion(self):
        cliente = self.iniciar(self.acceso())
        for ruta in ("/", "/docs", "/openapi.json"):
            with self.subTest(ruta=ruta):
                respuesta = cliente.get(ruta)
                self.assertEqual(respuesta.status_code, 401)
                self.assertIn("Basic", respuesta.headers["www-authenticate"])
        self.assertEqual(cliente.post("/consultas", json={"pregunta": "Hola"}).status_code, 401)
        self.assertEqual(cliente.get("/health").status_code, 200)
        self.servicio.assert_not_awaited()

    def test_usuario_o_clave_incorrectos_no_consumen_modelo(self):
        cliente = self.iniciar(self.acceso())
        for auth in (("otro", "clave-ficticia-pruebas"), ("demo-prueba", "incorrecta"), ("otro", "incorrecta")):
            with self.subTest(usuario=auth[0]):
                self.assertEqual(cliente.post("/consultas", json={"pregunta": "Hola"}, auth=auth).status_code, 401)
        self.servicio.assert_not_awaited()

    def test_acceso_correcto_permite_pantalla_docs_y_consulta(self):
        cliente = self.iniciar(self.acceso())
        auth = ("demo-prueba", "clave-ficticia-pruebas")
        for ruta in ("/", "/docs", "/openapi.json"):
            self.assertEqual(cliente.get(ruta, auth=auth).status_code, 200)
        self.assertEqual(cliente.post("/consultas", json={"pregunta": "Hola"}, auth=auth).status_code, 200)
        self.servicio.assert_awaited_once_with("Hola")

    def test_render_sin_acceso_configurado_no_arranca(self):
        with self.assertRaises(RuntimeError):
            self.iniciar({"RENDER": "true"})
        self.servicio.assert_not_awaited()

    def test_credenciales_parciales_no_arrancan(self):
        for variables in ({"DEMO_USUARIO": "demo"}, {"DEMO_CLAVE": "clave"},
                          {"DEMO_USUARIO": "demo", "DEMO_CLAVE": "   "}):
            with self.subTest(variables=list(variables)), self.assertRaises(RuntimeError):
                self.iniciar(variables)

    def test_render_con_acceso_configurado_arranca_protegido(self):
        cliente = self.iniciar({**self.acceso(), "RENDER": "true"})
        self.assertEqual(cliente.get("/").status_code, 401)
        self.assertEqual(cliente.get("/health").status_code, 200)
        self.assertEqual(cliente.get("/", auth=("demo-prueba", "clave-ficticia-pruebas")).status_code, 200)

    def test_los_recursos_publicos_no_contienen_clave_de_acceso(self):
        cliente = self.iniciar(self.acceso())
        for ruta in ("/static/app.js", "/static/styles.css"):
            respuesta = cliente.get(ruta)
            self.assertEqual(respuesta.status_code, 200)
            self.assertNotIn(self.acceso()["DEMO_CLAVE"], respuesta.text)
            self.assertNotIn("GOOGLE_API_KEY", respuesta.text)


if __name__ == "__main__":
    unittest.main()
