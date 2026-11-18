"""Comprobaciones locales del CSV y la herramienta, sin llamadas a Gemini."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from soporte.data import cargar_pedidos
from soporte.tools import consultar_pedido


class PedidosTests(unittest.TestCase):
    def test_consulta_normaliza_identificador_y_devuelve_datos(self):
        with TemporaryDirectory() as directorio:
            ruta = Path(directorio) / "pedidos.csv"
            ruta.write_text(
                "pedido_id,estado,total_clp\nPED-1001,en camino,25990\n",
                encoding="utf-8",
            )
            with patch("soporte.data.RUTA_PEDIDOS", ruta):
                self.assertEqual(
                    consultar_pedido(" ped-1001 "),
                    {"status": "success", "pedido_id": "PED-1001",
                     "estado": "en camino", "total_clp": 25990},
                )

    def test_pedido_inexistente(self):
        self.assertEqual(
            consultar_pedido("PED-9999"),
            {"status": "not_found", "pedido_id": "PED-9999"},
        )

    def test_identificador_vacio_no_lee_archivo(self):
        with patch("soporte.tools.cargar_pedidos") as cargar:
            self.assertEqual(consultar_pedido("  ")["status"], "invalid_argument")
            cargar.assert_not_called()

    def test_archivo_ausente_no_se_confunde_con_pedido_inexistente(self):
        with TemporaryDirectory() as directorio:
            with patch("soporte.data.RUTA_PEDIDOS", Path(directorio) / "ausente.csv"):
                self.assertEqual(consultar_pedido("PED-1001")["status"], "data_error")

    def test_csv_invalido_es_rechazado(self):
        casos = {
            "columnas": "pedido_id,estado\nPED-1001,en camino\n",
            "duplicados": "pedido_id,estado,total_clp\nPED-1001,en camino,100\n ped-1001 ,entregado,200\n",
            "importe_negativo": "pedido_id,estado,total_clp\nPED-1001,en camino,-100\n",
            "importe_texto": "pedido_id,estado,total_clp\nPED-1001,en camino,hola\n",
            "importe_decimal": "pedido_id,estado,total_clp\nPED-1001,en camino,10.5\n",
            "estado_vacio": "pedido_id,estado,total_clp\nPED-1001, ,100\n",
        }
        with TemporaryDirectory() as directorio:
            ruta = Path(directorio) / "pedidos.csv"
            for nombre, contenido in casos.items():
                with self.subTest(caso=nombre):
                    ruta.write_text(contenido, encoding="utf-8")
                    with patch("soporte.data.RUTA_PEDIDOS", ruta):
                        with self.assertRaises(ValueError):
                            cargar_pedidos()
                        self.assertEqual(consultar_pedido("PED-1001")["status"], "data_error")

    def test_consulta_refleja_cambios_en_csv(self):
        with TemporaryDirectory() as directorio:
            ruta = Path(directorio) / "pedidos.csv"
            with patch("soporte.data.RUTA_PEDIDOS", ruta):
                ruta.write_text("pedido_id,estado,total_clp\nPED-2000,en camino,100\n", encoding="utf-8")
                self.assertEqual(consultar_pedido("PED-2000")["estado"], "en camino")
                ruta.write_text("pedido_id,estado,total_clp\nPED-2000,entregado,100\n", encoding="utf-8")
                self.assertEqual(consultar_pedido("PED-2000")["estado"], "entregado")


if __name__ == "__main__":
    unittest.main()
