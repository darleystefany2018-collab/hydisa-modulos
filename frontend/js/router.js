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

/* Pantallas visitadas en orden (la última es la actual). Inicio es la raíz: al llegar a ella se reinicia.
   Sirve para que "Volver" sepa si hay una pantalla anterior dentro de la app. */
const pila = [];

/* Dibuja la pantalla que corresponde a la dirección actual */
App.mostrar = () => {
  if (App.limpiar) { App.limpiar(); App.limpiar = null; }     // detiene temporizadores de la pantalla anterior
  App.cerrarHoja();
  const id = App.vistaActual();
  const vista = App.vistas[id];

  if (id === "inicio") pila.length = 0;
  if (pila[pila.length - 2] === id) pila.pop();               // se volvió atrás (botón o navegador)
  else if (pila[pila.length - 1] !== id) pila.push(id);
  /* El botón "Volver" vive en la cabecera, junto al menú. El administrador solo tiene su módulo: no lo necesita. */
  const atras = $("btnAtras");                                // (si index.html no está actualizado no existe: no debe romper la pantalla)
  if (atras) atras.hidden = id === "inicio" || App.esAdmin();

  /* Barra solo con el título (el botón de volver ya está en la cabecera) */
  const barra = id === "inicio" ? "" : `
    <div class="barra-vista">
      <h2>${vista.titulo}</h2>
    </div>`;
  const contenedor = $("vista");
  contenedor.innerHTML = barra + vista.pintar();
  if (vista.activar) vista.activar(contenedor);
  if (App.marcarNavegacion) App.marcarNavegacion(id);
  window.scrollTo(0, 0);
};

window.addEventListener("hashchange", App.mostrar);

/* Botón "Volver" de la cabecera: si hay pantalla anterior usa el historial del navegador
   (así queda igual que el botón "atrás" del celular); si no la hay (p. ej. se recargó la página), va a inicio. */
if ($("btnAtras")) $("btnAtras").addEventListener("click", () => {
  if (pila.length > 1) history.back(); else App.navegar("inicio");
});

/* Cualquier elemento con data-ir="nombre" lleva a esa pantalla */
document.addEventListener("click", (e) => {
  const destino = e.target.closest("[data-ir]");
  if (destino) { App.cerrarHoja(); App.navegar(destino.dataset.ir); }
});
