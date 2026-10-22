"""Prueba la conexión a la base de datos y crea las tablas si no existen."""
from hydisa.base_datos import BaseDatos

bd = BaseDatos("datos/hydisa.db")
print("Usando:", "PostgreSQL (nube)" if bd.es_postgres else "SQLite (local)")
filas = bd.consultar("SELECT COUNT(*) AS total FROM usuarios")
print("Usuarios en la base:", filas[0]["total"])
bd.cerrar()