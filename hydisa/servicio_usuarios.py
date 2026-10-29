"""RF01 Registrar usuario - RF02 Autenticar usuarios (RN-01, RN-14) - control de permisos.

Equivale al pseudocódigo del login, pero en POO y guardando la clave con hash.
Se usa scrypt (librería estándar). En el stack final puede cambiarse por bcrypt.
"""
import hashlib
import hmac
import os
import re

from .config import CORREO_ADMIN, LARGO_MINIMO_CLAVE, PERMISOS
from .excepciones import CredencialesError, DatosInvalidosError
from .modelos import Usuario
from .tiempo import a_iso_utc

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

    # ---------- permisos y conversión de filas ----------
    @staticmethod
    def _validar_permisos(permisos):
        """Devuelve la lista limpia (sin repetidos, en el orden del catálogo) o falla si hay claves inventadas."""
        if permisos is None:
            return list(PERMISOS)
        if not isinstance(permisos, (list, tuple)):
            raise DatosInvalidosError("Los permisos deben ser una lista.")
        desconocidos = [p for p in permisos if p not in PERMISOS]
        if desconocidos:
            raise DatosInvalidosError(f"Permiso no válido: {desconocidos[0]}")
        return [p for p in PERMISOS if p in permisos]

    @staticmethod
    def _a_usuario(fila):
        permisos = [p for p in (fila["permisos"] or "").split(",") if p in PERMISOS]
        usuario = Usuario(fila["id"], fila["nombre"], fila["correo"], fila["rol"], permisos)
        if usuario.es_administrador():
            usuario.permisos = []                   # cuenta de gestión: sin funciones de acompañamiento
        return usuario

    # ---------- casos de uso ----------
    def registrar(self, nombre, correo, clave, rol="usuario", permisos=None):
        nombre, correo = nombre.strip(), correo.strip().lower()
        if not nombre or not correo or not clave:
            raise DatosInvalidosError("Todos los campos son obligatorios.")
        if not PATRON_CORREO.match(correo):
            raise DatosInvalidosError("El correo no tiene un formato válido.")
        if len(clave) < LARGO_MINIMO_CLAVE:
            raise DatosInvalidosError(
                f"La contraseña debe tener mínimo {LARGO_MINIMO_CLAVE} caracteres.")
        if rol == "administrador" and correo != CORREO_ADMIN:
            raise DatosInvalidosError("Solo la cuenta oficial puede ser administradora.")
        permisos = [] if rol == "administrador" else self._validar_permisos(permisos)
        if self.bd.consultar_uno("SELECT id FROM usuarios WHERE correo = ?", (correo,)):
            raise DatosInvalidosError("Ese correo ya está registrado.")
        nuevo_id = self.bd.ejecutar(
            "INSERT INTO usuarios (nombre, correo, password_hash, rol, permisos) VALUES (?,?,?,?,?)",
            (nombre, correo, self._cifrar(clave), rol, ",".join(permisos)))
        return Usuario(nuevo_id, nombre, correo, rol, permisos)

    def iniciar_sesion(self, correo, clave):
        fila = self.bd.consultar_uno(
            "SELECT * FROM usuarios WHERE correo = ? AND activo = 1",
            (correo.strip().lower(),))
        if fila is None or not self._verificar(clave, fila["password_hash"]):
            # Mismo mensaje en ambos casos: no revelamos si el correo existe.
            raise CredencialesError("Usuario o contraseña incorrectos.")
        return self._a_usuario(fila)

    # ---------- administración (el servidor solo las llama tras comprobar el rol) ----------
    def obtener(self, usuario_id, solo_activos=False):
        """Lee el usuario actual desde la BD (así un cambio de permisos rige de inmediato)."""
        sql = "SELECT * FROM usuarios WHERE id = ?" + (" AND activo = 1" if solo_activos else "")
        fila = self.bd.consultar_uno(sql, (usuario_id,))
        return self._a_usuario(fila) if fila else None

    def listar(self):
        filas = self.bd.consultar(
            """SELECT u.id, u.nombre, u.correo, u.rol, u.activo, u.permisos, u.creado_en,
                      (SELECT COUNT(*) FROM reportes r WHERE r.usuario_id = u.id) AS n_reportes
               FROM usuarios u ORDER BY u.id""")
        return [{**self._a_usuario(f).__dict__, "activo": bool(f["activo"]),
                 "creado_en": a_iso_utc(f["creado_en"]), "n_reportes": f["n_reportes"]} for f in filas]

    def actualizar_permisos(self, usuario_id, permisos):
        destino = self.obtener(usuario_id)
        if destino is None:
            raise IndexError("Ese usuario no existe.")
        if destino.es_administrador():
            raise DatosInvalidosError("Los permisos del administrador no se pueden modificar.")
        permisos = self._validar_permisos(permisos)
        self.bd.ejecutar("UPDATE usuarios SET permisos = ? WHERE id = ?", (",".join(permisos), usuario_id))
        destino.permisos = permisos
        return destino

    def asegurar_administrador(self, clave):
        """Crea o repara la cuenta de administrador usando la clave secreta del .env (ADMIN_CLAVE).

        Es la única forma de obtener el rol: nadie puede pedirlo desde la API.
        """
        if len(clave) < LARGO_MINIMO_CLAVE:
            raise DatosInvalidosError(f"ADMIN_CLAVE debe tener mínimo {LARGO_MINIMO_CLAVE} caracteres.")
        fila = self.bd.consultar_uno("SELECT * FROM usuarios WHERE correo = ?", (CORREO_ADMIN,))
        if fila is None:
            self.registrar("Administrador HYDISA", CORREO_ADMIN, clave, rol="administrador")
            return "creada"
        if (fila["rol"] == "administrador" and fila["activo"]
                and self._verificar(clave, fila["password_hash"])):
            return "sin cambios"
        self.bd.ejecutar(
            "UPDATE usuarios SET rol = 'administrador', activo = 1, password_hash = ?, permisos = ? WHERE id = ?",
            (self._cifrar(clave), "", fila["id"]))
        return "actualizada"
