"""Servidor web de HYDISA (API + frontend). Ejecutar con:  python servidor.py

Para qué sirve: es el "puente" entre el frontend (lo que se ve en el navegador)
y las clases de Python que ya hicimos. Cada opción del menú de main.py
tiene aquí un "endpoint" (una dirección web) que llama a la MISMA lógica:

    main.py                      ->  servidor.py (dirección web)
    1. Registrarse               ->  POST /api/admin/usuarios   (solo administrador)
    2. Iniciar sesión            ->  POST /api/login
    1. Cargar PDF (+ palabras)   ->  POST /api/reportes
    2. Historial                 ->  GET  /api/reportes
    3. Ver ruta + progreso       ->  GET  /api/reportes/<id>/ruta
    4. Marcar actividad          ->  POST /api/reportes/<id>/actividades/<n>/cumplir
    5. Exportar PDF              ->  GET  /api/reportes/<id>/pdf
    (palabras clave de un reporte) GET  /api/reportes/<id>/palabras

Control de acceso (todo se decide AQUÍ, en el servidor; el navegador solo muestra u oculta):
  - Cada solicitud trae un token. El token apunta a un id de usuario y el usuario se vuelve
    a leer de la base de datos en CADA solicitud (rol, permisos y si sigue activo).
  - Administrador = rol "administrador" y correo hydisa123@gmail.com (ver modelos.Usuario).
  - Rutas /api/admin/*  -> solo administrador (403 para cualquier otro).
  - Cada operación con reportes exige un permiso concreto (config.PERMISOS).
  - No existe registro público: las cuentas las crea el administrador.
  - Separación de roles: el administrador SOLO gestiona (cuentas, usuarios, reportes ajenos, agenda
    y alertas SOS). Las rutas de acompañamiento (/api/reportes, /api/sesiones, /api/sos) le responden 403.
    A los demás usuarios, todo lo de /api/admin/* les responde 403.
  - Disponibilidad: el administrador publica un rango libre (o todo el día) que se divide en bloques de
    30 min (/api/admin/agenda); los usuarios
    reservan solo bloques publicados y libres (/api/sesiones). SOS: POST /api/sos crea una alerta que
    el administrador ve y marca como atendida (/api/admin/alertas).

Solo usa la biblioteca estándar de Python: no hay que instalar nada nuevo.
"""
import json
import mimetypes
import os
import re
import secrets
import tempfile
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from hydisa.base_datos import BaseDatos
from hydisa.config import (CORREO_ADMIN, DURACION_MAXIMA_SESION_MIN, DURACION_SESION_MIN, HORA_APERTURA, HORA_CIERRE,
                           PERMISOS, RAIZ, RUTA_BD, TAMANO_MAXIMO_MB)
from hydisa.excepciones import (ArchivoInvalidoError, CredencialesError, HorarioNoDisponibleError, HydisaError,
                                PermisoDenegadoError)
from hydisa.servicio_alertas import ServicioAlertas
from hydisa.servicio_reportes import ServicioReportes
from hydisa.servicio_sesiones import ServicioSesiones
from hydisa.tiempo import a_iso_utc
from hydisa.servicio_usuarios import ServicioUsuarios

CARPETA_FRONTEND = RAIZ / "frontend"
PUERTO = int(os.getenv("PUERTO", "8000"))
LIMITE_CUERPO = (TAMANO_MAXIMO_MB + 1) * 1024 * 1024      # margen sobre el límite del PDF (RNF14)


class RespuestaError(Exception):
    """Error con código HTTP para devolver al frontend."""

    def __init__(self, codigo, mensaje):
        super().__init__(mensaje)
        self.codigo = codigo


class Aplicacion:
    """Reúne los servicios y las sesiones abiertas (en memoria)."""

    def __init__(self, bd):
        self.bd = bd
        self.usuarios = ServicioUsuarios(bd)
        self.reportes = ServicioReportes(bd)
        self.agenda = ServicioSesiones(bd)
        self.alertas = ServicioAlertas(bd)
        self.sesiones = {}                  # token -> id de usuario (el usuario se relee en cada solicitud)


class Manejador(BaseHTTPRequestHandler):
    app = None                              # se asigna en crear_servidor()

    # ---------- utilidades de respuesta ----------
    def _cabeceras_comunes(self):
        # CORS: permite abrir index.html con doble clic (file://) y aun así llamar a la API.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Nombre-Archivo")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Cache-Control", "no-store")

    def _enviar_json(self, datos, codigo=200):
        cuerpo = json.dumps(datos, ensure_ascii=False).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self._cabeceras_comunes()
        self.end_headers()
        self.wfile.write(cuerpo)

    def _enviar_bytes(self, contenido, tipo, nombre_descarga=None):
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(contenido)))
        if nombre_descarga:
            self.send_header("Content-Disposition", f'attachment; filename="{nombre_descarga}"')
        self._cabeceras_comunes()
        self.end_headers()
        self.wfile.write(contenido)

    def _leer_json(self):
        largo = int(self.headers.get("Content-Length") or 0)
        if largo > 100_000:
            raise RespuestaError(413, "Solicitud demasiado grande.")
        try:
            datos = json.loads(self.rfile.read(largo) or b"{}")
        except json.JSONDecodeError as error:
            raise RespuestaError(400, "El cuerpo no es JSON válido.") from error
        if not isinstance(datos, dict):
            raise RespuestaError(400, "El cuerpo debe ser un objeto JSON.")
        return datos

    def _usuario_actual(self):
        encabezado = self.headers.get("Authorization", "")
        token = encabezado[7:] if encabezado.startswith("Bearer ") else ""
        usuario_id = self.app.sesiones.get(token)
        usuario = self.app.usuarios.obtener(usuario_id, solo_activos=True) if usuario_id else None
        if usuario is None:
            self.app.sesiones.pop(token, None)          # cuenta desactivada o token inventado
            raise RespuestaError(401, "Debes iniciar sesión.")
        return usuario

    @staticmethod
    def _exigir_permiso(usuario, permiso):
        if usuario.es_administrador():
            raise RespuestaError(403, "El administrador solo tiene funciones de gestión.")
        if not usuario.tiene_permiso(permiso):
            raise RespuestaError(403, "Tu cuenta no tiene permiso para esta acción.")

    @staticmethod
    def _exigir_no_admin(usuario):
        """Sesiones y SOS son para usuarios; el administrador solo gestiona."""
        if usuario.es_administrador():
            raise RespuestaError(403, "El administrador solo tiene funciones de gestión.")

    @staticmethod
    def _exigir_admin(usuario):
        if not usuario.es_administrador():
            raise RespuestaError(403, "Solo el administrador puede hacer esto.")

    @staticmethod
    def _serializar_usuario(u):
        admin = u.es_administrador()
        return {"id": u.id, "nombre": u.nombre, "correo": u.correo, "rol": u.rol,
                "es_admin": admin, "permisos": [] if admin else list(u.permisos)}

    def _serializar_ruta(self, usuario, reporte_id):
        items = self.app.reportes.obtener_ruta(usuario, reporte_id)
        return {
            "reporte_id": reporte_id,
            "progreso": self.app.reportes.progreso(usuario, reporte_id),
            "ruta": [{"posicion": n, "categoria": i.categoria, "prioridad": i.prioridad,
                      "actividad": i.actividad, "cumplida": i.cumplida}
                     for n, i in enumerate(items, 1)],
        }

    def _palabras_de(self, usuario, reporte_id):
        """Palabras clave de un reporte ya guardado (usa el texto almacenado en la BD)."""
        fila = self.app.bd.consultar_uno(
            "SELECT texto FROM reportes WHERE id = ? AND usuario_id = ?", (reporte_id, usuario.id))
        if fila is None:
            raise RespuestaError(404, "Ese reporte no existe.")
        return self.app.reportes.motor.palabras_detectadas(fila["texto"])

    # ---------- despacho ----------
    def do_OPTIONS(self):
        self.send_response(204)
        self._cabeceras_comunes()
        self.end_headers()

    def do_GET(self):
        self._despachar("GET")

    def do_POST(self):
        self._despachar("POST")

    def _despachar(self, metodo):
        ruta = urlparse(self.path).path
        try:
            if ruta.startswith("/api/"):
                self._api(metodo, ruta[5:].strip("/"))
            elif metodo == "GET":
                self._estatico(ruta)
            else:
                raise RespuestaError(405, "Método no permitido.")
        except RespuestaError as error:
            self._enviar_json({"error": str(error)}, error.codigo)
        except CredencialesError as error:
            self._enviar_json({"error": str(error)}, 401)
        except PermisoDenegadoError as error:
            self._enviar_json({"error": str(error)}, 403)
        except HorarioNoDisponibleError as error:
            self._enviar_json({"error": str(error)}, 409)
        except HydisaError as error:
            self._enviar_json({"error": str(error)}, 400)
        except IndexError as error:
            self._enviar_json({"error": str(error)}, 404)
        except ValueError as error:
            self._enviar_json({"error": f"Solicitud inválida: {error}"}, 400)
        except Exception as error:                       # no mostramos detalles internos
            self.log_error("Error interno: %r", error)
            self._enviar_json({"error": "Error interno del servidor."}, 500)

    # ---------- API ----------
    def _api(self, metodo, ruta):
        app = self.app
        partes = ruta.split("/")

        if (metodo, ruta) == ("POST", "login"):                          # main: 2. Iniciar sesión
            d = self._leer_json()
            u = app.usuarios.iniciar_sesion(d.get("correo", ""), d.get("clave", ""))
            token = secrets.token_urlsafe(32)
            app.sesiones[token] = u.id
            return self._enviar_json({"token": token, "usuario": self._serializar_usuario(u)})

        if (metodo, ruta) == ("POST", "logout"):                         # main: 0. Salir
            token = self.headers.get("Authorization", "")[7:]
            app.sesiones.pop(token, None)
            return self._enviar_json({"ok": True})

        usuario = self._usuario_actual()                                 # desde aquí: requiere sesión

        if (metodo, ruta) == ("GET", "yo"):
            return self._enviar_json({"usuario": self._serializar_usuario(usuario)})

        if partes[0] == "admin":                                         # solo administrador
            self._exigir_admin(usuario)
            return self._api_admin(metodo, partes[1:])

        if partes[0] == "sesiones":                                      # acompañamiento: agenda
            self._exigir_no_admin(usuario)
            if (metodo, partes) == ("GET", ["sesiones"]):
                return self._enviar_json({"disponibles": app.agenda.disponibles(usuario),
                                          "mias": app.agenda.mias(usuario)})
            if metodo == "POST" and len(partes) == 3 and partes[1].isdigit() and partes[2] in ("reservar", "cancelar"):
                if partes[2] == "reservar":
                    bloque = app.agenda.reservar(usuario, int(partes[1]), self._leer_json().get("tema", ""))
                else:
                    bloque = app.agenda.cancelar(usuario, int(partes[1]))
                return self._enviar_json({"bloque": bloque})

        if partes[0] == "sos":                                           # botón SOS
            self._exigir_no_admin(usuario)
            if (metodo, partes) == ("GET", ["sos"]):
                return self._enviar_json({"pendiente": app.alertas.pendiente_de(usuario)})
            if (metodo, partes) == ("POST", ["sos"]):
                alerta, nueva = app.alertas.crear(usuario, self._leer_json().get("mensaje", ""))
                return self._enviar_json({"alerta": alerta, "nueva": nueva}, 201 if nueva else 200)

        if (metodo, ruta) == ("GET", "reportes"):                        # 2. Historial
            self._exigir_permiso(usuario, "ver_reportes")
            filas = app.reportes.historial(usuario)
            return self._enviar_json({"reportes": [
                {"id": f["id"], "nombre_archivo": f["nombre_archivo"], "creado_en": a_iso_utc(f["creado_en"])}
                for f in filas]})

        if (metodo, ruta) == ("POST", "reportes"):                       # 1. Cargar PDF
            if not usuario.tiene_permiso("cargar_pdf"):
                self.rfile.read(min(int(self.headers.get("Content-Length") or 0), LIMITE_CUERPO))
            self._exigir_permiso(usuario, "cargar_pdf")
            return self._cargar_pdf(usuario)

        if len(partes) >= 3 and partes[0] == "reportes" and partes[1].isdigit():
            reporte_id, resto = int(partes[1]), partes[2:]

            if metodo == "GET" and resto == ["ruta"]:                    # 3. Ver ruta
                self._exigir_permiso(usuario, "ver_reportes")
                return self._enviar_json(self._serializar_ruta(usuario, reporte_id))

            if metodo == "GET" and resto == ["palabras"]:
                self._exigir_permiso(usuario, "ver_reportes")
                return self._enviar_json({"palabras": self._palabras_de(usuario, reporte_id)})

            if metodo == "POST" and len(resto) == 3 and resto[0] == "actividades" \
                    and resto[1].isdigit() and resto[2] == "cumplir":    # 4. Marcar actividad
                self._exigir_permiso(usuario, "marcar_actividades")
                app.reportes.marcar_cumplida(usuario, reporte_id, int(resto[1]))
                return self._enviar_json(self._serializar_ruta(usuario, reporte_id))

            if metodo == "GET" and resto == ["pdf"]:                     # 5. Exportar PDF
                self._exigir_permiso(usuario, "exportar_pdf")
                destino = app.reportes.exportar_pdf(usuario, reporte_id)
                return self._enviar_bytes(Path(destino).read_bytes(), "application/pdf", Path(destino).name)

        raise RespuestaError(404, "Ruta de la API no encontrada.")

    def _api_admin(self, metodo, partes):
        """Rutas /api/admin/... (el rol ya fue comprobado antes de llegar aquí)."""
        app = self.app
        admin = self._usuario_actual()
        if partes[:1] == ["alertas"]:                                    # alertas SOS
            if metodo == "GET" and len(partes) == 1:
                pendientes, atendidas = app.alertas.listar(admin)
                return self._enviar_json({"pendientes": pendientes, "atendidas": atendidas})
            if metodo == "POST" and len(partes) == 3 and partes[1].isdigit() and partes[2] == "atender":
                return self._enviar_json({"alerta": app.alertas.atender(admin, int(partes[1]))})
            raise RespuestaError(404, "Ruta de la API no encontrada.")

        if partes[:1] == ["agenda"]:                                     # disponibilidad horaria
            if metodo == "GET" and len(partes) == 1:
                return self._enviar_json({"bloques": app.agenda.listar_agenda(admin),
                                          "duracion_maxima": DURACION_MAXIMA_SESION_MIN,
                                          "duracion_sesion": DURACION_SESION_MIN,
                                          "apertura": HORA_APERTURA, "cierre": HORA_CIERRE})
            if metodo == "POST" and len(partes) == 1:
                d = self._leer_json()
                for campo in ("todo_el_dia", "reemplazar"):                  # deben ser true/false de verdad
                    if not isinstance(d.get(campo, False), bool):
                        raise RespuestaError(400, f"«{campo}» debe ser true o false.")
                r = app.agenda.publicar_rango(admin, d.get("fecha"), d.get("inicio"), d.get("fin"),
                                              todo_el_dia=d.get("todo_el_dia", False), reemplazar=d.get("reemplazar", False))
                # "bloque" (el primero) se conserva por compatibilidad con quien publicaba un solo bloque
                return self._enviar_json({"bloque": r["creados"][0], "bloques": r["creados"], **{k: v for k, v in r.items() if k != "creados"}}, 201)
            if metodo == "POST" and len(partes) == 3 and partes[1].isdigit() and partes[2] == "eliminar":
                app.agenda.eliminar_bloque(admin, int(partes[1]))
                return self._enviar_json({"ok": True})
            raise RespuestaError(404, "Ruta de la API no encontrada.")

        if partes[:1] != ["usuarios"]:
            raise RespuestaError(404, "Ruta de la API no encontrada.")
        partes = partes[1:]

        if not partes and metodo == "GET":                               # listado de usuarios
            return self._enviar_json({
                "usuarios": [{**u, "es_admin": u["rol"] == "administrador" and u["correo"] == CORREO_ADMIN}
                             for u in app.usuarios.listar()],
                "catalogo": [{"clave": k, "nombre": v} for k, v in PERMISOS.items()]})

        if not partes and metodo == "POST":                              # crear usuario (+ permisos)
            d = self._leer_json()
            # Siempre rol "usuario": el campo "rol" que mande el cliente se ignora.
            nuevo = app.usuarios.registrar(d.get("nombre", ""), d.get("correo", ""), d.get("clave", ""),
                                           rol="usuario", permisos=d.get("permisos", []))
            return self._enviar_json({"usuario": self._serializar_usuario(nuevo)}, 201)

        if partes and partes[0].isdigit():
            destino = app.usuarios.obtener(int(partes[0]))
            if destino is None:
                raise RespuestaError(404, "Ese usuario no existe.")
            resto = partes[1:]

            if metodo == "GET" and not resto:                            # detalle de un usuario
                filas = app.reportes.historial(destino)
                return self._enviar_json({
                    "usuario": self._serializar_usuario(destino),
                    "reportes": [{"id": f["id"], "nombre_archivo": f["nombre_archivo"],
                                  "creado_en": a_iso_utc(f["creado_en"])} for f in filas]})

            if metodo == "POST" and resto == ["permisos"]:               # cambiar permisos
                d = self._leer_json()
                actualizado = app.usuarios.actualizar_permisos(destino.id, d.get("permisos"))
                return self._enviar_json({"usuario": self._serializar_usuario(actualizado)})

            if metodo == "GET" and len(resto) == 2 and resto[0] == "reportes" and resto[1].isdigit():
                rid = int(resto[1])                                      # ver un reporte ajeno
                datos = self._serializar_ruta(destino, rid)
                datos["palabras"] = self._palabras_de(destino, rid)
                return self._enviar_json(datos)

        raise RespuestaError(404, "Ruta de la API no encontrada.")

    def _cargar_pdf(self, usuario):
        """Recibe los bytes del PDF, lo guarda en una carpeta temporal con su nombre
        original y ejecuta exactamente lo mismo que la opción 1 de main.py."""
        largo = int(self.headers.get("Content-Length") or 0)
        if largo <= 0:
            raise ArchivoInvalidoError("No se recibió ningún archivo.")
        if largo > LIMITE_CUERPO:
            raise ArchivoInvalidoError(f"El archivo supera {TAMANO_MAXIMO_MB} MB.")
        nombre = unquote(self.headers.get("X-Nombre-Archivo", "documento.pdf"))
        nombre = re.sub(r'[\\/:*?"<>|]', "_", Path(nombre).name) or "documento.pdf"
        contenido = self.rfile.read(largo)
        with tempfile.TemporaryDirectory() as carpeta:
            ruta_pdf = Path(carpeta) / nombre
            ruta_pdf.write_bytes(contenido)
            reporte_id = self.app.reportes.analizar_pdf(usuario, ruta_pdf)
            texto = self.app.reportes.pdf.extraer_texto(ruta_pdf)
            palabras = self.app.reportes.motor.palabras_detectadas(texto)
        datos = self._serializar_ruta(usuario, reporte_id)
        datos["palabras"] = palabras
        datos["nombre_archivo"] = nombre
        return self._enviar_json(datos, 201)

    # ---------- archivos del frontend ----------
    def _estatico(self, ruta):
        relativa = unquote(ruta).lstrip("/") or "index.html"
        archivo = (CARPETA_FRONTEND / relativa).resolve()
        if not archivo.is_relative_to(CARPETA_FRONTEND.resolve()) or not archivo.is_file():
            raise RespuestaError(404, "Archivo no encontrado.")
        tipo = mimetypes.guess_type(archivo.name)[0] or "application/octet-stream"
        if tipo.startswith("text/") or tipo in ("application/javascript", "application/json"):
            tipo += "; charset=utf-8"
        self._enviar_bytes(archivo.read_bytes(), tipo)

    def log_message(self, formato, *args):
        print(f"[HYDISA] {self.address_string()} {formato % args}")


def crear_servidor(bd, puerto=PUERTO, host="127.0.0.1"):
    """Crea el servidor. Se usa también desde las pruebas."""
    Manejador.app = Aplicacion(bd)
    return HTTPServer((host, puerto), Manejador)


def main():
    bd = BaseDatos(RUTA_BD)
    servidor = crear_servidor(bd)
    clave_admin = os.getenv("ADMIN_CLAVE", "")
    if clave_admin:
        print(f"Cuenta de administrador ({CORREO_ADMIN}): {Manejador.app.usuarios.asegurar_administrador(clave_admin)}.")
    elif not bd.consultar_uno("SELECT id FROM usuarios WHERE correo = ?", (CORREO_ADMIN,)):
        print("AVISO: no existe el administrador. Agrega ADMIN_CLAVE=tu_clave al archivo .env y reinicia.")
    tipo = "PostgreSQL (Supabase)" if bd.es_postgres else "SQLite local"
    print(f"HYDISA listo con base de datos {tipo}.")
    print(f"Abre en el navegador:  http://127.0.0.1:{PUERTO}")
    print("Para detener el servidor: Ctrl + C")
    if not os.getenv("NO_ABRIR_NAVEGADOR"):
        threading.Timer(1.0, webbrowser.open, args=(f"http://127.0.0.1:{PUERTO}",)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        servidor.server_close()
        bd.cerrar()


if __name__ == "__main__":
    main()
