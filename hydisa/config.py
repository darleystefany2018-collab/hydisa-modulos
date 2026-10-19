"""Configuración central. Aquí viven las constantes para no repetirlas."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
RUTA_BD = RAIZ / "datos" / "hydisa.db"
CARPETA_REPORTES = RAIZ / "datos" / "reportes"
TAMANO_MAXIMO_MB = 10          # RNF14: límite de tamaño de archivo
LARGO_MINIMO_CLAVE = 8         # RF01: requisitos mínimos de seguridad