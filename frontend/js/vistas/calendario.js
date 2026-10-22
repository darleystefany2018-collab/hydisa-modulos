/* ==================================================================
   PANTALLA "CALENDARIO" (acceso rápido "Calendario")
   Para qué sirve: muestra la ruta completa con la fecha de cada día,
   marcando los días hechos, el de hoy y los que faltan. Tocar un día
   abre su actividad.
   ================================================================== */
App.vistas.calendario = {
  titulo: "Calendario de la ruta",
  pintar() {
    const hoy = App.diaActual();
    const celdas = App.ACTIVIDADES.map((a, i) => {
      const n = i + 1, f = App.fechaDelDia(n);
      const clase = App.estado.completados.includes(n) ? "celda--hecho"
                  : (n === hoy && !App.rutaTerminada()) ? "celda--hoy" : "";
      return `<button class="celda ${clase}" data-dia="${n}" aria-label="Día ${n}: ${esc(a.titulo)}">
        <small>${f.toLocaleDateString("es-CO", { weekday: "short" })}</small>
        <strong>${f.getDate()}</strong>
        <small>${f.toLocaleDateString("es-CO", { month: "short" })}</small>
        <span class="celda__dia">Día ${n}</span>
      </button>`;
    }).join("");
    return `<p class="texto-suave">Tu ruta comenzó el ${App.fechaDeTexto(App.estado.inicioRuta)}.</p>
            <div class="calendario">${celdas}</div>
            <p class="leyenda"><span class="punto punto--hecho"></span>Hecho <span class="punto punto--hoy"></span>Hoy <span class="punto"></span>Pendiente</p>`;
  },
  activar(c) {
    c.querySelectorAll(".celda").forEach((b) => b.addEventListener("click", () => {
      const n = Number(b.dataset.dia), a = App.ACTIVIDADES[n - 1];
      const hecho = App.estado.completados.includes(n);
      App.abrirHoja(`Día ${n}: ${a.titulo}`, `
        <p>${esc(a.descripcion)}</p>
        <p class="texto-chico">${a.minutos} minutos · ${a.tipo} · ${hecho ? "Hecho ✓" : n === App.diaActual() ? "Es tu día de hoy" : "Pendiente"}</p>
        ${n === App.diaActual() && !App.rutaTerminada() ? `<button class="boton" data-ir="actividad">Comenzar actividad</button>` : ""}`);
    }));
  }
};
