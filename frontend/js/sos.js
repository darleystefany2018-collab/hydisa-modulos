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

  $("btnSOS").addEventListener("click", abrir);
})();
