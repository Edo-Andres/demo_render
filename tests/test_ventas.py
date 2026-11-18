"""Verifica calculos y contratos con un CSV independiente del ejercicio manual."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from soporte.schemas import ResumenVentas
from soporte.tools import consultar_pedido, resumir_ventas

CSV_PRUEBA = (
    "pedido_id,estado,total_clp\n"
    "PED-A,en camino,1000\n"
    "PED-B,entregado,2000\n"
    "PED-C,en camino,3000\n"
)


class VentasTests(unittest.TestCase):
    def setUp(self):
        temporal = TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        self.ruta = Path(temporal.name) / "pedidos.csv"
        self.ruta.write_text(CSV_PRUEBA, encoding="utf-8")
        parche = patch("soporte.data.RUTA_PEDIDOS", self.ruta)
        parche.start()
        self.addCleanup(parche.stop)

    def test_total_sin_filtro(self):
        self.assertEqual(resumir_ventas(), {
            "status": "success", "estado": None,
            "cantidad_pedidos": 3, "total_clp": 6000,
        })

    def test_filtra_y_normaliza_estado(self):
        self.assertEqual(resumir_ventas(" EN CAMINO "), {
            "status": "success", "estado": "en camino",
            "cantidad_pedidos": 2, "total_clp": 4000,
        })

    def test_estado_valido_sin_pedidos_devuelve_ceros(self):
        self.assertEqual(resumir_ventas("preparando"), {
            "status": "success", "estado": "preparando",
            "cantidad_pedidos": 0, "total_clp": 0,
        })

    def test_estado_invalido_no_lee_datos(self):
        with patch("soporte.tools.cargar_pedidos") as cargar:
            self.assertEqual(resumir_ventas("desconocido")["status"], "invalid_argument")
            cargar.assert_not_called()

    def test_csv_solo_cabecera_es_un_resumen_vacio(self):
        self.ruta.write_text("pedido_id,estado,total_clp\n", encoding="utf-8")
        resultado = resumir_ventas()
        self.assertEqual(resultado["status"], "success")
        self.assertEqual(resultado["cantidad_pedidos"], 0)
        self.assertEqual(resultado["total_clp"], 0)

    def test_error_datos_no_devuelve_un_total(self):
        for contenido in ("pedido_id,estado\nPED-A,en camino\n",
                          "pedido_id,estado,total_clp\nPED-A,desconocido,1000\n"):
            with self.subTest(contenido=contenido):
                self.ruta.write_text(contenido, encoding="utf-8")
                for herramienta in (resumir_ventas, lambda: consultar_pedido("PED-A")):
                    resultado = herramienta()
                    self.assertEqual(resultado["status"], "data_error")
                    self.assertNotIn("total_clp", resultado)

    def test_estado_csv_se_normaliza(self):
        self.ruta.write_text("pedido_id,estado,total_clp\nPED-A, EN CAMINO ,1000\n", encoding="utf-8")
        self.assertEqual(resumir_ventas("en camino")["total_clp"], 1000)
        self.assertEqual(consultar_pedido("PED-A")["estado"], "en camino")

    def test_contrato_rechaza_negativos_y_tipos_incorrectos(self):
        for campos in (
            {"cantidad_pedidos": -1, "total_clp": 1000},
            {"cantidad_pedidos": 1, "total_clp": -1000},
            {"cantidad_pedidos": 1, "total_clp": "1000"},
            {"cantidad_pedidos": 1, "total_clp": 10.5},
            {"estado": "desconocido", "cantidad_pedidos": 1, "total_clp": 1000},
        ):
            with self.subTest(campos=campos):
                with self.assertRaises(ValidationError):
                    ResumenVentas(**campos)


if __name__ == "__main__":
    unittest.main()
