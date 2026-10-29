"""Agenda de acompañamiento: bloques de disponibilidad (los publica el administrador)
y reservas (las hacen los usuarios).

Decisiones de diseño:
  - Cada BLOQUE (una fila de `disponibilidad`) es una sesión de máximo 30 minutos en una fecha
    concreta (disponibilidad puntual, no recurrente). El usuario reserva el bloque completo.
  - El administrador NO publica bloques uno por uno: publica un RANGO libre (09:00-10:00, 14:00-18:00
    o todo el día) y `publicar_rango` lo divide en bloques de DURACION_SESION_MIN. Así la tabla, las
    reservas y la vista de los usuarios siguen funcionando igual que antes.
  - El rango debe caber en el horario de operación (HORA_APERTURA - HORA_CIERRE de config.py).
  - Un bloque no puede solaparse con otro (se valida al crearlo y hay un UNIQUE en la BD).
  - Publicar nunca altera lo existente: si el rango se cruza con bloques ya publicados se rechaza,
    salvo que el administrador pida "reemplazar", que solo sustituye bloques LIBRES. Las citas
    reservadas jamás se borran ni se mueven.
  - Reservar es una sola instrucción UPDATE ... WHERE usuario_id IS NULL: si dos personas
    intentan a la vez, solo una gana.
  - Las horas se interpretan en la hora local del servidor (el computador donde corre HYDISA).
  - Los roles se vuelven a comprobar aquí aunque el servidor web ya lo haga (doble barrera).
"""
from datetime import datetime

from .base_datos import ErrorIntegridad
from .config import (DURACION_MAXIMA_SESION_MIN, DURACION_MINIMA_SESION_MIN, DURACION_SESION_MIN, HORA_APERTURA,
                     HORA_CIERRE, LARGO_MAXIMO_TEMA)
from .excepciones import DatosInvalidosError, HorarioNoDisponibleError, PermisoDenegadoError
from .tiempo import marca_utc

FORMATO_FECHA = "%Y-%m-%d"
FORMATO_HORA = "%H:%M"


class ServicioSesiones:
    def __init__(self, bd, ahora=datetime.now):
        self.bd = bd
        self._ahora = ahora                 # se puede reemplazar en las pruebas

    # ---------- utilidades ----------
    @staticmethod
    def _exigir_admin(usuario):
        if not usuario.es_administrador():
            raise PermisoDenegadoError("Solo el administrador publica horarios.")

    @staticmethod
    def _exigir_usuario(usuario):
        if usuario.es_administrador():
            raise PermisoDenegadoError("El administrador solo gestiona: no agenda sesiones.")

    @staticmethod
    def _leer(texto, formato, nombre):
        try:
            return datetime.strptime(texto, formato)
        except (TypeError, ValueError) as error:
            raise DatosInvalidosError(f"{nombre} no tiene un formato válido.") from error

    @staticmethod
    def _minutos(inicio, fin):
        """Duración entre dos horas 'HH:MM' del mismo día."""
        return int((datetime.strptime(fin, FORMATO_HORA) - datetime.strptime(inicio, FORMATO_HORA)).total_seconds() // 60)

    def _empieza_en(self, fecha, inicio):
        return datetime.strptime(f"{fecha} {inicio}", f"{FORMATO_FECHA} {FORMATO_HORA}")

    def _validar_duracion(self, inicio, fin):
        """REGLA DE 30 MINUTOS: se aplica al crear el bloque y otra vez al reservarlo."""
        minutos = self._minutos(inicio, fin)
        if minutos > DURACION_MAXIMA_SESION_MIN:
            raise DatosInvalidosError(f"Cada sesión dura máximo {DURACION_MAXIMA_SESION_MIN} minutos.")
        if minutos < DURACION_MINIMA_SESION_MIN:
            raise DatosInvalidosError(f"Cada sesión dura mínimo {DURACION_MINIMA_SESION_MIN} minutos.")

    @staticmethod
    def _a_dict(fila, con_usuario=False):
        reservado = fila["usuario_id"] is not None
        bloque = {"id": fila["id"], "fecha": fila["fecha"], "inicio": fila["hora_inicio"], "fin": fila["hora_fin"],
                  "minutos": ServicioSesiones._minutos(fila["hora_inicio"], fila["hora_fin"]),
                  "reservado": reservado, "tema": fila["tema"]}
        if con_usuario:      # el administrador ve quién reservó; los demás usuarios no
            bloque["usuario"] = ({"id": fila["usuario_id"], "nombre": fila["u_nombre"], "correo": fila["u_correo"]}
                                 if reservado else None)
        return bloque

    def _obtener(self, bloque_id):
        return self.bd.consultar_uno("SELECT * FROM disponibilidad WHERE id = ?", (bloque_id,))

    # ---------- administrador ----------
    def _validar_rango(self, fecha, inicio, fin):
        """Formatos, fin posterior a inicio y dentro del horario de operación. Devuelve los textos normalizados."""
        fecha_d = self._leer(fecha, FORMATO_FECHA, "La fecha")
        inicio_d = self._leer(inicio, FORMATO_HORA, "La hora de inicio")
        fin_d = self._leer(fin, FORMATO_HORA, "La hora de fin")
        fecha, inicio, fin = (fecha_d.strftime(FORMATO_FECHA), inicio_d.strftime(FORMATO_HORA),
                              fin_d.strftime(FORMATO_HORA))
        if fin <= inicio:
            raise DatosInvalidosError("La hora de fin debe ser posterior a la de inicio.")
        if inicio < HORA_APERTURA or fin > HORA_CIERRE:
            raise DatosInvalidosError(f"El horario de operación es de {HORA_APERTURA} a {HORA_CIERRE}.")
        return fecha, inicio, fin

    def crear_bloque(self, admin, fecha, inicio, fin):
        """Crea UN bloque (una sola sesión de máx. 30 min). Lo usa publicar_rango internamente y las pruebas."""
        self._exigir_admin(admin)
        fecha, inicio, fin = self._validar_rango(fecha, inicio, fin)
        self._validar_duracion(inicio, fin)
        if self._empieza_en(fecha, inicio) <= self._ahora():
            raise DatosInvalidosError("Solo puedes publicar horarios futuros.")
        if self.bd.consultar_uno(
                "SELECT id FROM disponibilidad WHERE fecha = ? AND hora_inicio < ? AND hora_fin > ?",
                (fecha, fin, inicio)):
            raise HorarioNoDisponibleError("Ese horario se solapa con otro bloque ya publicado.")
        try:
            nuevo_id = self.bd.ejecutar(
                "INSERT INTO disponibilidad (fecha, hora_inicio, hora_fin, creado_por) VALUES (?,?,?,?)",
                (fecha, inicio, fin, admin.id))
        except ErrorIntegridad as error:
            raise HorarioNoDisponibleError("Ya existe un bloque que empieza a esa hora.") from error
        return self._a_dict(self._obtener(nuevo_id))

    # ----- publicar un rango libre -----
    @staticmethod
    def _a_minutos(hora):
        h, m = hora.split(":")
        return int(h) * 60 + int(m)

    @staticmethod
    def _a_hora(minutos):
        return f"{minutos // 60:02d}:{minutos % 60:02d}"

    def _espacios(self, inicio, fin):
        """Divide [inicio, fin) en espacios de DURACION_SESION_MIN. El último puede ser más corto si
        le sobran al menos DURACION_MINIMA_SESION_MIN minutos. Devuelve (espacios, minutos_sobrantes)."""
        espacios, t, tope = [], self._a_minutos(inicio), self._a_minutos(fin)
        while t < tope:
            f = min(t + DURACION_SESION_MIN, tope)
            if f - t < DURACION_MINIMA_SESION_MIN:
                return espacios, f - t
            espacios.append((self._a_hora(t), self._a_hora(f)))
            t = f
        return espacios, 0

    def publicar_rango(self, admin, fecha, inicio=None, fin=None, todo_el_dia=False, reemplazar=False):
        """Publica disponibilidad para un rango libre y lo divide en espacios reservables.

        todo_el_dia: usa de la apertura al cierre (se ignoran inicio y fin).
        reemplazar:  False (por defecto) -> si algún espacio se cruza con bloques ya publicados se rechaza todo.
                     True  -> se sustituyen los bloques LIBRES que se crucen; los reservados no se tocan y
                              en su lugar no se publica nada (quedan como están).
        Todo ocurre en una sola transacción: o se publica completo o no cambia nada.
        """
        self._exigir_admin(admin)
        if todo_el_dia:
            inicio, fin = HORA_APERTURA, HORA_CIERRE
        fecha, inicio, fin = self._validar_rango(fecha, inicio, fin)

        candidatos, sobrante = self._espacios(inicio, fin)
        if not candidatos:
            raise DatosInvalidosError(f"El rango debe durar al menos {DURACION_MINIMA_SESION_MIN} minutos.")

        # Lo que ya pasó no se publica (útil para "todo el día" en el día de hoy)
        ahora = self._ahora()
        futuros = [c for c in candidatos if self._empieza_en(fecha, c[0]) > ahora]
        omitidos_pasados = len(candidatos) - len(futuros)
        if not futuros:
            raise DatosInvalidosError("Ese rango ya pasó: solo puedes publicar horarios futuros.")

        # Cruces con lo ya publicado ese día
        existentes = self.bd.consultar("SELECT * FROM disponibilidad WHERE fecha = ?", (fecha,))
        def cruza(c, f):
            return f["hora_inicio"] < c[1] and f["hora_fin"] > c[0]
        cruzados = [f for f in existentes if any(cruza(c, f) for c in futuros)]
        if cruzados and not reemplazar:
            primero = min(cruzados, key=lambda f: f["hora_inicio"])
            raise HorarioNoDisponibleError(
                f"Ese rango se cruza con horarios ya publicados ({primero['hora_inicio']}-{primero['hora_fin']}"
                f"{' y otros' if len(cruzados) > 1 else ''}). Elige otro rango o usa «reemplazar espacios libres».")

        libres = [f for f in cruzados if f["usuario_id"] is None]
        reservados = [f for f in cruzados if f["usuario_id"] is not None]
        nuevos = [c for c in futuros if not any(cruza(c, f) for f in reservados)]   # nunca sobre una cita reservada
        if not nuevos:
            raise HorarioNoDisponibleError("No hay espacios libres para publicar: el rango ya tiene citas reservadas.")

        operaciones = [("DELETE FROM disponibilidad WHERE id = ? AND usuario_id IS NULL", (f["id"],)) for f in libres]
        operaciones += [("INSERT INTO disponibilidad (fecha, hora_inicio, hora_fin, creado_por) VALUES (?,?,?,?)",
                         (fecha, ini, fi, admin.id)) for ini, fi in nuevos]
        try:
            self.bd.ejecutar_lote(operaciones)
        except ErrorIntegridad as error:
            raise HorarioNoDisponibleError("Ya existen bloques que empiezan a esas horas.") from error

        creados = [self._a_dict(self.bd.consultar_uno(
            "SELECT * FROM disponibilidad WHERE fecha = ? AND hora_inicio = ?", (fecha, ini))) for ini, _ in nuevos]
        return {"creados": creados, "reemplazados": len(libres), "conservados": len(reservados),
                "omitidos_pasados": omitidos_pasados, "sobrante_min": sobrante,
                "rango": {"fecha": fecha, "inicio": inicio, "fin": fin}}

    def listar_agenda(self, admin):
        """Todos los bloques desde hoy, con el nombre de quien reservó."""
        self._exigir_admin(admin)
        filas = self.bd.consultar(
            """SELECT d.*, u.nombre AS u_nombre, u.correo AS u_correo
               FROM disponibilidad d LEFT JOIN usuarios u ON u.id = d.usuario_id
               WHERE d.fecha >= ? ORDER BY d.fecha, d.hora_inicio""",
            (self._ahora().strftime(FORMATO_FECHA),))
        return [self._a_dict(f, con_usuario=True) for f in filas]

    def eliminar_bloque(self, admin, bloque_id):
        self._exigir_admin(admin)
        fila = self._obtener(bloque_id)
        if fila is None:
            raise IndexError("Ese bloque no existe.")
        if fila["usuario_id"] is not None:
            raise HorarioNoDisponibleError("No puedes eliminar un bloque que ya fue reservado.")
        self.bd.ejecutar("DELETE FROM disponibilidad WHERE id = ? AND usuario_id IS NULL", (bloque_id,))

    # ---------- usuarios ----------
    def disponibles(self, usuario):
        """Bloques libres y futuros: lo que el usuario ve para reservar."""
        self._exigir_usuario(usuario)
        ahora = self._ahora()
        filas = self.bd.consultar(
            """SELECT * FROM disponibilidad WHERE usuario_id IS NULL
               AND (fecha > ? OR (fecha = ? AND hora_inicio > ?)) ORDER BY fecha, hora_inicio""",
            (ahora.strftime(FORMATO_FECHA), ahora.strftime(FORMATO_FECHA), ahora.strftime(FORMATO_HORA)))
        return [self._a_dict(f) for f in filas]

    def mias(self, usuario):
        self._exigir_usuario(usuario)
        filas = self.bd.consultar(
            "SELECT * FROM disponibilidad WHERE usuario_id = ? AND fecha >= ? ORDER BY fecha, hora_inicio",
            (usuario.id, self._ahora().strftime(FORMATO_FECHA)))
        return [self._a_dict(f) for f in filas]

    def reservar(self, usuario, bloque_id, tema=""):
        self._exigir_usuario(usuario)
        tema = (tema or "").strip() if isinstance(tema, str) or tema is None else None
        if tema is None or len(tema) > LARGO_MAXIMO_TEMA:
            raise DatosInvalidosError(f"El tema debe ser texto de máximo {LARGO_MAXIMO_TEMA} caracteres.")
        fila = self._obtener(bloque_id)
        if fila is None:
            raise IndexError("Ese horario no existe.")          # solo se puede reservar lo publicado
        self._validar_duracion(fila["hora_inicio"], fila["hora_fin"])
        if self._empieza_en(fila["fecha"], fila["hora_inicio"]) <= self._ahora():
            raise HorarioNoDisponibleError("Ese horario ya pasó.")
        if self.bd.consultar_uno(
                """SELECT id FROM disponibilidad WHERE usuario_id = ? AND fecha = ? AND hora_inicio < ?
                   AND hora_fin > ? AND id != ?""",
                (usuario.id, fila["fecha"], fila["hora_fin"], fila["hora_inicio"], bloque_id)):
            raise HorarioNoDisponibleError("Ya tienes otra sesión que se cruza con ese horario.")
        cambiadas = self.bd.actualizar(
            "UPDATE disponibilidad SET usuario_id = ?, tema = ?, reservado_en = ? WHERE id = ? AND usuario_id IS NULL",
            (usuario.id, tema, marca_utc(), bloque_id))
        if cambiadas == 0:
            raise HorarioNoDisponibleError("Ese horario ya fue reservado por otra persona.")
        return self._a_dict(self._obtener(bloque_id))

    def cancelar(self, usuario, bloque_id):
        """El usuario libera su propia reserva (el bloque vuelve a quedar disponible)."""
        self._exigir_usuario(usuario)
        fila = self.bd.consultar_uno(
            "SELECT * FROM disponibilidad WHERE id = ? AND usuario_id = ?", (bloque_id, usuario.id))
        if fila is None:
            raise IndexError("No tienes una reserva con ese número.")   # no revela reservas ajenas
        if self._empieza_en(fila["fecha"], fila["hora_inicio"]) <= self._ahora():
            raise HorarioNoDisponibleError("No puedes cancelar una sesión que ya empezó.")
        self.bd.actualizar(
            "UPDATE disponibilidad SET usuario_id = NULL, tema = '', reservado_en = NULL WHERE id = ? AND usuario_id = ?",
            (bloque_id, usuario.id))
        return self._a_dict(self._obtener(bloque_id))
