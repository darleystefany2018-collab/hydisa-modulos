/* ==================================================================
   MÓDULO 1 - MENÚ PRINCIPAL (panel lateral)
   MÓDULO 8 - NAVEGACIÓN PRINCIPAL (barra inferior)
   Para qué sirve: permiten pasar de una sección a otra. El menú lateral
   muestra todas las secciones; la barra inferior, las 5 principales.
   ================================================================== */

/* Dibuja la barra inferior y la lista del menú lateral */
App.pintarNavegacion = () => {
  $("navegacion").innerHTML = App.SECCIONES.filter((s) => s.navegacion).map((s) => `
    <button class="nav__item" data-ir="${s.id}" data-nav="${s.id}">
      ${icono(s.icono)}<span>${s.nombre}</span>
    </button>`).join("");

  $("listaMenu").innerHTML = App.SECCIONES.filter((s) => !s.soloAdmin || App.esAdmin()).map((s) => `
    <li><button data-ir="${s.id}">${icono(s.icono)} ${s.nombre}</button></li>`).join("");
};

/* Marca como activa la pestaña de la pantalla actual */
App.marcarNavegacion = (id) => {
  document.querySelectorAll(".nav__item").forEach((b) =>
    b.classList.toggle("nav__item--activo", b.dataset.nav === id));
};

/* Abrir y cerrar el panel lateral */
App.abrirMenu = (abrir) => {
  $("panelMenu").classList.toggle("panel--abierto", abrir);
  $("panelMenu").setAttribute("aria-hidden", String(!abrir));
  $("velo").hidden = !abrir;
};
$("btnMenu").addEventListener("click", () => App.abrirMenu(true));
$("btnCerrarMenu").addEventListener("click", () => App.abrirMenu(false));
$("velo").addEventListener("click", () => App.abrirMenu(false));

/* Al elegir una sección del menú, se cierra el panel */
$("listaMenu").addEventListener("click", (e) => { if (e.target.closest("[data-ir]")) App.abrirMenu(false); });
