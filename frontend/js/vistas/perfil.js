/* ==================================================================
   PANTALLA "PERFIL" (avatar de la cabecera y pestaña Perfil)
   Para qué sirve: la persona cambia su nombre, revisa su intención y
   su avance, reinicia la ruta o borra todos sus datos.
   ================================================================== */
App.vistas.perfil = {
  titulo: "Mi perfil",
  pintar() {
    const e = App.estado;
    return `
      <section class="tarjeta">
        <label class="campo"><span>Tu nombre</span>
          <input id="campoNombre" type="text" maxlength="30" value="${esc(e.usuario.nombre)}"></label>
        <button id="btnGuardarNombre" class="boton">Guardar nombre</button>
      </section>
      <section class="tarjeta">
        <p class="texto-chico">Tu intención</p>
        <p class="intencion__texto">${esc(e.intencion)}</p>
        <button id="btnIntencionPerfil" class="enlace">Cambiar intención ${icono("i-chevron", "icono icono--mini")}</button>
      </section>
      <section class="tarjeta">
        <p><strong>${App.diasCompletados()}</strong> de ${TOTAL_DIAS} días completados · <strong>${e.registros.length}</strong> registros</p>
      </section>
      <button id="btnCerrarSesion" class="boton boton--sec">Cerrar sesión</button>
      <button id="btnReiniciar" class="boton boton--sec">Reiniciar mi ruta</button>
      <button id="btnBorrar" class="boton boton--peligro">Borrar todos mis datos</button>
      <p class="texto-chico" style="text-align:center;margin-top:12px">HYDISA no emite diagnósticos ni recomendaciones médicas.</p>`;
  },
  activar(c) {
    c.querySelector("#btnGuardarNombre").addEventListener("click", () => {
      const nombre = c.querySelector("#campoNombre").value.trim();
      if (!nombre) return App.aviso("Escribe tu nombre");
      App.estado.usuario.nombre = nombre;
      App.guardar();
      App.aviso("Nombre actualizado");
    });
    c.querySelector("#btnIntencionPerfil").addEventListener("click", () => App.abrirIntencion());
    c.querySelector("#btnCerrarSesion").addEventListener("click", () => App.cerrarSesionCompleta());
    c.querySelector("#btnReiniciar").addEventListener("click", () => {
      if (confirm("¿Reiniciar tu ruta desde el día 1? Tus registros se conservan.")) {
        App.reiniciarRuta(); App.aviso("Ruta reiniciada"); App.navegar("inicio");
      }
    });
    c.querySelector("#btnBorrar").addEventListener("click", () => {
      if (confirm("¿Borrar TODOS tus datos? Esta acción no se puede deshacer.")) {
        App.borrarTodo(); App.aviso("Datos borrados"); App.navegar("inicio"); App.mostrar();
      }
    });
  }
};
