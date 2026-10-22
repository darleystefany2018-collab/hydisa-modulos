/* ==================================================================
   PANTALLA "EVOLUCIÓN" (acceso rápido "Mi evolución")
   Para qué sirve: resume el progreso: días completados, porcentaje,
   registros hechos, promedio de ánimo, y una gráfica con los últimos
   estados de ánimo registrados.
   ================================================================== */
App.vistas.evolucion = {
  titulo: "Mi evolución",
  pintar() {
    const regs = App.estado.registros;
    const promedio = regs.length ? (regs.reduce((s, r) => s + r.animo, 0) / regs.length).toFixed(1) : "—";

    /* Gráfica de barras con los últimos 7 registros (del más viejo al más nuevo) */
    const ultimos = regs.slice(0, 7).reverse();
    let grafica = `<p class="vacio">Guarda registros en la sección Registro para ver tu gráfica.</p>`;
    if (ultimos.length) {
      const ancho = 300, alto = 130, hueco = ancho / ultimos.length;
      const barras = ultimos.map((r, i) => {
        const h = (r.animo / 5) * (alto - 24);
        const w = Math.min(hueco * 0.64, 34), x = i * hueco + (hueco - w) / 2;   // barras delgadas y centradas
        return `<rect x="${x}" y="${alto - 18 - h}" width="${w}" height="${h}" rx="6" fill="var(--verde-medio)"/>
                <text x="${x + w / 2}" y="${alto - 4}" text-anchor="middle" font-size="9" fill="#6d7a73">${App.fechaDiaMes(r.fecha)}</text>
                <text x="${x + w / 2}" y="${alto - 22 - h}" text-anchor="middle" font-size="11">${App.ANIMOS[r.animo - 1].emoji}</text>`;
      }).join("");
      grafica = `<svg viewBox="0 0 ${ancho} ${alto}" class="grafica" role="img" aria-label="Estado de ánimo en los últimos registros">${barras}</svg>`;
    }

    return `
      <section class="estadisticas">
        <div class="estadistica"><strong>${App.diasCompletados()}/${TOTAL_DIAS}</strong><span>Días completados</span></div>
        <div class="estadistica"><strong>${App.porcentaje()} %</strong><span>De tu ruta</span></div>
        <div class="estadistica"><strong>${regs.length}</strong><span>Registros</span></div>
        <div class="estadistica"><strong>${promedio}</strong><span>Ánimo promedio (1-5)</span></div>
      </section>
      <section class="tarjeta">
        <h3 class="tarjeta__titulo">Tu estado de ánimo</h3>${grafica}
      </section>
      <section class="tarjeta">
        <h3 class="tarjeta__titulo">Progreso de la ruta</h3>
        <div class="barra"><div class="barra__relleno" style="width:${App.porcentaje()}%"></div></div>
        <p class="texto-suave" style="margin-top:8px">${App.rutaTerminada() ? "¡Ruta completa!" : `Hoy te toca el día ${App.diaActual()}.`}</p>
      </section>`;
  }
};
