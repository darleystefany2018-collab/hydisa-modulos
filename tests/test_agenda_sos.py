"""Pruebas de la agenda (bloques de máx. 30 min, reservas) y del botón SOS. Reloj fijo para no depender de la hora real."""
import unittest
from datetime import datetime

from hydisa.base_datos import BaseDatos
from hydisa.excepciones import DatosInvalidosError, HorarioNoDisponibleError, PermisoDenegadoError
from hydisa.servicio_alertas import ServicioAlertas
from hydisa.servicio_sesiones import ServicioSesiones
from hydisa.servicio_usuarios import ServicioUsuarios

AHORA = datetime(2026, 10, 23, 10, 0)      # "hoy" para las pruebas
MANANA = "2026-10-24"


class PruebasAgenda(unittest.TestCase):
    def setUp(self):
        self.bd = BaseDatos()
        usuarios = ServicioUsuarios(self.bd)
        usuarios.asegurar_administrador("ClaveAdmin123")
        self.admin = usuarios.iniciar_sesion("hydisa123@gmail.com", "ClaveAdmin123")
        self.ana = usuarios.registrar("Ana", "ana@mail.com", "clave12345")
        self.luis = usuarios.registrar("Luis", "luis@mail.com", "clave12345")
        self.agenda = ServicioSesiones(self.bd, ahora=lambda: AHORA)
        self.alertas = ServicioAlertas(self.bd)

    def insertar_crudo(self, fecha, inicio, fin):
        """Simula datos que no pasaron por el servicio (para probar la segunda barrera)."""
        return self.bd.ejecutar(
            "INSERT INTO disponibilidad (fecha, hora_inicio, hora_fin, creado_por) VALUES (?,?,?,?)",
            (fecha, inicio, fin, self.admin.id))

    # ---------- roles ----------
    def test_administrador_no_tiene_permisos_de_usuario(self):
        self.assertTrue(self.admin.es_administrador())
        self.assertEqual(self.admin.permisos, [])
        for permiso in ("cargar_pdf", "ver_reportes", "marcar_actividades", "exportar_pdf"):
            self.assertFalse(self.admin.tiene_permiso(permiso))

    def test_solo_el_administrador_gestiona_la_agenda_y_las_alertas(self):
        with self.assertRaises(PermisoDenegadoError):
            self.agenda.crear_bloque(self.ana, MANANA, "09:00", "09:30")
        with self.assertRaises(PermisoDenegadoError):
            self.agenda.listar_agenda(self.ana)
        with self.assertRaises(PermisoDenegadoError):
            self.alertas.listar(self.ana)
        with self.assertRaises(PermisoDenegadoError):
            self.alertas.atender(self.ana, 1)

    def test_administrador_no_agenda_ni_usa_sos(self):
        bloque = self.agenda.crear_bloque(self.admin, MANANA, "09:00", "09:30")
        with self.assertRaises(PermisoDenegadoError):
            self.agenda.reservar(self.admin, bloque["id"])
        with self.assertRaises(PermisoDenegadoError):
            self.agenda.disponibles(self.admin)
        with self.assertRaises(PermisoDenegadoError):
            self.alertas.crear(self.admin, "hola")

    # ---------- duración de 30 minutos ----------
    def test_bloque_de_30_minutos_o_menos_se_acepta(self):
        self.assertEqual(self.agenda.crear_bloque(self.admin, MANANA, "09:00", "09:30")["minutos"], 30)
        self.assertEqual(self.agenda.crear_bloque(self.admin, MANANA, "10:00", "10:15")["minutos"], 15)

    def test_bloque_de_mas_de_30_minutos_se_rechaza(self):
        for fin in ("09:31", "09:45", "10:00", "12:00"):
            with self.assertRaises(DatosInvalidosError, msg=fin):
                self.agenda.crear_bloque(self.admin, MANANA, "09:00", fin)

    def test_bloques_invalidos(self):
        for fecha, ini, fin in [(MANANA, "09:30", "09:00"), (MANANA, "09:00", "09:00"), (MANANA, "09:00", "09:03"),
                                ("mañana", "09:00", "09:30"), (MANANA, "9h", "09:30"), (MANANA, "09:00", None),
                                ("2026-10-22", "09:00", "09:30"), ("2026-10-23", "09:30", "10:00")]:   # pasado / ya empezó
            with self.assertRaises(DatosInvalidosError, msg=(fecha, ini, fin)):
                self.agenda.crear_bloque(self.admin, fecha, ini, fin)

    def test_reserva_revalida_los_30_minutos(self):
        largo = self.insertar_crudo(MANANA, "09:00", "09:45")           # alguien lo metió sin pasar por el servicio
        with self.assertRaises(DatosInvalidosError):
            self.agenda.reservar(self.ana, largo)

    # ---------- solapamientos ----------
    def test_los_bloques_no_se_solapan(self):
        self.agenda.crear_bloque(self.admin, MANANA, "10:00", "10:30")
        for ini, fin in [("10:00", "10:30"), ("10:15", "10:45"), ("09:45", "10:15"), ("10:10", "10:20")]:
            with self.assertRaises(HorarioNoDisponibleError, msg=(ini, fin)):
                self.agenda.crear_bloque(self.admin, MANANA, ini, fin)
        self.agenda.crear_bloque(self.admin, MANANA, "10:30", "11:00")     # pegado, sin cruzarse: sí
        self.agenda.crear_bloque(self.admin, "2026-10-25", "10:00", "10:30")  # otro día: sí

    # ---------- reservas ----------
    def test_reserva_solo_dentro_de_lo_publicado(self):
        with self.assertRaises(IndexError):
            self.agenda.reservar(self.ana, 999)                           # no existe ese horario
        bloque = self.agenda.crear_bloque(self.admin, MANANA, "09:00", "09:30")
        self.assertEqual([b["id"] for b in self.agenda.disponibles(self.ana)], [bloque["id"]])
        reservado = self.agenda.reservar(self.ana, bloque["id"], "Manejo del estrés")
        self.assertTrue(reservado["reservado"])
        self.assertEqual(self.agenda.disponibles(self.luis), [])           # ya no aparece para nadie
        self.assertEqual([b["id"] for b in self.agenda.mias(self.ana)], [bloque["id"]])
        self.assertEqual(self.agenda.mias(self.luis), [])

    def test_horario_ocupado_no_se_puede_reservar_otra_vez(self):
        bloque = self.agenda.crear_bloque(self.admin, MANANA, "09:00", "09:30")
        self.agenda.reservar(self.ana, bloque["id"])
        with self.assertRaises(HorarioNoDisponibleError):
            self.agenda.reservar(self.luis, bloque["id"])
        with self.assertRaises(HorarioNoDisponibleError):
            self.agenda.reservar(self.ana, bloque["id"])

    def test_no_se_reserva_un_horario_pasado(self):
        pasado = self.insertar_crudo("2026-10-23", "08:00", "08:30")
        with self.assertRaises(HorarioNoDisponibleError):
            self.agenda.reservar(self.ana, pasado)

    def test_usuario_no_reserva_dos_sesiones_que_se_cruzan(self):
        a, b = self.insertar_crudo(MANANA, "09:00", "09:30"), self.insertar_crudo(MANANA, "09:15", "09:45")
        self.agenda.reservar(self.ana, a)
        with self.assertRaises(HorarioNoDisponibleError):
            self.agenda.reservar(self.ana, b)

    def test_cancelar_libera_el_horario_y_solo_el_dueno_puede(self):
        bloque = self.agenda.crear_bloque(self.admin, MANANA, "09:00", "09:30")
        self.agenda.reservar(self.ana, bloque["id"])
        with self.assertRaises(IndexError):
            self.agenda.cancelar(self.luis, bloque["id"])
        self.agenda.cancelar(self.ana, bloque["id"])
        self.assertEqual(len(self.agenda.disponibles(self.luis)), 1)
        self.agenda.reservar(self.luis, bloque["id"])

    def test_admin_ve_quien_reservo_y_no_elimina_reservados(self):
        libre = self.agenda.crear_bloque(self.admin, MANANA, "09:00", "09:30")
        ocupado = self.agenda.crear_bloque(self.admin, MANANA, "10:00", "10:30")
        self.agenda.reservar(self.ana, ocupado["id"], "Hábitos de descanso")
        agenda = {b["id"]: b for b in self.agenda.listar_agenda(self.admin)}
        self.assertIsNone(agenda[libre["id"]]["usuario"])
        self.assertEqual(agenda[ocupado["id"]]["usuario"]["nombre"], "Ana")
        with self.assertRaises(HorarioNoDisponibleError):
            self.agenda.eliminar_bloque(self.admin, ocupado["id"])
        self.agenda.eliminar_bloque(self.admin, libre["id"])
        self.assertNotIn(libre["id"], [b["id"] for b in self.agenda.listar_agenda(self.admin)])

    # ---------- SOS ----------
    def test_sos_genera_alerta_con_usuario_y_hora(self):
        alerta, nueva = self.alertas.crear(self.ana, "  Me siento muy ansiosa  ")
        self.assertTrue(nueva)
        pendientes, atendidas = self.alertas.listar(self.admin)
        self.assertEqual(len(pendientes), 1)
        self.assertEqual(atendidas, [])
        p = pendientes[0]
        self.assertEqual((p["usuario"]["nombre"], p["usuario"]["correo"]), ("Ana", "ana@mail.com"))
        self.assertEqual(p["mensaje"], "Me siento muy ansiosa")
        self.assertRegex(p["creado_en"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertFalse(p["atendida"])

    def test_sos_sin_mensaje_es_valido_y_no_se_duplica(self):
        primera, nueva1 = self.alertas.crear(self.ana)
        segunda, nueva2 = self.alertas.crear(self.ana, "otra vez")
        self.assertEqual((nueva1, nueva2, primera["id"]), (True, False, segunda["id"]))
        self.assertEqual(len(self.alertas.listar(self.admin)[0]), 1)
        self.alertas.crear(self.luis)                                       # otra persona sí genera la suya
        self.assertEqual(len(self.alertas.listar(self.admin)[0]), 2)

    def test_sos_mensaje_demasiado_largo(self):
        with self.assertRaises(DatosInvalidosError):
            self.alertas.crear(self.ana, "x" * 301)
        with self.assertRaises(DatosInvalidosError):
            self.alertas.crear(self.ana, 123)

    def test_administrador_marca_la_alerta_como_atendida(self):
        alerta, _ = self.alertas.crear(self.ana)
        atendida = self.alertas.atender(self.admin, alerta["id"])
        self.assertTrue(atendida["atendida"])
        self.assertIsNotNone(atendida["atendida_en"])
        pendientes, atendidas = self.alertas.listar(self.admin)
        self.assertEqual((pendientes, [a["id"] for a in atendidas]), ([], [alerta["id"]]))
        self.assertIsNone(self.alertas.pendiente_de(self.ana))
        self.assertTrue(self.alertas.atender(self.admin, alerta["id"])["atendida"])   # repetir no falla
        with self.assertRaises(IndexError):
            self.alertas.atender(self.admin, 999)
        _, nueva = self.alertas.crear(self.ana)                             # ya puede pedir ayuda de nuevo
        self.assertTrue(nueva)



class PruebasCancelarYReprogramar(unittest.TestCase):
    """El administrador cancela o reprograma citas de los usuarios (reloj fijo: hoy 23-oct-2026 10:00)."""

    def setUp(self):
        self.bd = BaseDatos()
        usuarios = ServicioUsuarios(self.bd)
        usuarios.asegurar_administrador("ClaveAdmin123")
        self.admin = usuarios.iniciar_sesion("hydisa123@gmail.com", "ClaveAdmin123")
        self.ana = usuarios.registrar("Ana", "ana@mail.com", "clave12345")
        self.luis = usuarios.registrar("Luis", "luis@mail.com", "clave12345")
        self.agenda = ServicioSesiones(self.bd, ahora=lambda: AHORA)
        self.a = self.agenda.crear_bloque(self.admin, MANANA, "09:00", "09:30")["id"]
        self.b = self.agenda.crear_bloque(self.admin, MANANA, "09:30", "10:00")["id"]
        self.c = self.agenda.crear_bloque(self.admin, "2026-10-26", "14:00", "14:30")["id"]
        self.agenda.reservar(self.ana, self.a, "Hábitos de descanso")

    def libres(self):
        return [x["id"] for x in self.agenda.disponibles(self.luis)]

    def test_solo_el_administrador_cancela_o_reprograma(self):
        for accion in (lambda: self.agenda.cancelar_cita(self.ana, self.a),
                       lambda: self.agenda.reprogramar(self.ana, self.a, self.c)):
            with self.assertRaises(PermisoDenegadoError):
                accion()

    def test_cancelar_libera_el_horario_y_borra_la_cita_del_usuario(self):
        self.assertNotIn(self.a, self.libres())
        r = self.agenda.cancelar_cita(self.admin, self.a)
        self.assertEqual((r["reservado"], r["tema"]), (False, ""))
        self.assertIn(self.a, self.libres())                 # vuelve a ser reservable
        self.assertEqual(self.agenda.mias(self.ana), [])      # y desaparece de las citas de Ana
        self.assertTrue(self.agenda.reservar(self.luis, self.a)["reservado"])

    def test_cancelar_exige_una_cita_existente_y_futura(self):
        with self.assertRaises(HorarioNoDisponibleError):     # libre: no hay nada que cancelar
            self.agenda.cancelar_cita(self.admin, self.b)
        with self.assertRaises(IndexError):
            self.agenda.cancelar_cita(self.admin, 99999)
        self.agenda.reservar(self.ana, self.c, "x")
        self.agenda = ServicioSesiones(self.bd, ahora=lambda: datetime(2026, 10, 26, 14, 10))   # la cita ya empezó
        with self.assertRaises(HorarioNoDisponibleError):
            self.agenda.cancelar_cita(self.admin, self.c)

    def test_reprogramar_mueve_la_cita_y_actualiza_ambos_horarios(self):
        r = self.agenda.reprogramar(self.admin, self.a, self.c)
        self.assertFalse(r["anterior"]["reservado"])
        self.assertTrue(r["nueva"]["reservado"])
        self.assertIn(self.a, self.libres())                  # el anterior se libera
        self.assertNotIn(self.c, self.libres())               # el nuevo queda bloqueado
        mias = self.agenda.mias(self.ana)
        self.assertEqual([(m["id"], m["tema"]) for m in mias], [(self.c, "Hábitos de descanso")])   # conserva el tema

    def test_reprogramar_no_acepta_horarios_ocupados_pasados_ni_inexistentes(self):
        self.agenda.reservar(self.luis, self.b, "otro")
        with self.assertRaises(HorarioNoDisponibleError):     # ocupado
            self.agenda.reprogramar(self.admin, self.a, self.b)
        pasado = self.bd.ejecutar(
            "INSERT INTO disponibilidad (fecha, hora_inicio, hora_fin, creado_por) VALUES (?,?,?,?)",
            ("2026-10-23", "08:00", "08:30", self.admin.id))
        with self.assertRaises(HorarioNoDisponibleError):     # ya pasó
            self.agenda.reprogramar(self.admin, self.a, pasado)
        with self.assertRaises(IndexError):
            self.agenda.reprogramar(self.admin, self.a, 99999)
        with self.assertRaises(DatosInvalidosError):          # mismo horario
            self.agenda.reprogramar(self.admin, self.a, self.a)
        with self.assertRaises(HorarioNoDisponibleError):     # origen sin cita
            self.agenda.reprogramar(self.admin, self.c, self.b)
        self.assertEqual([m["id"] for m in self.agenda.mias(self.ana)], [self.a])     # nada cambió

    def test_reprogramar_no_cruza_otra_sesion_de_la_misma_persona(self):
        self.agenda.reservar(self.ana, self.c, "otra")        # Ana tiene a (09:00) y c (lunes 14:00)
        otro = self.bd.ejecutar(      # dato "crudo" (el servicio no deja publicar bloques cruzados): segunda barrera
            "INSERT INTO disponibilidad (fecha, hora_inicio, hora_fin, creado_por) VALUES (?,?,?,?)",
            ("2026-10-26", "14:15", "14:45", self.admin.id))
        with self.assertRaises(HorarioNoDisponibleError):
            self.agenda.reprogramar(self.admin, self.a, otro)

if __name__ == "__main__":
    unittest.main()
