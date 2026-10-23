"""Pruebas de la API web: usan el servidor real con una base SQLite temporal."""
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from reportlab.pdfgen import canvas

from hydisa.base_datos import BaseDatos
from servidor import crear_servidor


def pdf_ejemplo(ruta, lineas):
    c = canvas.Canvas(str(ruta))
    for n, linea in enumerate(lineas):
        c.drawString(72, 780 - 20 * n, linea)
    c.save()


class PruebasAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.bd = BaseDatos(":memory:")      # en memoria: nunca toca la base real
        cls.servidor = crear_servidor(cls.bd, puerto=0)
        cls.base = f"http://127.0.0.1:{cls.servidor.server_port}"
        threading.Thread(target=cls.servidor.serve_forever, daemon=True).start()
        cls.pdf = cls.tmp / "reporte.pdf"
        pdf_ejemplo(cls.pdf, ["Reporte Healy", "estrés y ansiedad altos", "poco descanso y sueño"])

    @classmethod
    def tearDownClass(cls):
        cls.servidor.shutdown()
        cls.servidor.server_close()
        cls.bd.cerrar()

    def llamar(self, metodo, ruta, datos=None, token=None, crudo=None, cabeceras=None):
        cuerpo = crudo if crudo is not None else (json.dumps(datos).encode() if datos is not None else None)
        peticion = urllib.request.Request(self.base + ruta, data=cuerpo, method=metodo)
        if crudo is None and cuerpo is not None:
            peticion.add_header("Content-Type", "application/json")
        if token:
            peticion.add_header("Authorization", f"Bearer {token}")
        for k, v in (cabeceras or {}).items():
            peticion.add_header(k, v)
        try:
            with urllib.request.urlopen(peticion) as r:
                datos_r = r.read()
                return r.status, (json.loads(datos_r) if "json" in r.headers["Content-Type"] else datos_r)
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def entrar(self, correo="ana@correo.com"):
        self.llamar("POST", "/api/registro", {"nombre": "Ana", "correo": correo, "clave": "clave1234"})
        return self.llamar("POST", "/api/login", {"correo": correo, "clave": "clave1234"})[1]["token"]

    def test_sin_sesion_es_401(self):
        self.assertEqual(self.llamar("GET", "/api/reportes")[0], 401)

    def test_registro_login_y_errores(self):
        self.assertEqual(self.llamar("POST", "/api/registro", {"nombre": "A", "correo": "mal", "clave": "clave1234"})[0], 400)
        self.assertEqual(self.llamar("POST", "/api/login", {"correo": "no@no.com", "clave": "xxxxxxxx"})[0], 401)

    def test_flujo_completo(self):
        t = self.entrar("flujo@correo.com")
        codigo, r = self.llamar("POST", "/api/reportes", crudo=self.pdf.read_bytes(), token=t,
                                cabeceras={"X-Nombre-Archivo": "reporte.pdf"})
        self.assertEqual(codigo, 201)
        self.assertIn("Emocional", r["palabras"])
        self.assertTrue(r["ruta"])
        rid = r["reporte_id"]
        self.assertEqual(self.llamar("GET", "/api/reportes", token=t)[1]["reportes"][0]["id"], rid)
        codigo, r2 = self.llamar("POST", f"/api/reportes/{rid}/actividades/1/cumplir", token=t)
        self.assertEqual(codigo, 200)
        self.assertGreater(r2["progreso"], 0)
        self.assertEqual(self.llamar("POST", f"/api/reportes/{rid}/actividades/99/cumplir", token=t)[0], 404)
        self.assertIn("Emocional", self.llamar("GET", f"/api/reportes/{rid}/palabras", token=t)[1]["palabras"])
        codigo, pdf = self.llamar("GET", f"/api/reportes/{rid}/pdf", token=t)
        self.assertEqual(codigo, 200)
        self.assertTrue(pdf.startswith(b"%PDF-"))
        # duplicado y archivo falso
        self.assertEqual(self.llamar("POST", "/api/reportes", crudo=self.pdf.read_bytes(), token=t,
                                     cabeceras={"X-Nombre-Archivo": "reporte.pdf"})[0], 400)
        self.assertEqual(self.llamar("POST", "/api/reportes", crudo=b"hola", token=t,
                                     cabeceras={"X-Nombre-Archivo": "falso.pdf"})[0], 400)

    def test_aislamiento_entre_usuarios(self):
        t1, t2 = self.entrar("uno@correo.com"), self.entrar("dos@correo.com")
        pdf2 = self.tmp / "otro.pdf"
        pdf_ejemplo(pdf2, ["ejercicio y estres cuarto reporte"])
        rid = self.llamar("POST", "/api/reportes", crudo=pdf2.read_bytes(), token=t1,
                          cabeceras={"X-Nombre-Archivo": "otro.pdf"})[1]["reporte_id"]
        self.assertEqual(self.llamar("GET", f"/api/reportes/{rid}/palabras", token=t2)[0], 404)
        self.assertEqual(self.llamar("GET", f"/api/reportes/{rid}/ruta", token=t2)[1]["ruta"], [])

    def test_frontend_se_sirve_y_no_sale_de_su_carpeta(self):
        with urllib.request.urlopen(self.base + "/") as r:
            self.assertIn(b"HYDISA", r.read())
        self.assertEqual(self.llamar("GET", "/..%2Fservidor.py")[0], 404)


if __name__ == "__main__":
    unittest.main()
