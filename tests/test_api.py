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
from hydisa.config import CORREO_ADMIN, PERMISOS
from hydisa.servicio_usuarios import ServicioUsuarios
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
        cls.clave_admin = "ClaveAdmin123"
        ServicioUsuarios(cls.bd).asegurar_administrador(cls.clave_admin)
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

    def token_admin(self):
        return self.llamar("POST", "/api/login", {"correo": CORREO_ADMIN, "clave": self.clave_admin})[1]["token"]

    def crear(self, correo, permisos=None, nombre="Ana"):
        """El administrador crea la cuenta (el registro público ya no existe)."""
        datos = {"nombre": nombre, "correo": correo, "clave": "clave1234",
                 "permisos": list(PERMISOS) if permisos is None else permisos}
        return self.llamar("POST", "/api/admin/usuarios", datos, token=self.token_admin())

    def entrar(self, correo="ana@correo.com", permisos=None):
        self.crear(correo, permisos)
        return self.llamar("POST", "/api/login", {"correo": correo, "clave": "clave1234"})[1]["token"]

    def test_sin_sesion_es_401(self):
        self.assertEqual(self.llamar("GET", "/api/reportes")[0], 401)

    def test_registro_login_y_errores(self):
        self.assertEqual(self.crear("mal")[0], 400)
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

    # ---------- control de acceso ----------
    def test_registro_publico_ya_no_existe(self):
        datos = {"nombre": "X", "correo": "x@correo.com", "clave": "clave1234"}
        self.assertEqual(self.llamar("POST", "/api/registro", datos)[0], 401)          # sin sesión: rechazado
        self.assertEqual(self.llamar("POST", "/api/registro", datos, token=self.token_admin())[0], 404)  # ni el admin: no existe
        self.assertEqual(self.llamar("POST", "/api/login", {"correo": "x@correo.com", "clave": "clave1234"})[0], 401)
        self.assertEqual(self.llamar("POST", "/api/admin/usuarios", datos)[0], 401)     # sin sesión

    def test_admin_se_identifica_en_el_servidor(self):
        usuario = self.llamar("POST", "/api/login", {"correo": CORREO_ADMIN, "clave": self.clave_admin})[1]["usuario"]
        self.assertTrue(usuario["es_admin"])
        t = self.entrar("comun@correo.com")
        self.assertFalse(self.llamar("GET", "/api/yo", token=t)[1]["usuario"]["es_admin"])

    def test_usuario_comun_recibe_403_en_todo_lo_admin(self):
        t = self.entrar("comun2@correo.com")
        for metodo, ruta, datos in [("GET", "/api/admin/usuarios", None), ("GET", "/api/admin/usuarios/1", None),
                                    ("POST", "/api/admin/usuarios", {"nombre": "Z", "correo": "z@correo.com", "clave": "clave1234"}),
                                    ("POST", "/api/admin/usuarios/1/permisos", {"permisos": []}),
                                    ("GET", "/api/admin/usuarios/1/reportes/1", None)]:
            self.assertEqual(self.llamar(metodo, ruta, datos, token=t)[0], 403, ruta)
        self.assertEqual(self.llamar("GET", "/api/admin/usuarios")[0], 401)

    def test_no_se_puede_pedir_rol_administrador(self):
        t = self.token_admin()
        datos = {"nombre": "Astuto", "correo": "astuto@correo.com", "clave": "clave1234", "rol": "administrador"}
        codigo, r = self.llamar("POST", "/api/admin/usuarios", datos, token=t)
        self.assertEqual(codigo, 201)
        self.assertEqual(r["usuario"]["rol"], "usuario")                  # el campo "rol" se ignora
        datos["correo"] = CORREO_ADMIN
        self.assertEqual(self.llamar("POST", "/api/admin/usuarios", datos, token=t)[0], 400)

    def test_admin_ve_usuarios_y_sus_datos(self):
        t = self.entrar("datos@correo.com")
        rid = self.llamar("POST", "/api/reportes", crudo=self.pdf.read_bytes(), token=t,
                          cabeceras={"X-Nombre-Archivo": "datos.pdf"})[1]["reporte_id"]
        ta = self.token_admin()
        lista = self.llamar("GET", "/api/admin/usuarios", token=ta)[1]
        fila = next(u for u in lista["usuarios"] if u["correo"] == "datos@correo.com")
        self.assertEqual(fila["n_reportes"], 1)
        self.assertEqual(len(lista["catalogo"]), len(PERMISOS))
        detalle = self.llamar("GET", f"/api/admin/usuarios/{fila['id']}", token=ta)[1]
        self.assertEqual(detalle["reportes"][0]["id"], rid)
        ruta = self.llamar("GET", f"/api/admin/usuarios/{fila['id']}/reportes/{rid}", token=ta)[1]
        self.assertTrue(ruta["ruta"])
        self.assertIn("Emocional", ruta["palabras"])
        self.assertEqual(self.llamar("GET", "/api/admin/usuarios/99999", token=ta)[0], 404)

    def test_permisos_limitados_se_aplican_en_el_servidor(self):
        t = self.entrar("solover@correo.com", permisos=["ver_reportes"])
        carga = dict(crudo=self.pdf.read_bytes(), token=t, cabeceras={"X-Nombre-Archivo": "a.pdf"})
        self.assertEqual(self.llamar("POST", "/api/reportes", **carga)[0], 403)
        self.assertEqual(self.llamar("GET", "/api/reportes", token=t)[0], 200)
        # otro usuario con todos los permisos crea un reporte; el de "solo ver" no puede marcarlo ni exportarlo
        t2 = self.entrar("completo@correo.com")
        rid = self.llamar("POST", "/api/reportes", crudo=self.pdf.read_bytes(), token=t2,
                          cabeceras={"X-Nombre-Archivo": "b.pdf"})[1]["reporte_id"]
        self.assertEqual(self.llamar("POST", f"/api/reportes/{rid}/actividades/1/cumplir", token=t)[0], 403)
        self.assertEqual(self.llamar("GET", f"/api/reportes/{rid}/pdf", token=t)[0], 403)

    def test_cambio_de_permisos_rige_sin_volver_a_entrar(self):
        t = self.entrar("cambia@correo.com")
        uid = self.llamar("GET", "/api/yo", token=t)[1]["usuario"]["id"]
        self.assertEqual(self.llamar("GET", "/api/reportes", token=t)[0], 200)
        ta = self.token_admin()
        codigo, r = self.llamar("POST", f"/api/admin/usuarios/{uid}/permisos", {"permisos": []}, token=ta)
        self.assertEqual((codigo, r["usuario"]["permisos"]), (200, []))
        self.assertEqual(self.llamar("GET", "/api/reportes", token=t)[0], 403)         # mismo token, ya sin permiso
        self.llamar("POST", f"/api/admin/usuarios/{uid}/permisos", {"permisos": ["ver_reportes"]}, token=ta)
        self.assertEqual(self.llamar("GET", "/api/reportes", token=t)[0], 200)

    def test_permisos_invalidos_y_admin_intocable(self):
        ta = self.token_admin()
        self.entrar("valida@correo.com")
        uid = next(u["id"] for u in self.llamar("GET", "/api/admin/usuarios", token=ta)[1]["usuarios"]
                   if u["correo"] == "valida@correo.com")
        self.assertEqual(self.llamar("POST", f"/api/admin/usuarios/{uid}/permisos", {"permisos": ["todo"]}, token=ta)[0], 400)
        self.assertEqual(self.llamar("POST", f"/api/admin/usuarios/{uid}/permisos", {"permisos": "ver_reportes"}, token=ta)[0], 400)
        admin_id = next(u["id"] for u in self.llamar("GET", "/api/admin/usuarios", token=ta)[1]["usuarios"]
                        if u["correo"] == CORREO_ADMIN)
        self.assertEqual(self.llamar("POST", f"/api/admin/usuarios/{admin_id}/permisos", {"permisos": []}, token=ta)[0], 400)


if __name__ == "__main__":
    unittest.main()
