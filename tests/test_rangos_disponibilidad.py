"""Pruebas de la publicación de disponibilidad por rangos libres (reloj fijo)."""
import unittest
from datetime import datetime

from hydisa.base_datos import BaseDatos, ErrorIntegridad
from hydisa.config import DURACION_SESION_MIN, HORA_APERTURA, HORA_CIERRE
from hydisa.excepciones import DatosInvalidosError, HorarioNoDisponibleError, PermisoDenegadoError
from hydisa.servicio_sesiones import ServicioSesiones
from hydisa.servicio_usuarios import ServicioUsuarios

AHORA = datetime(2026, 10, 23, 10, 0)
MANANA = "2026-10-24"


def horas(resultado):
    return [(b["inicio"], b["fin"]) for b in resultado["creados"]]


class PruebasRangos(unittest.TestCase):
    def setUp(self):
        self.bd = BaseDatos()
        usuarios = ServicioUsuarios(self.bd)
        usuarios.asegurar_administrador("ClaveAdmin123")
        self.admin = usuarios.iniciar_sesion("hydisa123@gmail.com", "ClaveAdmin123")
        self.ana = usuarios.registrar("Ana", "ana@mail.com", "clave12345")
        self.agenda = ServicioSesiones(self.bd, ahora=lambda: AHORA)

    def filas(self, fecha=MANANA):
        return self.bd.consultar("SELECT * FROM disponibilidad WHERE fecha = ? ORDER BY hora_inicio", (fecha,))

    # ---------- rangos ----------
    def test_rango_de_una_hora_genera_dos_espacios(self):
        r = self.agenda.publicar_rango(self.admin, MANANA, "09:00", "10:00")
        self.assertEqual(horas(r), [("09:00", "09:30"), ("09:30", "10:00")])
        self.assertTrue(all(b["minutos"] == DURACION_SESION_MIN and not b["reservado"] for b in r["creados"]))

    def test_rango_de_varias_horas(self):
        r = self.agenda.publicar_rango(self.admin, MANANA, "14:00", "18:00")
        self.assertEqual(len(r["creados"]), 8)
        self.assertEqual((horas(r)[0], horas(r)[-1]), (("14:00", "14:30"), ("17:30", "18:00")))
        for anterior, siguiente in zip(horas(r), horas(r)[1:]):                 # pegados, sin huecos ni cruces
            self.assertEqual(anterior[1], siguiente[0])

    def test_rango_que_no_es_multiplo_de_la_duracion(self):
        r = self.agenda.publicar_rango(self.admin, MANANA, "09:00", "09:45")
        self.assertEqual(horas(r), [("09:00", "09:30"), ("09:30", "09:45")])      # el último es más corto
        r = self.agenda.publicar_rango(self.admin, MANANA, "11:00", "11:32")
        self.assertEqual((horas(r), r["sobrante_min"]), ([("11:00", "11:30")], 2))   # 2 min no alcanzan para una cita
        with self.assertRaises(DatosInvalidosError):
            self.agenda.publicar_rango(self.admin, MANANA, "12:00", "12:03")      # menos del mínimo

    def test_todo_el_dia_va_de_la_apertura_al_cierre(self):
        r = self.agenda.publicar_rango(self.admin, MANANA, todo_el_dia=True)
        self.assertEqual((horas(r)[0][0], horas(r)[-1][1]), (HORA_APERTURA, HORA_CIERRE))
        esperados = (int(HORA_CIERRE[:2]) - int(HORA_APERTURA[:2])) * 60 // DURACION_SESION_MIN
        self.assertEqual(len(r["creados"]), esperados)
        # inicio y fin que mande el cliente se ignoran cuando es todo el día
        otro = self.agenda.publicar_rango(self.admin, "2026-10-25", "10:00", "10:30", todo_el_dia=True)
        self.assertEqual(len(otro["creados"]), esperados)

    def test_todo_el_dia_de_hoy_omite_lo_que_ya_paso(self):
        r = self.agenda.publicar_rango(self.admin, "2026-10-23", todo_el_dia=True)     # ahora son las 10:00
        self.assertEqual(horas(r)[0], ("10:30", "11:00"))                              # 10:00 ya empezó
        self.assertEqual(r["omitidos_pasados"], 5)                                     # 08:00, 08:30, 09:00, 09:30 y 10:00
        with self.assertRaises(DatosInvalidosError):
            self.agenda.publicar_rango(self.admin, "2026-10-23", "08:00", "09:00")      # todo en el pasado

    # ---------- validaciones ----------
    def test_fin_debe_ser_posterior_al_inicio(self):
        for ini, fin in [("10:00", "10:00"), ("10:00", "09:00")]:
            with self.assertRaises(DatosInvalidosError):
                self.agenda.publicar_rango(self.admin, MANANA, ini, fin)
        self.assertEqual(self.filas(), [])

    def test_no_se_sale_del_horario_de_operacion(self):
        for ini, fin in [("07:30", "09:00"), ("17:30", "18:30"), ("19:00", "20:00"), ("00:00", "23:59")]:
            with self.assertRaises(DatosInvalidosError, msg=(ini, fin)):
                self.agenda.publicar_rango(self.admin, MANANA, ini, fin)
        self.agenda.publicar_rango(self.admin, MANANA, HORA_APERTURA, "09:00")           # justo en el límite: sí
        self.agenda.publicar_rango(self.admin, MANANA, "17:00", HORA_CIERRE)
        with self.assertRaises(DatosInvalidosError):                                      # crear_bloque también lo respeta
            self.agenda.crear_bloque(self.admin, "2026-10-25", "18:00", "18:30")

    def test_traslape_se_rechaza_y_no_cambia_nada(self):
        original = self.agenda.publicar_rango(self.admin, MANANA, "10:00", "11:00")
        antes = [dict(f) for f in self.filas()]
        for ini, fin in [("10:00", "11:00"), ("10:30", "12:00"), ("09:00", "10:30"), ("09:00", "12:00")]:
            with self.assertRaises(HorarioNoDisponibleError, msg=(ini, fin)):
                self.agenda.publicar_rango(self.admin, MANANA, ini, fin)
        self.assertEqual([dict(f) for f in self.filas()], antes)                          # ni se borró ni se agregó nada
        self.assertEqual(len(original["creados"]), 2)

    def test_rangos_pegados_y_de_otro_dia_si_se_permiten_y_no_alteran_lo_existente(self):
        a = self.agenda.publicar_rango(self.admin, MANANA, "09:00", "10:00")
        self.agenda.publicar_rango(self.admin, MANANA, "10:00", "11:00")                  # pegado
        self.agenda.publicar_rango(self.admin, "2026-10-25", "09:00", "10:00")            # otro día
        ids_existentes = [b["id"] for b in a["creados"]]
        self.assertEqual([f["id"] for f in self.filas()][:2], ids_existentes)
        self.assertEqual(len(self.filas()), 4)

    def test_solo_el_administrador_publica(self):
        with self.assertRaises(PermisoDenegadoError):
            self.agenda.publicar_rango(self.ana, MANANA, "09:00", "10:00")
        with self.assertRaises(DatosInvalidosError):
            self.agenda.publicar_rango(self.admin, "mañana", "09:00", "10:00")

    # ---------- reemplazo y citas reservadas ----------
    def test_reemplazar_sustituye_solo_lo_libre_y_conserva_las_citas(self):
        base = self.agenda.publicar_rango(self.admin, MANANA, "09:00", "11:00")["creados"]   # 4 espacios
        fuera = self.agenda.publicar_rango(self.admin, MANANA, "14:00", "15:00")["creados"]
        reservada = base[1]                                                                   # 09:30-10:00
        self.agenda.reservar(self.ana, reservada["id"], "Manejo del estrés")
        copia_reserva = dict(self.bd.consultar_uno("SELECT * FROM disponibilidad WHERE id = ?", (reservada["id"],)))

        r = self.agenda.publicar_rango(self.admin, MANANA, "09:00", "11:00", reemplazar=True)
        self.assertEqual((r["reemplazados"], r["conservados"]), (3, 1))
        self.assertEqual(horas(r), [("09:00", "09:30"), ("10:00", "10:30"), ("10:30", "11:00")])   # rodea la cita
        # la cita reservada quedó EXACTAMENTE igual (mismo id, mismo usuario, tema y hora de reserva)
        self.assertEqual(dict(self.bd.consultar_uno("SELECT * FROM disponibilidad WHERE id = ?", (reservada["id"],))), copia_reserva)
        # lo que estaba fuera del rango no se tocó
        self.assertEqual([f["id"] for f in self.filas() if f["hora_inicio"] >= "14:00"], [b["id"] for b in fuera])
        # no hay cruces en toda la agenda del día
        filas = self.filas()
        for x, y in zip(filas, filas[1:]):
            self.assertLessEqual(x["hora_fin"], y["hora_inicio"])

    def test_si_todo_el_rango_esta_reservado_no_se_borra_nada(self):
        bloques = self.agenda.publicar_rango(self.admin, MANANA, "09:00", "10:00")["creados"]
        for b in bloques:
            self.agenda.reservar(self.ana, b["id"])
        antes = [dict(f) for f in self.filas()]
        with self.assertRaises(HorarioNoDisponibleError):
            self.agenda.publicar_rango(self.admin, MANANA, "09:00", "10:00", reemplazar=True)
        self.assertEqual([dict(f) for f in self.filas()], antes)

    def test_las_reservas_no_cambian_al_publicar_mas_disponibilidad(self):
        bloque = self.agenda.publicar_rango(self.admin, MANANA, "09:00", "10:00")["creados"][0]
        self.agenda.reservar(self.ana, bloque["id"], "Hábitos de descanso")
        antes = dict(self.bd.consultar_uno("SELECT * FROM disponibilidad WHERE id = ?", (bloque["id"],)))
        self.agenda.publicar_rango(self.admin, MANANA, "10:00", "12:00")
        self.agenda.publicar_rango(self.admin, "2026-10-25", todo_el_dia=True)
        self.assertEqual(dict(self.bd.consultar_uno("SELECT * FROM disponibilidad WHERE id = ?", (bloque["id"],))), antes)
        self.assertEqual([b["id"] for b in self.agenda.mias(self.ana)], [bloque["id"]])

    def test_vista_de_usuarios_no_cambia(self):
        """Los espacios generados son filas normales de `disponibilidad`: los usuarios los ven y reservan igual que antes."""
        r = self.agenda.publicar_rango(self.admin, MANANA, "09:00", "10:00")
        self.assertEqual([b["id"] for b in self.agenda.disponibles(self.ana)], [b["id"] for b in r["creados"]])
        self.agenda.reservar(self.ana, r["creados"][0]["id"])
        self.assertEqual(len(self.agenda.disponibles(self.ana)), 1)

    # ---------- transacción ----------
    def test_lote_es_todo_o_nada(self):
        self.agenda.crear_bloque(self.admin, MANANA, "09:00", "09:30")
        insertar = "INSERT INTO disponibilidad (fecha, hora_inicio, hora_fin, creado_por) VALUES (?,?,?,?)"
        with self.assertRaises(ErrorIntegridad):
            self.bd.ejecutar_lote([(insertar, (MANANA, "10:00", "10:30", self.admin.id)),
                                   (insertar, (MANANA, "09:00", "09:30", self.admin.id))])   # el 2º viola el UNIQUE
        self.assertEqual([f["hora_inicio"] for f in self.filas()], ["09:00"])                  # el 1º se deshizo


if __name__ == "__main__":
    unittest.main()
