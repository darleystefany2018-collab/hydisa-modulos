"""RF04/RF10 guardar reporte y ruta - RF13 cumplimiento - RF15 historial - RF16 exportar."""
import sqlite3
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib import colors

from .config import CARPETA_REPORTES
from .excepciones import ArchivoInvalidoError
from .modelos import ItemRuta
from .motor_reglas import MotorReglas
from .servicio_pdf import ServicioPDF

AVISO = ("HYDISA no emite diagnósticos, tratamientos ni recomendaciones médicas. "
         "La información tiene un propósito educativo y de bienestar.")


class ServicioReportes:
    def __init__(self, bd, servicio_pdf=None, motor=None):
        self.bd = bd
        self.pdf = servicio_pdf or ServicioPDF()
        self.motor = motor or MotorReglas()

    def analizar_pdf(self, usuario, ruta_pdf):
        """Valida -> extrae -> aplica reglas -> guarda en la BD. Devuelve el id del reporte."""
        self.pdf.validar(ruta_pdf)
        texto = self.pdf.extraer_texto(ruta_pdf)
        try:
            reporte_id = self.bd.ejecutar(
                "INSERT INTO reportes (usuario_id, nombre_archivo, hash_sha256, texto) VALUES (?,?,?,?)",
                (usuario.id, Path(ruta_pdf).name, self.pdf.calcular_hash(ruta_pdf), texto))
        except sqlite3.IntegrityError as error:
            raise ArchivoInvalidoError("Ya analizaste este mismo PDF antes.") from error
        for item in self.motor.construir_ruta(texto):
            self.bd.ejecutar(
                "INSERT INTO rutas (reporte_id, categoria, prioridad, actividad) VALUES (?,?,?,?)",
                (reporte_id, item.categoria, item.prioridad, item.actividad))
        return reporte_id

    def historial(self, usuario):
        """RF15 / RNF03: solo los reportes del propio usuario."""
        return self.bd.consultar(
            "SELECT id, nombre_archivo, creado_en FROM reportes WHERE usuario_id = ? ORDER BY id DESC",
            (usuario.id,))

    def obtener_ruta(self, usuario, reporte_id):
        filas = self.bd.consultar(
            """SELECT r.* FROM rutas r JOIN reportes p ON p.id = r.reporte_id
               WHERE p.id = ? AND p.usuario_id = ? ORDER BY r.prioridad, r.id""",
            (reporte_id, usuario.id))
        return [ItemRuta(f["categoria"], f["prioridad"], f["actividad"], bool(f["cumplida"]))
                for f in filas]

    def marcar_cumplida(self, usuario, reporte_id, posicion):
        """RF13: marca la actividad número `posicion` (desde 1) como cumplida."""
        filas = self.bd.consultar(
            """SELECT r.id FROM rutas r JOIN reportes p ON p.id = r.reporte_id
               WHERE p.id = ? AND p.usuario_id = ? ORDER BY r.prioridad, r.id""",
            (reporte_id, usuario.id))
        if not 1 <= posicion <= len(filas):
            raise IndexError("Esa actividad no existe.")
        self.bd.ejecutar("UPDATE rutas SET cumplida = 1 WHERE id = ?", (filas[posicion - 1]["id"],))

    def progreso(self, usuario, reporte_id):
        """RF14 / RN-12: porcentaje de actividades cumplidas."""
        ruta = self.obtener_ruta(usuario, reporte_id)
        return round(100 * sum(i.cumplida for i in ruta) / len(ruta)) if ruta else 0

    def exportar_pdf(self, usuario, reporte_id, carpeta=CARPETA_REPORTES):
        """RF16: genera el PDF con la ruta personalizada usando ReportLab."""
        ruta = self.obtener_ruta(usuario, reporte_id)
        if not ruta:
            raise ArchivoInvalidoError("No hay ruta para exportar.")
        Path(carpeta).mkdir(parents=True, exist_ok=True)
        destino = Path(carpeta) / f"ruta_bienestar_{reporte_id}.pdf"
        estilos = getSampleStyleSheet()
        datos = [["Prioridad", "Categoría", "Actividad", "Estado"]]
        datos += [[i.prioridad, i.categoria, Paragraph(i.actividad, estilos["BodyText"]),
                   "Cumplida" if i.cumplida else "Pendiente"] for i in ruta]
        tabla = Table(datos, colWidths=[60, 80, 270, 70], repeatRows=1)
        tabla.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E7D6B")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        SimpleDocTemplate(str(destino), pagesize=A4).build([
            Paragraph("HYDISA - Ruta personalizada de bienestar", estilos["Title"]),
            Paragraph(f"Usuario: {usuario.nombre} | Reporte N.º {reporte_id} | "
                      f"Progreso: {self.progreso(usuario, reporte_id)}%", estilos["Normal"]),
            Spacer(1, 14), tabla, Spacer(1, 14), Paragraph(AVISO, estilos["Italic"])])
        return destino