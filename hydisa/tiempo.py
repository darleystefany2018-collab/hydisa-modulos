"""Fechas y horas: se guardan en UTC y el navegador las muestra en la hora local de cada persona."""
from datetime import datetime, timezone


def marca_utc():
    """Instante actual como texto ISO en UTC, por ejemplo 2026-10-23T15:44:05Z."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def a_iso_utc(valor):
    """Convierte lo que devuelve la BD (SQLite o PostgreSQL, ambos en UTC) al mismo formato ISO con Z."""
    if not valor:
        return None
    return str(valor).replace(" ", "T")[:19] + "Z"
