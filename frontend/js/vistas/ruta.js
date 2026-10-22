/* ==================================================================
   PANTALLA "MI RUTA" (y "Ver todas las actividades")
   Para qué sirve: lista los 11 días con su actividad. Los días hechos y
   el de hoy se pueden abrir para leer el detalle; los futuros esperan.
   ================================================================== */
App.vistas.ruta = {
  titulo: "Mi ruta",
  pintar() {
    const hoy = App.diaActual();
    const items = App.ACTIVIDADES.map((a, i) => {
      const n = i + 1;
      const hecho = App.estado.completados.includes(n);
      const esHoy = n === hoy && !App.rutaTerminada();
      const estado = hecho ? "Hecho" : esHoy ? "Hoy" : "Pendiente";
      const clase = hecho ? "item--hecho" : esHoy ? "item--hoy" : "item--pendiente";
      return `
        <li class="item item--dia ${clase}">
          <button class="item__boton" data-dia="${n}" ${!hecho && !esHoy ? "disabled" : ""}>
            <span class="item__num">${hecho ? icono("i-check") : n}</span>
            <span class="item__texto"><strong>${esc(a.titulo)}</strong><small>${a.minutos} min · ${a.tipo}</small></span>
            <span class="etiqueta etiqueta--${estado.toLowerCase()}">${estado}</span>
          </button>
          <p class="item__detalle" hidden>${esc(a.descripcion)}</p>
        </li>`;
    }).join("");
    return `<p class="texto-suave">Llevas ${App.diasCompletados()} de ${TOTAL_DIAS} días (${App.porcentaje()} %).</p>
            <ul class="lista">${items}</ul>`;
  },
  activar(c) {
    /* Tocar un día abre o cierra su descripción; tocar el de hoy ofrece comenzarlo */
    c.querySelectorAll(".item__boton").forEach((boton) =>
      boton.addEventListener("click", () => {
        const detalle = boton.parentElement.querySelector(".item__detalle");
        detalle.hidden = !detalle.hidden;
        const esHoy = boton.parentElement.classList.contains("item--hoy");
        if (esHoy && !boton.parentElement.querySelector(".enlace")) {
          detalle.insertAdjacentHTML("afterend", `<button class="enlace" data-ir="actividad">Comenzar esta actividad ${icono("i-chevron", "icono icono--mini")}</button>`);
        }
      }));
  }
};
