"""Pruebas de la API web: usan el servidor real con una base SQLite temporal."""
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import date, timedelta
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

    def entrar(self, correo="ana@correo.com", permisos=None, nombre="Ana"):
        self.crear(correo, permisos, nombre)
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


    # ---------- roles: el administrador solo gestiona ----------
    def test_administrador_bloqueado_en_acompanamiento(self):
        ta = self.token_admin()
        yo = self.llamar("GET", "/api/yo", token=ta)[1]["usuario"]
        self.assertEqual((yo["es_admin"], yo["permisos"]), (True, []))
        for metodo, ruta, datos in [("GET", "/api/reportes", None), ("GET", "/api/reportes/1/ruta", None),
                                    ("GET", "/api/reportes/1/palabras", None), ("GET", "/api/reportes/1/pdf", None),
                                    ("POST", "/api/reportes/1/actividades/1/cumplir", None),
                                    ("GET", "/api/sesiones", None), ("POST", "/api/sesiones/1/reservar", {}),
                                    ("POST", "/api/sesiones/1/cancelar", None),
                                    ("GET", "/api/sos", None), ("POST", "/api/sos", {"mensaje": "hola"})]:
            self.assertEqual(self.llamar(metodo, ruta, datos, token=ta)[0], 403, ruta)
        carga = dict(crudo=self.pdf.read_bytes(), token=ta, cabeceras={"X-Nombre-Archivo": "admin.pdf"})
        self.assertEqual(self.llamar("POST", "/api/reportes", **carga)[0], 403)
        self.assertEqual(self.llamar("GET", "/api/admin/usuarios", token=ta)[0], 200)      # sus funciones siguen

    def test_usuario_no_entra_a_agenda_ni_alertas_de_gestion(self):
        t = self.entrar("sinadmin@correo.com")
        for metodo, ruta, datos in [("GET", "/api/admin/agenda", None),
                                    ("POST", "/api/admin/agenda", {"fecha": "2030-01-01", "inicio": "09:00", "fin": "09:30"}),
                                    ("POST", "/api/admin/agenda/1/eliminar", None),
                                    ("GET", "/api/admin/alertas", None), ("POST", "/api/admin/alertas/1/atender", None)]:
            self.assertEqual(self.llamar(metodo, ruta, datos, token=t)[0], 403, ruta)
            self.assertEqual(self.llamar(metodo, ruta, datos)[0], 401, ruta)              # sin sesión

    # ---------- agenda ----------
    def bloque(self, token, hora_ini, hora_fin, dia=1):
        fecha = (date.today() + timedelta(days=dia)).isoformat()
        return self.llamar("POST", "/api/admin/agenda", {"fecha": fecha, "inicio": hora_ini, "fin": hora_fin}, token=token)

    def test_agenda_publicar_ver_reservar_y_cancelar(self):
        ta, t1, t2 = self.token_admin(), self.entrar("ag1@correo.com"), self.entrar("ag2@correo.com")
        codigo, r = self.bloque(ta, "08:00", "08:30", dia=3)
        self.assertEqual((codigo, r["bloque"]["minutos"]), (201, 30))
        bid = r["bloque"]["id"]
        self.assertIn(bid, [b["id"] for b in self.llamar("GET", "/api/sesiones", token=t1)[1]["disponibles"]])
        self.assertEqual(self.llamar("POST", f"/api/sesiones/{bid}/reservar", {"tema": "Hábitos de descanso"}, token=t1)[0], 200)
        # ocupado: ya no se ofrece y reservar de nuevo da 409
        self.assertNotIn(bid, [b["id"] for b in self.llamar("GET", "/api/sesiones", token=t2)[1]["disponibles"]])
        self.assertEqual(self.llamar("POST", f"/api/sesiones/{bid}/reservar", {}, token=t2)[0], 409)
        self.assertEqual(self.llamar("POST", f"/api/sesiones/{bid}/cancelar", token=t2)[0], 404)   # no es suya
        # el administrador ve quién reservó
        agenda = self.llamar("GET", "/api/admin/agenda", token=ta)[1]
        fila = next(b for b in agenda["bloques"] if b["id"] == bid)
        self.assertEqual((fila["reservado"], fila["usuario"]["correo"]), (True, "ag1@correo.com"))
        self.assertEqual(agenda["duracion_maxima"], 30)
        self.assertEqual(self.llamar("POST", f"/api/admin/agenda/{bid}/eliminar", token=ta)[0], 409)  # reservado
        self.assertEqual(self.llamar("POST", f"/api/sesiones/{bid}/cancelar", token=t1)[0], 200)
        self.assertIn(bid, [b["id"] for b in self.llamar("GET", "/api/sesiones", token=t2)[1]["disponibles"]])
        self.assertEqual(self.llamar("POST", f"/api/admin/agenda/{bid}/eliminar", token=ta)[0], 200)

    def test_agenda_solapes_y_formatos_en_la_api(self):
        ta = self.token_admin()
        self.assertEqual(self.bloque(ta, "09:30", "09:00", dia=4)[0], 400)      # al revés
        self.assertEqual(self.bloque(ta, "09:00", "09:30", dia=4)[0], 201)
        self.assertEqual(self.bloque(ta, "09:15", "09:45", dia=4)[0], 409)      # se cruza
        self.assertEqual(self.bloque(ta, "09:00", "09:30", dia=-1)[0], 400)     # ayer
        self.assertEqual(self.llamar("POST", "/api/admin/agenda", {"fecha": "x"}, token=ta)[0], 400)

    def test_admin_cancela_y_reprograma_citas_por_la_api(self):
        ta, t1, t2 = self.token_admin(), self.entrar("ag4@correo.com"), self.entrar("ag5@correo.com")
        a = self.bloque(ta, "08:00", "08:30", dia=6)[1]["bloque"]["id"]
        b = self.bloque(ta, "08:30", "09:00", dia=6)[1]["bloque"]["id"]
        self.llamar("POST", f"/api/sesiones/{a}/reservar", {"tema": "Estrés"}, token=t1)
        # un usuario normal no puede (403) y falta el horario nuevo (400)
        self.assertEqual(self.llamar("POST", f"/api/admin/agenda/{a}/cancelar", token=t1)[0], 403)
        self.assertEqual(self.llamar("POST", f"/api/admin/agenda/{a}/reprogramar", {"nuevo_id": b}, token=t1)[0], 403)
        self.assertEqual(self.llamar("POST", f"/api/admin/agenda/{a}/reprogramar", {}, token=ta)[0], 400)
        # reprogramar: el nuevo queda ocupado y el anterior libre
        codigo, r = self.llamar("POST", f"/api/admin/agenda/{a}/reprogramar", {"nuevo_id": b}, token=ta)
        self.assertEqual((codigo, r["anterior"]["reservado"], r["nueva"]["reservado"]), (200, False, True))
        libres = [x["id"] for x in self.llamar("GET", "/api/sesiones", token=t2)[1]["disponibles"]]
        self.assertIn(a, libres)
        self.assertNotIn(b, libres)
        self.assertEqual(self.llamar("POST", f"/api/admin/agenda/{a}/reprogramar", {"nuevo_id": b}, token=ta)[0], 409)  # a ya no tiene cita
        # cancelar: vuelve a estar libre
        self.assertEqual(self.llamar("POST", f"/api/admin/agenda/{b}/cancelar", token=ta)[0], 200)
        self.assertEqual(self.llamar("GET", "/api/sesiones", token=t1)[1]["mias"], [])
        self.assertEqual(self.llamar("POST", f"/api/admin/agenda/{b}/cancelar", token=ta)[0], 409)   # ya estaba libre

    def test_reservar_solo_lo_publicado(self):
        t = self.entrar("ag3@correo.com")
        self.assertEqual(self.llamar("POST", "/api/sesiones/987654/reservar", {}, token=t)[0], 404)
        self.assertEqual(self.llamar("POST", "/api/sesiones/1/reservar", {"tema": "x" * 200}, token=t)[0], 400)

    # ---------- SOS ----------
    def test_sos_crea_alerta_visible_para_el_administrador(self):
        ta, t = self.token_admin(), self.entrar("sos1@correo.com", nombre="Sofía")
        codigo, r = self.llamar("POST", "/api/sos", {"mensaje": "Necesito hablar con alguien"}, token=t)
        self.assertEqual((codigo, r["nueva"]), (201, True))
        alertas = self.llamar("GET", "/api/admin/alertas", token=ta)[1]
        mia = next(a for a in alertas["pendientes"] if a["usuario"]["correo"] == "sos1@correo.com")
        self.assertEqual((mia["usuario"]["nombre"], mia["mensaje"]), ("Sofía", "Necesito hablar con alguien"))
        self.assertTrue(mia["creado_en"].endswith("Z"))
        # repetir no duplica
        codigo, r2 = self.llamar("POST", "/api/sos", {}, token=t)
        self.assertEqual((codigo, r2["nueva"], r2["alerta"]["id"]), (200, False, mia["id"]))
        self.assertEqual(self.llamar("GET", "/api/sos", token=t)[1]["pendiente"]["id"], mia["id"])
        # el administrador la marca como atendida
        self.assertEqual(self.llamar("POST", f"/api/admin/alertas/{mia['id']}/atender", token=ta)[0], 200)
        alertas = self.llamar("GET", "/api/admin/alertas", token=ta)[1]
        self.assertNotIn(mia["id"], [a["id"] for a in alertas["pendientes"]])
        self.assertIn(mia["id"], [a["id"] for a in alertas["atendidas"]])
        self.assertIsNone(self.llamar("GET", "/api/sos", token=t)[1]["pendiente"])
        self.assertEqual(self.llamar("POST", "/api/admin/alertas/99999/atender", token=ta)[0], 404)

    def test_sos_exige_sesion_y_valida_el_mensaje(self):
        self.assertEqual(self.llamar("POST", "/api/sos", {})[0], 401)
        t = self.entrar("sos2@correo.com")
        self.assertEqual(self.llamar("POST", "/api/sos", {"mensaje": "x" * 301}, token=t)[0], 400)
        self.assertEqual(self.llamar("POST", "/api/sos", crudo=b"[1,2]", token=t)[0], 400)    # no es un objeto JSON

    # ---------- rangos libres de disponibilidad ----------
    def rango(self, token, dia, inicio=None, fin=None, **extra):
        fecha = (date.today() + timedelta(days=dia)).isoformat()
        return self.llamar("POST", "/api/admin/agenda", {"fecha": fecha, "inicio": inicio, "fin": fin, **extra}, token=token)

    def test_api_rango_de_una_hora_y_de_varias_horas(self):
        ta = self.token_admin()
        codigo, r = self.rango(ta, 10, "09:00", "10:00")
        self.assertEqual(codigo, 201)
        self.assertEqual([(b["inicio"], b["fin"]) for b in r["bloques"]], [("09:00", "09:30"), ("09:30", "10:00")])
        self.assertEqual(r["bloque"]["id"], r["bloques"][0]["id"])               # compatibilidad con el formato anterior
        codigo, r = self.rango(ta, 10, "14:00", "18:00")
        self.assertEqual((codigo, len(r["bloques"])), (201, 8))
        self.assertEqual(r["bloques"][-1]["fin"], "18:00")

    def test_api_todo_el_dia_y_horario_de_operacion(self):
        ta = self.token_admin()
        codigo, r = self.rango(ta, 11, todo_el_dia=True)
        self.assertEqual(codigo, 201)
        self.assertEqual((r["bloques"][0]["inicio"], r["bloques"][-1]["fin"], len(r["bloques"])), ("08:00", "18:00", 20))
        agenda = self.llamar("GET", "/api/admin/agenda", token=ta)[1]
        self.assertEqual((agenda["apertura"], agenda["cierre"], agenda["duracion_sesion"]), ("08:00", "18:00", 30))
        for ini, fin in [("07:30", "09:00"), ("17:00", "18:30"), ("06:00", "07:00"), ("19:00", "20:00")]:
            self.assertEqual(self.rango(ta, 12, ini, fin)[0], 400, (ini, fin))     # fuera de operación
        self.assertEqual(self.rango(ta, 12, "10:00", "10:00")[0], 400)               # fin no posterior
        self.assertEqual(self.rango(ta, 12, "10:00", "09:00")[0], 400)
        self.assertEqual(self.rango(ta, 12, "09:00", "10:00", todo_el_dia="si")[0], 400)

    def test_api_traslape_y_reemplazo(self):
        ta, t = self.token_admin(), self.entrar("rangos@correo.com")
        r = self.rango(ta, 13, "09:00", "11:00")[1]
        ids = [b["id"] for b in r["bloques"]]
        reservado = ids[0]
        self.assertEqual(self.llamar("POST", f"/api/sesiones/{reservado}/reservar", {"tema": "x"}, token=t)[0], 200)
        codigo, e = self.rango(ta, 13, "10:00", "12:00")                              # se cruza: se rechaza
        self.assertEqual(codigo, 409)
        self.assertIn("cruza", e["error"])
        # nada cambió
        bloques = [b for b in self.llamar("GET", "/api/admin/agenda", token=ta)[1]["bloques"] if b["id"] in ids]
        self.assertEqual(len(bloques), 4)
        # con "reemplazar": sustituye lo libre y NO toca la cita reservada
        codigo, r2 = self.rango(ta, 13, "09:00", "11:00", reemplazar=True)
        self.assertEqual((codigo, r2["reemplazados"], r2["conservados"], len(r2["bloques"])), (201, 3, 1, 3))
        agenda = {b["id"]: b for b in self.llamar("GET", "/api/admin/agenda", token=ta)[1]["bloques"]}
        self.assertTrue(agenda[reservado]["reservado"])
        self.assertEqual(agenda[reservado]["usuario"]["correo"], "rangos@correo.com")

    def test_usuario_sigue_viendo_y_reservando_los_espacios_generados(self):
        ta, t = self.token_admin(), self.entrar("rangos2@correo.com")
        ids = [b["id"] for b in self.rango(ta, 14, "09:00", "10:00")[1]["bloques"]]
        visibles = [b["id"] for b in self.llamar("GET", "/api/sesiones", token=t)[1]["disponibles"]]
        self.assertTrue(set(ids) <= set(visibles))
        self.assertEqual(self.llamar("POST", f"/api/sesiones/{ids[1]}/reservar", {}, token=t)[0], 200)
        self.assertEqual(self.rango(None, 14, "09:00", "10:00")[0], 401)
        self.assertEqual(self.rango(t, 14, "11:00", "12:00")[0], 403)                 # un usuario no publica


if __name__ == "__main__":
    unittest.main()
