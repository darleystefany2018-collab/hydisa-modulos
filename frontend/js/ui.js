/* ==================================================================
   UI: AYUDAS DE INTERFAZ
   Para qué sirve: pequeñas herramientas que usan todos los módulos:
   buscar elementos, dibujar iconos, mostrar avisos y abrir "hojas".
   ================================================================== */

/* Atajo para buscar un elemento por su id */
const $ = (id) => document.getElementById(id);

/* HTML de un icono de la caja de iconos */
const icono = (nombre, clase = "icono") => `<svg class="${clase}"><use href="#${nombre}"/></svg>`;

/* Convierte texto del usuario en texto seguro para mostrar en pantalla.
   Importante: evita que alguien escriba código dentro de una nota. */
const esc = (texto) => String(texto).replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

/* Formatos de fecha en español: "jue., 22 oct." */
App.fechaCorta = (fecha) => fecha.toLocaleDateString("es-CO", { weekday: "short", day: "numeric", month: "short" });
App.fechaDeTexto = (iso) => App.fechaCorta(new Date(iso + "T00:00:00"));
App.fechaDiaMes = (iso) => new Date(iso + "T00:00:00").toLocaleDateString("es-CO", { day: "numeric", month: "short" });   // "22 oct"

/* Fecha y hora LOCAL a partir de un instante en UTC que manda el servidor ("2026-10-24T17:30:00Z") */
App.fechaHora = (iso) => {
  const f = new Date(iso);
  if (isNaN(f)) return "";
  return f.toLocaleString("es-CO", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" });
};
/* "2026-10-24" + "09:00" -> "sáb., 24 oct. · 09:00 – 09:30" */
App.rangoBloque = (b) => `${App.fechaDeTexto(b.fecha)} · ${b.inicio} – ${b.fin}`;

/* Aviso flotante de 2 segundos */
App.aviso = (texto) => {
  const caja = $("aviso");
  caja.textContent = texto;
  caja.hidden = false;
  clearTimeout(App.aviso.temporizador);
  App.aviso.temporizador = setTimeout(() => (caja.hidden = true), 2200);
};

/* HOJA: ventana que sube desde abajo.
   - titulo: texto de arriba;  html: contenido;  alAbrir(cuerpo): conecta los botones;
   - alCerrar: se ejecuta al cerrarla (por ejemplo, para detener un temporizador). */
App.abrirHoja = (titulo, html, alAbrir, alCerrar) => {
  App.alCerrarHoja = alCerrar || null;
  $("hojaTitulo").textContent = titulo;
  $("hojaCuerpo").innerHTML = html;
  $("hojaVelo").hidden = false;
  $("hoja").hidden = false;
  if (alAbrir) alAbrir($("hojaCuerpo"));
};
App.cerrarHoja = () => {
  if (App.alCerrarHoja) { App.alCerrarHoja(); App.alCerrarHoja = null; }
  $("hojaVelo").hidden = true;
  $("hoja").hidden = true;
};
$("btnCerrarHoja").addEventListener("click", () => App.cerrarHoja());
$("hojaVelo").addEventListener("click", () => App.cerrarHoja());
document.addEventListener("keydown", (e) => { if (e.key === "Escape") App.cerrarHoja(); });
