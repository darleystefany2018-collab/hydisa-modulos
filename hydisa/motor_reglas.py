"""Motor de Reglas (MR-01 a MR-06). Núcleo de HYDISA, sin IA ni diagnósticos (RN-15).

Cada método corresponde a una regla del documento:
  MR-02 clasificar -> MR-03 priorizar -> MR-04 seleccionar -> MR-05 construir.
"""
import unicodedata

from .modelos import ItemRuta

# Palabras clave por categoría de bienestar (en el proyecto real vienen de la BD).
PALABRAS_CLAVE = {
    "Físico":    ["sueño", "descanso", "movimiento", "energía física", "hidratación"],
    "Emocional": ["estrés", "ansiedad", "emoción", "ánimo", "calma"],
    "Mental":    ["concentración", "enfoque", "memoria", "claridad", "mente"],
    "Energético": ["frecuencia", "armonía", "equilibrio", "coherencia", "vitalidad"],
}

ACTIVIDADES = {
    "Físico": ["Camina 20 minutos al aire libre.", "Establece una hora fija para dormir."],
    "Emocional": ["Practica 5 minutos de respiración consciente.", "Escribe tres cosas que agradeces hoy."],
    "Mental": ["Haz una pausa de 10 minutos sin pantallas.", "Dedica 15 minutos a una lectura tranquila."],
    "Energético": ["Dedica un momento del día a la meditación.", "Mantén una rutina de descanso constante."],
}


def normalizar(texto):
    """Pasa a minúsculas y quita las tildes: 'Estrés' -> 'estres'."""
    descompuesto = unicodedata.normalize("NFD", texto.lower())
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")


class MotorReglas:
    def palabras_detectadas(self, texto):
        """Devuelve qué palabras clave aparecen y cuántas veces, por categoría.

        Ejemplo: {'Emocional': {'estrés': 2, 'ansiedad': 1}}
        Funciona con o sin tildes y con mayúsculas o minúsculas.
        """
        texto = normalizar(texto)
        encontradas = {}
        for categoria, palabras in PALABRAS_CLAVE.items():
            for palabra in palabras:
                veces = texto.count(normalizar(palabra))
                if veces:
                    encontradas.setdefault(categoria, {})[palabra] = veces
        return encontradas

    def clasificar(self, texto):
        """MR-02: cuenta cuántas veces aparece cada categoría en el texto."""
        return {categoria: sum(palabras.values())
                for categoria, palabras in self.palabras_detectadas(texto).items()}

    def priorizar(self, conteo):
        """MR-03: de mayor a menor frecuencia."""
        return sorted(conteo, key=conteo.get, reverse=True)

    def seleccionar(self, categoria):
        """MR-04: actividades asociadas a una categoría."""
        return ACTIVIDADES.get(categoria, [])

    def construir_ruta(self, texto):
        """MR-05: arma la ruta completa."""
        ruta = []
        for prioridad, categoria in enumerate(self.priorizar(self.clasificar(texto)), start=1):
            for actividad in self.seleccionar(categoria):
                ruta.append(ItemRuta(categoria, prioridad, actividad))
        return ruta
