"""Acceso a la base de datos.

Si existe la variable DATABASE_URL (archivo .env) se usa PostgreSQL en la nube
(Supabase). Si no existe, se usa SQLite local. Las pruebas usan SQLite en memoria.
Se usan consultas parametrizadas (?) para evitar inyección SQL.
"""
import os
import sqlite3
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:          # si no está instalado, simplemente no lee el .env
    pass

ESQUEMA_SQLITE = """
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
    UNIQUE (usuario_id, hash_sha256)
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

ESQUEMA_POSTGRES = """
CREATE TABLE IF NOT EXISTS usuarios (
    id            SERIAL PRIMARY KEY,
    nombre        TEXT      NOT NULL,
    correo        TEXT      NOT NULL UNIQUE,
    password_hash TEXT      NOT NULL,
    rol           TEXT      NOT NULL DEFAULT 'usuario',
    activo        INTEGER   NOT NULL DEFAULT 1,
    creado_en     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS reportes (
    id             SERIAL PRIMARY KEY,
    usuario_id     INTEGER   NOT NULL REFERENCES usuarios(id),
    nombre_archivo TEXT      NOT NULL,
    hash_sha256    TEXT      NOT NULL,
    texto          TEXT      NOT NULL,
    creado_en      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (usuario_id, hash_sha256)
);
CREATE TABLE IF NOT EXISTS rutas (
    id         SERIAL PRIMARY KEY,
    reporte_id INTEGER NOT NULL REFERENCES reportes(id),
    categoria  TEXT    NOT NULL,
    prioridad  INTEGER NOT NULL,
    actividad  TEXT    NOT NULL,
    cumplida   INTEGER NOT NULL DEFAULT 0
);
"""


class ErrorIntegridad(Exception):
    """Se intentó guardar un dato repetido o inválido (por ejemplo, un PDF duplicado)."""


class BaseDatos:
    def __init__(self, ruta=":memory:"):
        url = os.getenv("DATABASE_URL")
        self.es_postgres = bool(url) and ruta != ":memory:"
        if self.es_postgres:
            import psycopg
            from psycopg.rows import dict_row
            self.conexion = psycopg.connect(url, autocommit=True, row_factory=dict_row)
            self.conexion.execute(ESQUEMA_POSTGRES)
            self._errores_integridad = (psycopg.errors.IntegrityError,)
        else:
            if ruta != ":memory:":
                Path(ruta).parent.mkdir(parents=True, exist_ok=True)
            self.conexion = sqlite3.connect(str(ruta), check_same_thread=False)   # el servidor atiende de a una petición
            self.conexion.row_factory = sqlite3.Row
            self.conexion.execute("PRAGMA foreign_keys = ON")
            self.conexion.executescript(ESQUEMA_SQLITE)
            self._errores_integridad = (sqlite3.IntegrityError,)

    def _preparar(self, sql):
        """PostgreSQL usa %s en lugar de ? para los parámetros."""
        return sql.replace("?", "%s") if self.es_postgres else sql

    def ejecutar(self, sql, parametros=()):
        """INSERT/UPDATE/DELETE. En un INSERT devuelve el id de la fila creada."""
        sql = self._preparar(sql)
        try:
            if self.es_postgres:
                if sql.lstrip().upper().startswith("INSERT"):
                    return self.conexion.execute(sql + " RETURNING id", parametros).fetchone()["id"]
                self.conexion.execute(sql, parametros)
                return None
            cursor = self.conexion.execute(sql, parametros)
            self.conexion.commit()
            return cursor.lastrowid
        except self._errores_integridad as error:
            raise ErrorIntegridad(str(error)) from error

    def consultar(self, sql, parametros=()):
        """SELECT que devuelve una lista de filas."""
        return self.conexion.execute(self._preparar(sql), parametros).fetchall()

    def consultar_uno(self, sql, parametros=()):
        """SELECT que devuelve una sola fila (o None)."""
        return self.conexion.execute(self._preparar(sql), parametros).fetchone()

    def cerrar(self):
        self.conexion.close()
