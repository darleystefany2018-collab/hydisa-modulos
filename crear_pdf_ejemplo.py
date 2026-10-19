from reportlab.pdfgen import canvas

lineas = [
    "Reporte Healy de ejemplo",
    "Se observa estres y ansiedad elevados.",
    "Hay falta de sueno y poco descanso.",
    "Se busca equilibrio, armonia y mejor concentracion.",
]
c = canvas.Canvas("datos/reporte_ejemplo.pdf")
for n, linea in enumerate(lineas):
    c.drawString(72, 780 - 20 * n, linea)
c.save()
print("PDF de ejemplo creado en datos/reporte_ejemplo.pdf")