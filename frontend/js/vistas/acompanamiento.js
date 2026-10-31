/* ==================================================================
   PANTALLA "ACOMPAÑAMIENTO" (acceso rápido "Acompañamiento")
   Para qué sirve: la persona ve los horarios que el administrador
   publicó, reserva uno (cada sesión dura máximo 30 minutos), ve sus
   próximas sesiones y puede cancelarlas. Solo se pueden reservar los
   bloques publicados y libres; el servidor lo comprueba en cada reserva.
   ================================================================== */
(() => {
  let raiz = null;
  const estado = { dia: null };   // día desplegado (AAAA-MM-DD); se conserva al recargar tras reservar o cancelar

  const falla = (error) => {
    if (error.sesionVencida) { App.mostrarAcceso("Tu sesión terminó. Entra otra vez."); return ""; }
    return error.sinServidor ? error.message + " Ábrela con iniciar_hydisa.bat." : error.message;
  };

  async function cargar() {
    raiz.innerHTML = `<p class="vacio">Cargando…</p>`;
    try {
      pintar(await App.api.sesiones());
    } catch (error) {
      const texto = falla(error);
      if (texto) raiz.innerHTML = `<p class="mensaje mensaje--error" role="alert">${esc(texto)}</p>`;
    }
  }

  function pintar({ disponibles, mias }) {
    const misSesiones = mias.length ? mias.map((s) => `
      <li class="item item--registro">
        <span class="animo__emoji">${icono("i-heart")}</span>
        <span class="item__texto"><strong>${esc(App.rangoBloque(s))}</strong><small>${esc(s.tema || "Sin tema")}</small></span>
        <button class="icono-btn" data-cancelar="${Number(s.id)}" aria-label="Cancelar sesión">${icono("i-trash")}</button>
      </li>`).join("") : `<li class="vacio">No tienes sesiones agendadas.</li>`;

    /* Los horarios libres se muestran por día con el componente compartido (js/agenda_dias.js):
       primero los días; las horas de un día aparecen al elegirlo. */
    const horarios = disponibles.length ? App.agendaDias.html(disponibles, estado, {
      resumen: (delDia) => `${delDia.length} ${delDia.length === 1 ? "horario libre" : "horarios libres"}`,
      hora: (b) => `<button class="horario" data-reservar="${Number(b.id)}" data-texto="${esc(App.rangoBloque(b))}">${esc(b.inicio)} – ${esc(b.fin)}</button>`
    }) : `<p class="vacio">Por ahora no hay horarios publicados. Vuelve más tarde.</p>`;

    raiz.innerHTML = `
      <section class="tarjeta">
        <h3 class="tarjeta__titulo">Horarios disponibles</h3>
        <p class="texto-chico">Cada sesión dura máximo 30 minutos. Elige un día para ver sus horas y reserva la que prefieras.</p>
        ${horarios}
      </section>
      <h3 class="subtitulo" style="margin-top:16px">Mis próximas sesiones</h3>
      <ul class="lista">${misSesiones}</ul>`;

    App.agendaDias.activar(raiz, estado);
    raiz.querySelectorAll("[data-reservar]").forEach((b) =>
      b.addEventListener("click", () => abrirReserva(Number(b.dataset.reservar), b.dataset.texto)));
    raiz.querySelectorAll("[data-cancelar]").forEach((b) => b.addEventListener("click", async () => {
      if (!confirm("¿Cancelar esta sesión? El horario quedará libre para otra persona.")) return;
      try {
        await App.api.cancelarReserva(Number(b.dataset.cancelar));
        App.aviso("Sesión cancelada");
      } catch (error) { const t = falla(error); if (t) App.aviso(t); }
      cargar();
    }));
  }

  function abrirReserva(id, texto) {
    const temas = App.TEMAS_SESION.map((t) => `<option>${esc(t)}</option>`).join("");
    App.abrirHoja("Reservar sesión", `
      <p><strong>${esc(texto)}</strong></p>
      <label class="campo"><span>Tema</span><select id="temaSesion">${temas}</select></label>
      <div id="mensajesReserva"></div>
      <button id="btnReservar" class="boton">Confirmar reserva</button>`, (cuerpo) => {
      cuerpo.querySelector("#btnReservar").addEventListener("click", async (e) => {
        const boton = e.currentTarget;
        boton.disabled = true;
        try {
          await App.api.reservar(id, cuerpo.querySelector("#temaSesion").value);
          App.agregarNotificacion(`Reservaste una sesión: ${texto}.`);
          App.guardar();
          App.cerrarHoja();
          App.aviso("Sesión reservada");
          cargar();
        } catch (error) {
          boton.disabled = false;
          const t = falla(error);
          if (t) cuerpo.querySelector("#mensajesReserva").innerHTML = `<p class="mensaje mensaje--error" role="alert">${esc(t)}</p>`;
          if (error.codigo === 409 || error.codigo === 404) cargar();     // el horario cambió: refresca la lista
        }
      });
    });
  }

  App.vistas.acompanamiento = {
    titulo: "Mis sesiones",
    pintar: () => `<div id="acompanamiento"></div>`,
    activar(c) { raiz = c.querySelector("#acompanamiento"); estado.dia = null; cargar(); }
  };
})();
