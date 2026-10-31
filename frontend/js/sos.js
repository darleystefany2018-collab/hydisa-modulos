/* ==================================================================
   MÓDULO SOS - BOTÓN DE AYUDA
   Para qué sirve: un botón flotante visible en todas las pantallas del
   usuario. Si necesita apoyo inmediato (por su estado de ánimo o por una
   duda urgente) lo pulsa, escribe si quiere qué le pasa y se envía una
   solicitud de ayuda: el administrador la ve como alerta en su módulo.
   Importante: HYDISA no es un servicio de emergencias y la pantalla lo
   dice claramente. El botón no existe para el administrador.
   ================================================================== */
(() => {
  const AVISO_EMERGENCIA = `<p class="sos__aviso">HYDISA no es un servicio de emergencias y la respuesta puede tardar.
    Si tu vida o la de otra persona está en peligro, llama ahora a la línea de emergencias <strong>123</strong>.</p>`;

  const falloGeneral = (error) => {
    if (error.sesionVencida) { App.cerrarHoja(); return App.mostrarAcceso("Tu sesión terminó. Entra otra vez."); }
    return error.sinServidor ? error.message + " Ábrela con iniciar_hydisa.bat." : error.message;
  };

  /* Pantalla de "solicitud ya enviada" (también se usa si ya había una pendiente) */
  const pintarEnviada = (alerta, nueva) => `
    <p class="mensaje mensaje--ok">${nueva ? "Tu solicitud fue enviada" : "Ya tienes una solicitud pendiente"}
      (${esc(App.fechaHora(alerta.creado_en))}). El administrador la verá en su panel.</p>
    <p class="texto-suave">Mientras esperas, respira lento: inhala 4 segundos, sostén 4 y exhala 4. Puedes hacerlo guiado en <strong>Recursos</strong>.</p>
    ${AVISO_EMERGENCIA}
    <button class="boton boton--sec" data-ir="recursos">Ir a la respiración guiada</button>`;

  async function abrir() {
    App.abrirHoja("Necesito ayuda ahora", `<p class="vacio">Cargando…</p>`);
    try {
      const { pendiente } = await App.api.sosEstado();
      if (pendiente) return App.abrirHoja("Necesito ayuda ahora", pintarEnviada(pendiente, false));
      App.abrirHoja("Necesito ayuda ahora", `
        <p class="texto-suave">Cuéntanos si quieres qué está pasando. Es opcional: también puedes enviar la solicitud sin escribir nada.</p>
        <label class="campo"><span>¿Qué está pasando? (opcional)</span>
          <textarea id="mensajeSos" rows="4" maxlength="300" placeholder="Me siento… / Tengo una duda urgente sobre…"></textarea></label>
        <div id="mensajesSos"></div>
        <button id="btnEnviarSos" class="boton">Enviar solicitud de ayuda</button>
        ${AVISO_EMERGENCIA}`, (cuerpo) => {
        cuerpo.querySelector("#btnEnviarSos").addEventListener("click", async (e) => {
          const enviar = e.currentTarget;
          enviar.disabled = true;
          try {
            const r = await App.api.sos(cuerpo.querySelector("#mensajeSos").value);
            if (r.nueva) { App.agregarNotificacion("Enviaste una solicitud de ayuda (SOS)."); App.guardar(); }
            App.abrirHoja("Necesito ayuda ahora", pintarEnviada(r.alerta, r.nueva));
          } catch (error) {
            enviar.disabled = false;
            const texto = falloGeneral(error);
            if (texto) cuerpo.querySelector("#mensajesSos").innerHTML = `<p class="mensaje mensaje--error" role="alert">${esc(texto)}</p>`;
          }
        });
      });
    } catch (error) {
      const texto = falloGeneral(error);
      if (texto) App.abrirHoja("Necesito ayuda ahora", `<p class="mensaje mensaje--error" role="alert">${esc(texto)}</p>${AVISO_EMERGENCIA}`);
    }
  }

  /* ---------- Botón flotante movible ----------
     Siempre visible (position: fixed), pero la persona puede arrastrarlo (mouse o dedo) o moverlo con
     las flechas del teclado para que no tape nada. Se queda dentro de la app, debajo de la cabecera y
     encima de la barra inferior, y recuerda su lugar. Un toque o clic simple sigue abriendo la ayuda. */
  function hacerFlotante(boton) {
    const CLAVE = "hydisa_sos_pos_v1", MARGEN = 8, UMBRAL = 6, PASO = 16;
    const app = document.querySelector(".app");
    /* pos = distancia al borde derecho de la app (dx) y al borde inferior de la pantalla (dy):
       los mismos valores que tenía el CSS original (16 y 92), por eso sin mover se ve igual que antes. */
    let pos = null, inicio = null, movio = false;
    try {
      const g = JSON.parse(localStorage.getItem(CLAVE) || "null");
      if (g && isFinite(g.dx) && isFinite(g.dy)) pos = { dx: g.dx, dy: g.dy };
    } catch (e) { /* sin almacenamiento: no recuerda el lugar */ }

    const limites = () => {
      const r = app.getBoundingClientRect(), tam = boton.offsetWidth || 58;
      const cab = document.querySelector(".cabecera"), nav = $("navegacion");
      const minX = r.left + MARGEN, minY = (cab ? cab.offsetHeight : 0) + MARGEN;
      return { r, tam, minX, minY,
        maxX: Math.max(minX, r.right - tam - MARGEN),
        maxY: Math.max(minY, innerHeight - (nav ? nav.offsetHeight : 70) - tam - MARGEN) };
    };
    const colocar = () => {                     // dibuja el botón en pos (ajustado a los límites actuales)
      if (!pos) return;                         // nunca movido: manda el CSS
      const l = limites();
      if (!l.r.width) return;                   // la app está oculta (pantalla de acceso): se recoloca al mostrarse
      const x = Math.min(Math.max(l.r.right - pos.dx - l.tam, l.minX), l.maxX);
      const y = Math.min(Math.max(innerHeight - pos.dy - l.tam, l.minY), l.maxY);
      Object.assign(boton.style, { left: x + "px", top: y + "px", right: "auto", bottom: "auto" });
    };
    const mover = (x, y) => {                   // x, y = esquina superior izquierda deseada
      const l = limites();
      x = Math.min(Math.max(x, l.minX), l.maxX); y = Math.min(Math.max(y, l.minY), l.maxY);
      pos = { dx: l.r.right - x - l.tam, dy: innerHeight - y - l.tam };
      colocar();
    };
    const guardar = () => { try { localStorage.setItem(CLAVE, JSON.stringify(pos)); } catch (e) { /* nada */ } };

    boton.addEventListener("pointerdown", (e) => {
      if (e.button > 0) return;                 // solo botón principal / dedo
      const r = boton.getBoundingClientRect();
      inicio = { px: e.clientX, py: e.clientY, x: r.left, y: r.top };
      movio = false;
      boton.setPointerCapture(e.pointerId);
    });
    boton.addEventListener("pointermove", (e) => {
      if (!inicio) return;
      const mx = e.clientX - inicio.px, my = e.clientY - inicio.py;
      if (!movio && Math.hypot(mx, my) < UMBRAL) return;   // un toque corto no es arrastre
      movio = true; boton.classList.add("sos--arrastrando");
      mover(inicio.x + mx, inicio.y + my);
    });
    const soltar = () => { inicio = null; boton.classList.remove("sos--arrastrando"); if (movio) guardar(); };
    boton.addEventListener("pointerup", soltar);
    boton.addEventListener("pointercancel", () => { soltar(); movio = false; });
    /* Si fue un arrastre, el "clic" que sigue al soltar no debe abrir la ayuda.
       Se registra ANTES que el de abrir() para poder detenerlo. */
    boton.addEventListener("click", (e) => { if (movio) { e.stopImmediatePropagation(); movio = false; } });

    boton.addEventListener("keydown", (e) => {   // accesibilidad: flechas mueven el botón
      const d = { ArrowLeft: [-PASO, 0], ArrowRight: [PASO, 0], ArrowUp: [0, -PASO], ArrowDown: [0, PASO] }[e.key];
      if (!d) return;
      e.preventDefault();
      const r = boton.getBoundingClientRect();
      mover(r.left + d[0], r.top + d[1]); guardar();
    });

    window.addEventListener("resize", colocar);                       // girar el celular o cambiar el tamaño de la ventana
    if (window.ResizeObserver) new ResizeObserver(colocar).observe(app); // la app aparece al iniciar sesión
    colocar();
  }

  hacerFlotante($("btnSOS"));
  $("btnSOS").addEventListener("click", abrir);
})();
