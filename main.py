"""Programa principal (consola). Ejecutar con:  python main.py"""
from hydisa.base_datos import BaseDatos
from hydisa.config import RUTA_BD
from hydisa.excepciones import HydisaError
from hydisa.servicio_reportes import ServicioReportes
from hydisa.servicio_usuarios import ServicioUsuarios


def mostrar_palabras_clave(reportes, ruta_pdf):
    """Muestra qué palabras clave encontró el motor en el PDF (con o sin tildes)."""
    texto = reportes.pdf.extraer_texto(ruta_pdf)
    encontradas = reportes.motor.palabras_detectadas(texto)
    print("\nPalabras clave encontradas:")
    for categoria, palabras in encontradas.items():
        detalle = ", ".join(f"{p} (x{n})" for p, n in palabras.items())
        print(f"  {categoria}: {detalle}")


def menu_usuario(usuario, reportes):
    while True:
        print(f"\n--- Hola, {usuario.nombre} ---")
        print("1. Cargar PDF   2. Historial   3. Ver ruta   4. Marcar actividad   5. Exportar PDF   0. Salir")
        opcion = input("Opción: ").strip()
        try:
            if opcion == "1":
                ruta_pdf = input("Ruta del PDF: ").strip().strip('"')
                rid = reportes.analizar_pdf(usuario, ruta_pdf)
                print(f"Reporte {rid} analizado. Ruta generada.")
                mostrar_palabras_clave(reportes, ruta_pdf)
            elif opcion == "2":
                for f in reportes.historial(usuario):
                    print(f"  #{f['id']}  {f['nombre_archivo']}  ({f['creado_en']})")
            elif opcion in ("3", "4", "5"):
                rid = int(input("N.º de reporte: "))
                if opcion == "3":
                    for n, i in enumerate(reportes.obtener_ruta(usuario, rid), 1):
                        print(f"  {n}. [{'x' if i.cumplida else ' '}] ({i.categoria}) {i.actividad}")
                    print(f"  Progreso: {reportes.progreso(usuario, rid)}%")
                elif opcion == "4":
                    reportes.marcar_cumplida(usuario, rid, int(input("N.º de actividad: ")))
                else:
                    print("PDF creado en:", reportes.exportar_pdf(usuario, rid))
            elif opcion == "0":
                return
        except (HydisaError, ValueError, IndexError) as error:
            print("Error:", error)


def main():
    bd = BaseDatos(RUTA_BD)
    usuarios, reportes = ServicioUsuarios(bd), ServicioReportes(bd)
    while True:
        print("\n=== HYDISA ===\n1. Registrarse   2. Iniciar sesión   0. Salir")
        opcion = input("Opción: ").strip()
        try:
            if opcion == "1":
                usuarios.registrar(input("Nombre: "), input("Correo: "), input("Contraseña: "))
                print("Registro exitoso. Ahora inicia sesión.")
            elif opcion == "2":
                menu_usuario(usuarios.iniciar_sesion(input("Correo: "), input("Contraseña: ")), reportes)
            elif opcion == "0":
                break
        except HydisaError as error:
            print("Error:", error)
    bd.cerrar()


if __name__ == "__main__":
    main()