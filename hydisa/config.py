"""Configuración central. Aquí viven las constantes para no repetirlas."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
RUTA_BD = RAIZ / "datos" / "hydisa.db"
CARPETA_REPORTES = RAIZ / "datos" / "reportes"
TAMANO_MAXIMO_MB = 10          # RNF14: límite de tamaño de archivo
LARGO_MINIMO_CLAVE = 8         # RF01: requisitos mínimos de seguridad

# ---------- Control de acceso ----------
# Única cuenta con rol de administrador. Se valida SIEMPRE en el servidor.
CORREO_ADMIN = "hydisa123@gmail.com"
# Catálogo de permisos que el administrador puede dar a cada usuario (clave -> descripción).
# La clave es lo que se guarda en la base de datos y se revisa en cada solicitud.
PERMISOS = {
    "cargar_pdf": "Cargar y analizar PDF",
    "ver_reportes": "Ver su historial, ruta y palabras clave",
    "marcar_actividades": "Marcar actividades como cumplidas",
    "exportar_pdf": "Exportar su ruta en PDF",
}
