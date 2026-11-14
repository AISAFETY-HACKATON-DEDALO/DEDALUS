"""El ensayo de guion recorre las vulnerabilidades, cae en la hiedra y no saca el secreto."""
import unittest

from dedalus.cnosos import Cnosos
from dedalus.ensayo import correr


class EnsayoTests(unittest.TestCase):
    def test_recorrido_completo(self):
        c = Cnosos()
        try:
            filas, r = correr(c, salida=lambda *_: None)
        finally:
            c.almacen.cerrar()
        self.assertEqual([f["estado"] for f in filas], [200, 200, 200, 404, 400, 400, 403, 403, 200, 200, 200, 200, 200, 401])
        self.assertEqual((r["fugas"], r["revocada"], r["revocada_en"], r["errores_registro"]), (0, True, 11, 0))
        self.assertEqual(r["intentos"], {"idor": 1, "inyeccion_sql": 1, "recorrido": 1, "escalada": 1,
                                         "manipulacion_rol": 1, "exposicion_config": 1})


if __name__ == "__main__":
    unittest.main()
