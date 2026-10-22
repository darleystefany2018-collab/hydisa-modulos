/* ==================================================================
   LÓGICA DE EKILIBRATTE
   Este archivo hace tres cosas:
     1. Guarda los DATOS de ejemplo (después vendrán de la base de datos).
     2. Tiene un bloque por cada MÓDULO de la pantalla que lo "dibuja".
     3. Responde a los clics del usuario.
   ================================================================== */

/* ------------------------------------------------------------------
   DATOS DE EJEMPLO
   Hoy están escritos aquí. Más adelante la función cargarDatos()
   los pedirá al backend de HYDISA (que los lee de Supabase).
   ------------------------------------------------------------------ */
const DATOS = {
  app: { nombre: "EKILIBRATTE", lema: "Tu espacio para volver a ti",
         frase: "“Pequeñas acciones, grandes cambios”" },
  usuario: { nombre: "Ana", notificacionesNuevas: true },
  intenciones: ["Recuperar mi equilibrio en la vida cotidiana.",
                "Dormir mejor y descansar más.",
                "Manejar el estrés con calma."],
  intencionActual: 0,
  ruta: { totalDias: 11, diaActual: 4 },       // el día 4 es el de hoy
  actividadHoy: {
    titulo: "Conecta con tu momento presente",
    descripcion: "Un ejercicio breve para reconocer cómo te sientes hoy y qué necesitas.",
    minutos: 10, tipo: "Reflexión"
  },
  accesos: [
    { icono: "i-chart",    nombre: "Mi evolución",   detalle: "Ver mi progreso" },
    { icono: "i-calendar", nombre: "Calendario",     detalle: "Toda la ruta" },
    { icono: "i-heart",    nombre: "Acompañamiento", detalle: "Mis sesiones" },
    { icono: "i-more",     nombre: "Más",            detalle: "Recursos" }
  ],
  navegacion: [
    { icono: "i-home",  nombre: "Inicio" },
    { icono: "i-leaf",  nombre: "Mi ruta" },
    { icono: "i-book",  nombre: "Registro" },
    { icono: "i-chart", nombre: "Evolución" },
    { icono: "i-user",  nombre: "Perfil" }
  ]
};

/* ------------------------------------------------------------------
   AYUDAS PEQUEÑAS
   ------------------------------------------------------------------ */
const $ = (id) => document.getElementById(id);           // atajo para buscar por id
const icono = (nombre, clase = "icono") =>                // arma el HTML de un icono
  `<svg class="${clase}"><use href="#${nombre}"/></svg>`;

/* Muestra un mensaje flotante por 2 segundos */
function mostrarAviso(texto) {
  const aviso = $("aviso");
  aviso.textContent = texto;
  aviso.hidden = false;
  clearTimeout(mostrarAviso.temporizador);
  mostrarAviso.temporizador = setTimeout(() => (aviso.hidden = true), 2000);
}

/* ------------------------------------------------------------------
   CARGA DE DATOS
   Hoy devuelve los datos de ejemplo. Cuando exista el backend será:
     const respuesta = await fetch("/api/inicio");
     return await respuesta.json();
   ------------------------------------------------------------------ */
async function cargarDatos() {
  return DATOS;
}

/* ------------------------------------------------------------------
   MÓDULO 1 y 2 - CABECERA: saludo del usuario y punto de notificación
   ------------------------------------------------------------------ */
function pintarCabecera(d) {
  $("saludo").textContent = `Hola, ${d.usuario.nombre}`;
  $("puntoNotificacion").hidden = !d.usuario.notificacionesNuevas;
}

/* ------------------------------------------------------------------
   MÓDULO 3 - BIENVENIDA: nombre de la app, lema y frase inspiradora
   ------------------------------------------------------------------ */
function pintarBienvenida(d) {
  $("nombreApp").textContent = d.app.nombre;
  $("lema").textContent = d.app.lema;
  $("frase").textContent = d.app.frase;
}

/* ------------------------------------------------------------------
   MÓDULO 4 - INTENCIÓN PERSONAL: muestra la intención elegida
   ------------------------------------------------------------------ */
function pintarIntencion(d) {
  $("intencion").textContent = d.intenciones[d.intencionActual];
}

/* ------------------------------------------------------------------
   MÓDULO 5 - PROGRESO DE LA RUTA
   Dibuja un círculo por día:  hecho (con check), actual o pendiente.
   Calcula el porcentaje:  días completados / total de días.
   ------------------------------------------------------------------ */
function pintarProgreso(d) {
  const { totalDias, diaActual } = d.ruta;
  $("tituloRuta").textContent = `Tu ruta de ${totalDias} días`;

  let circulos = "";
  for (let dia = 1; dia <= totalDias; dia++) {
    if (dia < diaActual)        circulos += `<li class="dia dia--hecho">${icono("i-check")}</li>`;
    else if (dia === diaActual) circulos += `<li class="dia dia--actual" aria-current="step">${dia}</li>`;
    else                        circulos += `<li class="dia">${dia}</li>`;
  }
  $("diasRuta").innerHTML = circulos;

  const porcentaje = Math.round((diaActual / totalDias) * 100);   // 4 de 11 = 36 %
  $("textoDia").textContent = `Día ${diaActual} de ${totalDias}`;
  $("textoPorcentaje").textContent = `${porcentaje} % completado`;
  $("barraRelleno").style.width = `${porcentaje}%`;
  document.querySelector(".barra").setAttribute("aria-valuenow", porcentaje);
}

/* ------------------------------------------------------------------
   MÓDULO 6 - ACTIVIDAD PRINCIPAL: la actividad recomendada para hoy
   ------------------------------------------------------------------ */
function pintarActividad(d) {
  const a = d.actividadHoy;
  $("diaActividad").textContent = `Día ${d.ruta.diaActual}`;
  $("actividadTitulo").textContent = a.titulo;
  $("actividadDescripcion").textContent = a.descripcion;
  $("actividadMinutos").textContent = `${a.minutos} minutos`;
  $("actividadTipo").textContent = a.tipo;
}

/* ------------------------------------------------------------------
   MÓDULO 7 - ACCESOS RÁPIDOS: atajos a las secciones importantes
   ------------------------------------------------------------------ */
function pintarAccesos(d) {
  $("accesos").innerHTML = d.accesos.map((a) => `
    <button class="acceso" data-seccion="${a.nombre}">
      ${icono(a.icono)}
      <span class="acceso__nombre">${a.nombre}</span>
      <span class="acceso__detalle">${a.detalle}</span>
    </button>`).join("");
}

/* ------------------------------------------------------------------
   MÓDULO 8 - NAVEGACIÓN INFERIOR: barra para cambiar de sección
   Y MENÚ LATERAL (Módulo 1): usa la misma lista de secciones.
   ------------------------------------------------------------------ */
function pintarNavegacion(d) {
  $("navegacion").innerHTML = d.navegacion.map((n, i) => `
    <button class="nav__item ${i === 0 ? "nav__item--activo" : ""}" data-seccion="${n.nombre}">
      ${icono(n.icono)}<span>${n.nombre}</span>
    </button>`).join("");

  $("listaMenu").innerHTML = d.navegacion.map((n) => `
    <li><button data-seccion="${n.nombre}">${icono(n.icono)} ${n.nombre}</button></li>`).join("");
}

/* ------------------------------------------------------------------
   INTERACCIONES: qué pasa cuando la persona toca cada elemento
   ------------------------------------------------------------------ */
function activarEventos(d) {
  /* Módulo 1: abrir y cerrar el menú lateral */
  const abrirMenu = (abrir) => {
    $("panelMenu").classList.toggle("panel--abierto", abrir);
    $("velo").hidden = !abrir;
  };
  $("btnMenu").addEventListener("click", () => abrirMenu(true));
  $("btnCerrarMenu").addEventListener("click", () => abrirMenu(false));
  $("velo").addEventListener("click", () => abrirMenu(false));

  /* Módulo 2: perfil y notificaciones */
  $("btnPerfil").addEventListener("click", () => mostrarAviso("Perfil (próximamente)"));
  $("btnCampana").addEventListener("click", () => {
    $("puntoNotificacion").hidden = true;             // ya las "leyó"
    mostrarAviso("No tienes notificaciones nuevas");
  });

  /* Módulo 4: cambiar la intención (rota por la lista) */
  $("btnCambiarIntencion").addEventListener("click", () => {
    d.intencionActual = (d.intencionActual + 1) % d.intenciones.length;
    pintarIntencion(d);
  });

  /* Módulo 6: comenzar la actividad y ver todas */
  $("btnComenzar").addEventListener("click", () => mostrarAviso("¡Actividad iniciada!"));
  $("btnVerTodas").addEventListener("click", () => mostrarAviso("Lista de actividades (próximamente)"));

  /* Módulos 1, 7 y 8: cualquier botón con data-seccion lleva a una sección */
  document.addEventListener("click", (e) => {
    const boton = e.target.closest("[data-seccion]");
    if (!boton) return;
    const seccion = boton.dataset.seccion;
    if (boton.classList.contains("nav__item")) {          // marcar la pestaña activa
      document.querySelectorAll(".nav__item").forEach((b) => b.classList.remove("nav__item--activo"));
      boton.classList.add("nav__item--activo");
    }
    abrirMenu(false);
    mostrarAviso(`${seccion} (próximamente)`);
  });
}

/* ------------------------------------------------------------------
   INICIO: carga los datos y dibuja todos los módulos
   ------------------------------------------------------------------ */
(async function iniciar() {
  const datos = await cargarDatos();
  pintarCabecera(datos);
  pintarBienvenida(datos);
  pintarIntencion(datos);
  pintarProgreso(datos);
  pintarActividad(datos);
  pintarAccesos(datos);
  pintarNavegacion(datos);
  activarEventos(datos);
})();
