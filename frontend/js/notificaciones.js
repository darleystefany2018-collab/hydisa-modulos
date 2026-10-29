/* ==================================================================
   MÓDULO 2 - PERFIL Y NOTIFICACIONES
   Para qué sirve: muestra el saludo con el nombre de la persona, el
   punto rojo cuando hay avisos sin leer y la lista de notificaciones.
   ================================================================== */

/* Actualiza el saludo y el punto rojo (se llama cada vez que se guarda) */
App.refrescarCabecera = () => {
  $("saludo").textContent = App.esAdmin() ? "Administrador" : `Hola, ${App.estado.usuario.nombre}`;
  $("puntoNotificacion").hidden = !App.estado.notificaciones.some((n) => !n.leida);
};

/* Abre la lista de notificaciones */
App.abrirNotificaciones = () => {
  const lista = App.estado.notificaciones;
  const html = lista.length
    ? `<ul class="lista">${lista.map((n) => `
        <li class="item ${n.leida ? "" : "item--nuevo"}">
          <p>${esc(n.texto)}</p><span class="texto-chico">${App.fechaDeTexto(n.fecha)}</span>
        </li>`).join("")}</ul>
       <button id="btnLeerTodas" class="boton boton--sec">Marcar todas como leídas</button>`
    : `<p class="vacio">No tienes notificaciones.</p>`;

  App.abrirHoja("Notificaciones", html, (cuerpo) => {
    const boton = cuerpo.querySelector("#btnLeerTodas");
    if (boton) boton.addEventListener("click", () => {
      App.estado.notificaciones.forEach((n) => (n.leida = true));
      App.guardar();
      App.cerrarHoja();
      App.aviso("Notificaciones leídas");
    });
  });
};

$("btnCampana").addEventListener("click", () => App.abrirNotificaciones());
$("btnPerfil").addEventListener("click", () => App.navegar(App.esAdmin() ? "admin" : "perfil"));
