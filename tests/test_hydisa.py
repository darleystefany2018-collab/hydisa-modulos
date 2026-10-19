import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reportlab.pdfgen import canvas

from hydisa.base_datos import BaseDatos
from hydisa.excepciones import ArchivoInvalidoError, CredencialesError, DatosInvalidosError
from hydisa.motor_reglas import MotorReglas
from hydisa.servicio_reportes import ServicioReportes
from hydisa.servicio_usuarios import ServicioUsuarios


def crear_pdf(ruta, lineas):
    c = canvas.Canvas(str(ruta))
    for n, linea in enumerate(lineas):
        c.drawString(72, 780 - 20 * n, linea)
    c.save()


class PruebasHydisa(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.bd = BaseDatos()
        self.usuarios = ServicioUsuarios(self.bd)
        self.reportes = ServicioReportes(self.bd)
        self.ana = self.usuarios.registrar("Ana", "ana@mail.com", "clave12345")
        self.pdf = self.tmp / "healy.pdf"
        crear_pdf(self.pdf, ["Reporte Healy", "estres y ansiedad altos", "falta de sueno y descanso",
                             "buscar equilibrio y armonia"])

    def test_registro_y_login(self):
        self.assertEqual(self.usuarios.iniciar_sesion("ANA@mail.com", "clave12345").nombre, "Ana")

    def test_clave_corta_y_correo_repetido(self):
        with self.assertRaises(DatosInvalidosError):
            self.usuarios.registrar("Luis", "luis@mail.com", "123")
        with self.assertRaises(DatosInvalidosError):
            self.usuarios.registrar("Ana2", "ana@mail.com", "otraclave123")

    def test_login_incorrecto(self):
        with self.assertRaises(CredencialesError):
            self.usuarios.iniciar_sesion("ana@mail.com", "mala")

    def test_clave_no_se_guarda_en_texto_plano(self):
        fila = self.bd.consultar_uno("SELECT password_hash FROM usuarios")
        self.assertNotIn("clave12345", fila["password_hash"])

    def test_rechaza_no_pdf(self):
        falso = self.tmp / "nota.txt"
        falso.write_text("hola")
        with self.assertRaises(ArchivoInvalidoError):
            self.reportes.analizar_pdf(self.ana, falso)

    def test_rechaza_pdf_danado(self):
        roto = self.tmp / "roto.pdf"
        roto.write_bytes(b"%PDF-1.4 basura")
        with self.assertRaises(ArchivoInvalidoError):
            self.reportes.analizar_pdf(self.ana, roto)

    def test_flujo_completo(self):
        rid = self.reportes.analizar_pdf(self.ana, self.pdf)
        ruta = self.reportes.obtener_ruta(self.ana, rid)
        self.assertTrue(ruta)
        self.reportes.marcar_cumplida(self.ana, rid, 1)
        self.assertGreater(self.reportes.progreso(self.ana, rid), 0)
        salida = self.reportes.exportar_pdf(self.ana, rid, self.tmp)
        self.assertTrue(salida.exists())

    def test_pdf_duplicado(self):
        self.reportes.analizar_pdf(self.ana, self.pdf)
        with self.assertRaises(ArchivoInvalidoError):
            self.reportes.analizar_pdf(self.ana, self.pdf)

    def test_aislamiento_entre_usuarios(self):
        rid = self.reportes.analizar_pdf(self.ana, self.pdf)
        otro = self.usuarios.registrar("Beto", "beto@mail.com", "clave12345")
        self.assertEqual(self.reportes.obtener_ruta(otro, rid), [])

    def test_palabras_clave_con_y_sin_tilde(self):
        m = MotorReglas()
        con_tilde = m.palabras_detectadas("Mucho estrés y poco sueño")
        sin_tilde = m.palabras_detectadas("MUCHO ESTRES Y POCO SUENO")
        self.assertEqual(con_tilde, sin_tilde)
        self.assertEqual(con_tilde["Emocional"], {"estrés": 1})

    def test_motor_prioriza(self):
        m = MotorReglas()
        self.assertEqual(m.priorizar({"Mental": 1, "Emocional": 5}), ["Emocional", "Mental"])


if __name__ == "__main__":
    unittest.main()