/* ==================================================================
   ROUTER: CAMBIO DE PANTALLA
   Para qué sirve: según la dirección (#/ruta, #/registro...) decide qué
   pantalla dibujar. Así el botón "atrás" del navegador también funciona.
   Cada pantalla es un objeto en App.vistas con:
     titulo   -> texto de la barra superior (inicio no la lleva)
     pintar() -> devuelve el HTML de la pantalla
     activar(contenedor) -> conecta los botones de esa pantalla
   ================================================================== */

/* Ir a otra pantalla */
App.navegar = (id) => { location.hash = "#/" + id; };

/* Nombre de la pantalla actual */
App.vistaActual = () => {
  /* El administrador solo tiene el módulo de gestión: cualquier otra dirección lo lleva ahí.
     (El servidor además le niega las rutas de acompañamiento: esto solo evita pantallas vacías.) */
  if (App.esAdmin()) return "admin";
  const id = location.hash.replace("#/", "");
  return App.vistas[id] ? id : "inicio";
};

/* Dibuja la pantalla que corresponde a la dirección actual */
App.mostrar = () => {
  if (App.limpiar) { App.limpiar(); App.limpiar = null; }     // detiene temporizadores de la pantalla anterior
  App.cerrarHoja();
  const id = App.vistaActual();
  const vista = App.vistas[id];
  /* Barra con título y botón "volver" (el administrador no tiene inicio al que volver) */
  const barra = id === "inicio" ? "" : `
    <div class="barra-vista">
      ${App.esAdmin() ? "" : `<button class="icono-btn" data-ir="inicio" aria-label="Volver al inicio">${icono("i-back")}</button>`}
      <h2>${vista.titulo}</h2>
    </div>`;
  const contenedor = $("vista");
  contenedor.innerHTML = barra + vista.pintar();
  if (vista.activar) vista.activar(contenedor);
  if (App.marcarNavegacion) App.marcarNavegacion(id);
  window.scrollTo(0, 0);
};

window.addEventListener("hashchange", App.mostrar);

/* Cualquier elemento con data-ir="nombre" lleva a esa pantalla */
document.addEventListener("click", (e) => {
  const destino = e.target.closest("[data-ir]");
  if (destino) { App.cerrarHoja(); App.navegar(destino.dataset.ir); }
});
