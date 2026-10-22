/* ==================================================================
   PANTALLA "ACOMPAÑAMIENTO" (acceso rápido "Acompañamiento")
   Para qué sirve: la persona agenda sesiones de acompañamiento (fecha,
   hora y tema), ve su lista de sesiones próximas y puede cancelarlas.
   ================================================================== */
App.vistas.acompanamiento = {
  titulo: "Mis sesiones",
  pintar() {
    const horas = ["08:00", "09:00", "10:00", "11:00", "14:00", "15:00", "16:00", "17:00"]
      .map((h) => `<option value="${h}">${h}</option>`).join("");
    const temas = App.TEMAS_SESION.map((t) => `<option>${t}</option>`).join("");
    const sesiones = [...App.estado.sesiones].sort((a, b) => (a.fecha + a.hora).localeCompare(b.fecha + b.hora));
    const lista = sesiones.length
      ? sesiones.map((s) => `<li class="item item--registro">
          <span class="animo__emoji">${icono("i-heart")}</span>
          <span class="item__texto"><strong>${App.fechaDeTexto(s.fecha)} · ${s.hora}</strong><small>${esc(s.tema)}</small></span>
          <button class="icono-btn" data-cancelar="${s.id}" aria-label="Cancelar sesión">${icono("i-trash")}</button>
        </li>`).join("")
      : `<li class="vacio">No tienes sesiones agendadas.</li>`;

    return `
      <section class="tarjeta">
        <h3 class="tarjeta__titulo">Agendar una sesión</h3>
        <label class="campo"><span>Fecha</span><input id="fechaSesion" type="date" min="${App.hoyISO()}"></label>
        <label class="campo"><span>Hora</span><select id="horaSesion">${horas}</select></label>
        <label class="campo"><span>Tema</span><select id="temaSesion">${temas}</select></label>
        <button id="btnAgendar" class="boton">Agendar sesión</button>
      </section>
      <h3 class="subtitulo">Próximas sesiones</h3>
      <ul class="lista">${lista}</ul>`;
  },
  activar(c) {
    c.querySelector("#btnAgendar").addEventListener("click", () => {
      const fecha = c.querySelector("#fechaSesion").value;
      if (!fecha) return App.aviso("Elige una fecha");
      if (fecha < App.hoyISO()) return App.aviso("La fecha no puede ser anterior a hoy");
      App.estado.sesiones.push({ id: App.nuevoId(), fecha, hora: c.querySelector("#horaSesion").value,
                                 tema: c.querySelector("#temaSesion").value });
      App.agregarNotificacion(`Agendaste una sesión para el ${App.fechaDeTexto(fecha)}.`);
      App.guardar();
      App.aviso("Sesión agendada");
      App.mostrar();
    });
    c.querySelectorAll("[data-cancelar]").forEach((b) => b.addEventListener("click", () => {
      App.estado.sesiones = App.estado.sesiones.filter((s) => String(s.id) !== b.dataset.cancelar);
      App.guardar();
      App.aviso("Sesión cancelada");
      App.mostrar();
    }));
  }
};
