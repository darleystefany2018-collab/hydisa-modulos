"""RF01 Registrar usuario - RF02 Autenticar usuarios (RN-01, RN-14).

Equivale al pseudocódigo del login, pero en POO y guardando la clave con hash.
Se usa scrypt (librería estándar). En el stack final puede cambiarse por bcrypt.
"""
import hashlib
import hmac
import os
import re

from .config import LARGO_MINIMO_CLAVE
from .excepciones import CredencialesError, DatosInvalidosError
from .modelos import Usuario

PATRON_CORREO = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$")


class ServicioUsuarios:
    def __init__(self, bd):
        self.bd = bd

    # ---------- utilidades de contraseña ----------
    @staticmethod
    def _cifrar(clave):
        sal = os.urandom(16)
        derivada = hashlib.scrypt(clave.encode(), salt=sal, n=2**14, r=8, p=1)
        return sal.hex() + "$" + derivada.hex()

    @staticmethod
    def _verificar(clave, guardado):
        sal_hex, hash_hex = guardado.split("$")
        derivada = hashlib.scrypt(clave.encode(), salt=bytes.fromhex(sal_hex),
                                  n=2**14, r=8, p=1)
        return hmac.compare_digest(derivada.hex(), hash_hex)

    # ---------- casos de uso ----------
    def registrar(self, nombre, correo, clave, rol="usuario"):
        nombre, correo = nombre.strip(), correo.strip().lower()
        if not nombre or not correo or not clave:
            raise DatosInvalidosError("Todos los campos son obligatorios.")
        if not PATRON_CORREO.match(correo):
            raise DatosInvalidosError("El correo no tiene un formato válido.")
        if len(clave) < LARGO_MINIMO_CLAVE:
            raise DatosInvalidosError(
                f"La contraseña debe tener mínimo {LARGO_MINIMO_CLAVE} caracteres.")
        if self.bd.consultar_uno("SELECT id FROM usuarios WHERE correo = ?", (correo,)):
            raise DatosInvalidosError("Ese correo ya está registrado.")
        nuevo_id = self.bd.ejecutar(
            "INSERT INTO usuarios (nombre, correo, password_hash, rol) VALUES (?,?,?,?)",
            (nombre, correo, self._cifrar(clave), rol))
        return Usuario(nuevo_id, nombre, correo, rol)

    def iniciar_sesion(self, correo, clave):
        fila = self.bd.consultar_uno(
            "SELECT * FROM usuarios WHERE correo = ? AND activo = 1",
            (correo.strip().lower(),))
        if fila is None or not self._verificar(clave, fila["password_hash"]):
            # Mismo mensaje en ambos casos: no revelamos si el correo existe.
            raise CredencialesError("Usuario o contraseña incorrectos.")
        return Usuario(fila["id"], fila["nombre"], fila["correo"], fila["rol"])