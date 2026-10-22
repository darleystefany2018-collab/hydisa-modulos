/* ==================================================================
   MÓDULO 4 - INTENCIÓN PERSONAL
   Para qué sirve: la persona elige una intención sugerida o escribe la
   suya. Se guarda y se muestra en el inicio y en el perfil.
   ================================================================== */
App.abrirIntencion = () => {
  const actual = App.estado.intencion;
  const opciones = App.INTENCIONES.map((texto, i) => `
    <button class="opcion ${texto === actual ? "opcion--activa" : ""}" data-indice="${i}">${esc(texto)}</button>`).join("");

  const html = `
    <div class="opciones">${opciones}</div>
    <label class="campo">
      <span>O escribe la tuya</span>
      <input id="intencionPropia" type="text" maxlength="80" placeholder="Ej.: Moverme un poco cada día">
    </label>
    <button id="btnGuardarIntencion" class="boton">Guardar mi intención</button>`;

  App.abrirHoja("Tu intención", html, (cuerpo) => {
    const guardar = (texto) => {
      App.estado.intencion = texto;
      App.agregarNotificacion("Cambiaste tu intención.");
      App.guardar();
      App.cerrarHoja();
      App.aviso("Intención actualizada");
      App.mostrar();                         // vuelve a dibujar la pantalla con el cambio
    };
    cuerpo.querySelectorAll(".opcion").forEach((b) =>
      b.addEventListener("click", () => guardar(App.INTENCIONES[b.dataset.indice])));
    cuerpo.querySelector("#btnGuardarIntencion").addEventListener("click", () => {
      const propia = cuerpo.querySelector("#intencionPropia").value.trim();
      if (!propia) return App.aviso("Elige una opción o escribe tu intención");
      guardar(propia);
    });
  });
};
