"""Botón SOS: solicitudes de ayuda de los usuarios y su atención por el administrador.

Decisiones de diseño:
  - Una persona solo puede tener UNA solicitud pendiente a la vez: si vuelve a pulsar SOS
    no se duplica (así nadie inunda al administrador por error).
  - El administrador se entera por actualización periódica de su pantalla (sondeo cada pocos
    segundos), no por notificaciones en tiempo real: es lo más simple con la tecnología actual.
  - HYDISA no es un servicio de emergencias; la pantalla del usuario lo dice claramente.
"""
from .config import LARGO_MAXIMO_SOS
from .excepciones import DatosInvalidosError, PermisoDenegadoError
from .tiempo import a_iso_utc, marca_utc

_CONSULTA = """SELECT a.id, a.usuario_id, a.mensaje, a.creado_en, a.atendida, a.atendida_en, a.atendida_por,
                      u.nombre AS u_nombre, u.correo AS u_correo
               FROM alertas_sos a JOIN usuarios u ON u.id = a.usuario_id"""


class ServicioAlertas:
    def __init__(self, bd):
        self.bd = bd

    @staticmethod
    def _exigir_admin(usuario):
        if not usuario.es_administrador():
            raise PermisoDenegadoError("Solo el administrador ve las alertas.")

    @staticmethod
    def _a_dict(fila):
        return {"id": fila["id"], "usuario": {"id": fila["usuario_id"], "nombre": fila["u_nombre"],
                                              "correo": fila["u_correo"]},
                "mensaje": fila["mensaje"], "creado_en": a_iso_utc(fila["creado_en"]),
                "atendida": bool(fila["atendida"]), "atendida_en": a_iso_utc(fila["atendida_en"])}

    def _obtener(self, alerta_id):
        return self.bd.consultar_uno(_CONSULTA + " WHERE a.id = ?", (alerta_id,))

    # ---------- usuario ----------
    def crear(self, usuario, mensaje=""):
        """Devuelve (alerta, es_nueva). Si ya había una pendiente, devuelve esa y es_nueva=False."""
        if usuario.es_administrador():
            raise PermisoDenegadoError("El administrador no usa el botón SOS.")
        if mensaje is None:
            mensaje = ""
        if not isinstance(mensaje, str) or len(mensaje.strip()) > LARGO_MAXIMO_SOS:
            raise DatosInvalidosError(f"El mensaje debe ser texto de máximo {LARGO_MAXIMO_SOS} caracteres.")
        pendiente = self.pendiente_de(usuario)
        if pendiente:
            return pendiente, False
        nuevo_id = self.bd.ejecutar(
            "INSERT INTO alertas_sos (usuario_id, mensaje, creado_en) VALUES (?,?,?)",
            (usuario.id, mensaje.strip(), marca_utc()))
        return self._a_dict(self._obtener(nuevo_id)), True

    def pendiente_de(self, usuario):
        fila = self.bd.consultar_uno(
            _CONSULTA + " WHERE a.usuario_id = ? AND a.atendida = 0 ORDER BY a.id DESC", (usuario.id,))
        return self._a_dict(fila) if fila else None

    # ---------- administrador ----------
    def listar(self, admin):
        """Pendientes (la más antigua primero) y las últimas 20 atendidas."""
        self._exigir_admin(admin)
        pendientes = self.bd.consultar(_CONSULTA + " WHERE a.atendida = 0 ORDER BY a.id")
        atendidas = self.bd.consultar(_CONSULTA + " WHERE a.atendida = 1 ORDER BY a.atendida_en DESC, a.id DESC LIMIT 20")
        return [self._a_dict(f) for f in pendientes], [self._a_dict(f) for f in atendidas]

    def atender(self, admin, alerta_id):
        self._exigir_admin(admin)
        fila = self._obtener(alerta_id)
        if fila is None:
            raise IndexError("Esa alerta no existe.")
        if not fila["atendida"]:
            self.bd.actualizar(
                "UPDATE alertas_sos SET atendida = 1, atendida_en = ?, atendida_por = ? WHERE id = ? AND atendida = 0",
                (marca_utc(), admin.id, alerta_id))
        return self._a_dict(self._obtener(alerta_id))
