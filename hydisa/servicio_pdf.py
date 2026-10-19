"""RF04 Cargar PDF - RF05 Validar formato - RF06 Extraer información.

Reglas: RN-02 (solo PDF), RN-04 (no dañado y legible), RNF14 (máx. 10 MB).
"""
import hashlib
from pathlib import Path

from .config import TAMANO_MAXIMO_MB
from .excepciones import ArchivoInvalidoError

try:                                # Stack de HYDISA: PyMuPDF
    import fitz                     # type: ignore
except ImportError:                 # Alternativa si no está instalado
    fitz = None
    from pypdf import PdfReader


class ServicioPDF:
    def validar(self, ruta):
        ruta = Path(ruta)
        if ruta.suffix.lower() != ".pdf":
            raise ArchivoInvalidoError("Solo se aceptan archivos .pdf.")
        if not ruta.is_file():
            raise ArchivoInvalidoError("El archivo no existe.")
        if ruta.stat().st_size > TAMANO_MAXIMO_MB * 1024 * 1024:
            raise ArchivoInvalidoError(f"El archivo supera {TAMANO_MAXIMO_MB} MB.")
        with open(ruta, "rb") as f:
            if f.read(5) != b"%PDF-":
                raise ArchivoInvalidoError("El archivo no es un PDF real.")

    def extraer_texto(self, ruta):
        try:
            if fitz is not None:
                with fitz.open(str(ruta)) as doc:
                    texto = "\n".join(p.get_text() for p in doc)
            else:
                texto = "\n".join(p.extract_text() or "" for p in PdfReader(str(ruta)).pages)
        except Exception as error:
            raise ArchivoInvalidoError(f"El PDF está dañado: {error}") from error
        if not texto.strip():
            raise ArchivoInvalidoError("El PDF no contiene texto legible (¿es escaneado?).")
        return texto

    @staticmethod
    def calcular_hash(ruta):
        return hashlib.sha256(Path(ruta).read_bytes()).hexdigest()