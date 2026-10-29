/* ==================================================================
   PANTALLA "ACOMPAÑAMIENTO" (acceso rápido "Acompañamiento")
   Para qué sirve: la persona ve los horarios que el administrador
   publicó, reserva uno (cada sesión dura máximo 30 minutos), ve sus
   próximas sesiones y puede cancelarlas. Solo se pueden reservar los
   bloques publicados y libres; el servidor lo comprueba en cada reserva.
   ================================================================== */
(() => {
  let raiz = null;

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

    /* Los horarios libres se agrupan por día */
    const porDia = {};
    disponibles.forEach((b) => (porDia[b.fecha] = porDia[b.fecha] || []).push(b));
    const horarios = Object.keys(porDia).length ? Object.entries(porDia).map(([fecha, bloques]) => `
      <p class="texto-chico" style="margin:12px 0 6px">${esc(App.fechaDeTexto(fecha))}</p>
      <div class="horarios">${bloques.map((b) => `
        <button class="horario" data-reservar="${Number(b.id)}" data-texto="${esc(App.rangoBloque(b))}">${esc(b.inicio)} – ${esc(b.fin)}</button>`).join("")}</div>`).join("")
      : `<p class="vacio">Por ahora no hay horarios publicados. Vuelve más tarde.</p>`;

    raiz.innerHTML = `
      <section class="tarjeta">
        <h3 class="tarjeta__titulo">Horarios disponibles</h3>
        <p class="texto-chico">Cada sesión dura máximo 30 minutos. Elige un horario para reservarlo.</p>
        ${horarios}
      </section>
      <h3 class="subtitulo" style="margin-top:16px">Mis próximas sesiones</h3>
      <ul class="lista">${misSesiones}</ul>`;

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
    activar(c) { raiz = c.querySelector("#acompanamiento"); cargar(); }
  };
})();
