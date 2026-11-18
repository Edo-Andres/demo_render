"""Pruebas de lectura y busqueda lexica de referencia, sin llamadas a Gemini."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from soporte.documentos import buscar_fragmentos
from soporte.tools import buscar_politicas


class DocumentosTests(unittest.TestCase):
    def test_plazo_envio_con_fuente_y_seccion(self):
        fragmentos = buscar_fragmentos("plazos de envio")
        fragmento = fragmentos[0]
        self.assertEqual(fragmento.archivo, "documentos/envios.md")
        self.assertEqual(fragmento.seccion, "Plazos de envio")
        self.assertIn("3 y 5 dias habiles", fragmento.texto)
        self.assertLessEqual(len(fragmentos), 3)

    def test_mayusculas_y_tildes_no_cambian_resultado(self):
        self.assertEqual(buscar_fragmentos("DEVOLUCI\u00d3N"), buscar_fragmentos("devolucion"))

    def test_pregunta_fuera_del_corpus_no_inventa_fuentes(self):
        self.assertEqual(buscar_fragmentos("garantia internacional"), [])

    def test_consulta_vacia_o_generica_no_lee_documentos(self):
        with patch("soporte.tools.recuperar_politicas") as cargar:
            for consulta in ("", " ??? ", "la politica del pedido"):
                with self.subTest(consulta=consulta):
                    self.assertEqual(buscar_politicas(consulta)["status"], "invalid_argument")
            cargar.assert_not_called()

    def test_documento_ausente_no_se_confunde_con_sin_coincidencias(self):
        with TemporaryDirectory() as carpeta:
            with patch("soporte.documentos.RUTA_DOCUMENTOS", Path(carpeta)):
                with self.assertRaises((OSError, UnicodeError, ValueError)):
                    buscar_fragmentos("envio")

    def test_documento_invalido_no_produce_respuesta_parcial(self):
        for contenido in ("# Sin secciones", "## Seccion vacia\n", "\ufffd"):
            with self.subTest(contenido=contenido):
                with patch("pathlib.Path.read_text", return_value=contenido):
                    with self.assertRaises(ValueError):
                        buscar_fragmentos("envio")
        with patch("pathlib.Path.read_text", side_effect=UnicodeError("UTF-8 invalido")):
            with self.assertRaises(UnicodeError):
                buscar_fragmentos("envio")

    def test_relee_el_texto_al_modificar_documento(self):
        with TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "politica.md"
            with patch("soporte.documentos.RUTA_DOCUMENTOS", Path(carpeta)), patch(
                "soporte.documentos.ARCHIVOS_POLITICAS", ("politica.md",)
            ):
                for horario in ("09:00", "10:00"):
                    ruta.write_text(f"# Atencion\n\n## Horario\nAbre a las {horario}.", encoding="utf-8")
                    resultado = buscar_fragmentos("horario")
                    self.assertIn(horario, resultado[0].texto)


if __name__ == "__main__":
    unittest.main()
