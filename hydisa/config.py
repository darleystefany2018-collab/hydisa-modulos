"""Configuración central. Aquí viven las constantes para no repetirlas."""
import os
from datetime import datetime
from pathlib import Path

try:                                  # lee el .env aquí también: así HORA_APERTURA, etc. se pueden cambiar sin tocar código
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

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

# ---------- Agenda de acompañamiento y SOS ----------
DURACION_MAXIMA_SESION_MIN = 30    # una sesión nunca dura más de 30 minutos
DURACION_MINIMA_SESION_MIN = 5     # evita bloques de 0 o 1 minuto por error de digitación


def _hora_config(nombre, defecto):
    """Lee una hora HH:MM del .env (o usa la de por defecto) y falla con un mensaje claro si está mal escrita."""
    valor = os.getenv(nombre, defecto).strip()
    try:
        return datetime.strptime(valor, "%H:%M").strftime("%H:%M")
    except ValueError:
        raise ValueError(f"{nombre} debe tener formato HH:MM (por ejemplo 08:00), no '{valor}'.") from None


# Horario de operación: la disponibilidad solo se puede publicar dentro de este rango.
HORA_APERTURA = _hora_config("HORA_APERTURA", "08:00")
HORA_CIERRE = _hora_config("HORA_CIERRE", "18:00")
# Duración estándar de cada cita: un rango publicado se divide en espacios de esta duración.
DURACION_SESION_MIN = int(os.getenv("DURACION_SESION_MIN", "30"))

if not HORA_APERTURA < HORA_CIERRE:
    raise ValueError("HORA_APERTURA debe ser anterior a HORA_CIERRE.")
if not DURACION_MINIMA_SESION_MIN <= DURACION_SESION_MIN <= DURACION_MAXIMA_SESION_MIN:
    raise ValueError(f"DURACION_SESION_MIN debe estar entre {DURACION_MINIMA_SESION_MIN} y {DURACION_MAXIMA_SESION_MIN}.")
LARGO_MAXIMO_TEMA = 80             # texto libre del tema al reservar
LARGO_MAXIMO_SOS = 300             # mensaje opcional de una solicitud SOS
