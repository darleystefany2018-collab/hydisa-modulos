"""Acceso a la base de datos (SQLite).

Clase `BaseDatos`: abre la conexión y crea las tablas.
Se usan consultas parametrizadas (?) para evitar inyección SQL.
Para pasar a PostgreSQL basta con reemplazar sqlite3 por psycopg2 y '?' por '%s'.
"""
import sqlite3
from pathlib import Path

ESQUEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre        TEXT    NOT NULL,
    correo        TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    rol           TEXT    NOT NULL DEFAULT 'usuario',
    activo        INTEGER NOT NULL DEFAULT 1,
    creado_en     TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS reportes (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id     INTEGER NOT NULL REFERENCES usuarios(id),
    nombre_archivo TEXT    NOT NULL,
    hash_sha256    TEXT    NOT NULL,
    texto          TEXT    NOT NULL,
    creado_en      TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (usuario_id, hash_sha256)          -- RNF13: un análisis por PDF
);
CREATE TABLE IF NOT EXISTS rutas (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    reporte_id INTEGER NOT NULL REFERENCES reportes(id),
    categoria  TEXT    NOT NULL,
    prioridad  INTEGER NOT NULL,
    actividad  TEXT    NOT NULL,
    cumplida   INTEGER NOT NULL DEFAULT 0
);
"""


class BaseDatos:
    def __init__(self, ruta=":memory:"):
        if ruta != ":memory:":
            Path(ruta).parent.mkdir(parents=True, exist_ok=True)
        self.conexion = sqlite3.connect(str(ruta))
        self.conexion.row_factory = sqlite3.Row
        self.conexion.execute("PRAGMA foreign_keys = ON")
        self.conexion.executescript(ESQUEMA)

    def ejecutar(self, sql, parametros=()):
        """INSERT/UPDATE/DELETE. Devuelve el id de la fila creada."""
        cursor = self.conexion.execute(sql, parametros)
        self.conexion.commit()
        return cursor.lastrowid

    def consultar(self, sql, parametros=()):
        """SELECT que devuelve una lista de filas."""
        return self.conexion.execute(sql, parametros).fetchall()

    def consultar_uno(self, sql, parametros=()):
        """SELECT que devuelve una sola fila (o None)."""
        return self.conexion.execute(sql, parametros).fetchone()

    def cerrar(self):
        self.conexion.close()