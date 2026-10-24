/* ==================================================================
   PANTALLA "MI ANÁLISIS" (todas las funciones de main.py)
   Para qué sirve: aquí se usa el programa de Python completo desde la
   pantalla, con la base de datos real (Supabase):
     main.py  1. Registrarse        -> pestaña "Crear cuenta"
     main.py  2. Iniciar sesión     -> pestaña "Entrar"
     menú 1.  Cargar PDF            -> pestaña "Cargar PDF" (+ palabras clave)
     menú 2.  Historial             -> pestaña "Historial"
     menú 3.  Ver ruta y progreso   -> detalle de un reporte
     menú 4.  Marcar actividad      -> botón "Marcar cumplida"
     menú 5.  Exportar PDF          -> botón "Exportar PDF"
     menú 0.  Salir                 -> botón "Cerrar sesión"
   ================================================================== */
(() => {
  let raiz = null;                 // contenedor donde se dibuja todo
  let pestana = "cargar";          // "cargar" | "historial" (o "entrar" | "crear" sin sesión)

  const fechaCorta = (t) => esc(String(t).slice(0, 16).replace("T", " "));
  const msg = (texto, tipo = "error") => `<p class="mensaje mensaje--${tipo}" role="alert">${esc(texto)}</p>`;

  /* Si el servidor no está encendido, explica cómo encenderlo */
  const sinServidor = () => {
    raiz.innerHTML = `
      <section class="tarjeta">
        <p class="tarjeta__titulo">Falta encender HYDISA</p>
        <p class="texto-suave">Esta pantalla necesita el servidor de Python. Ábrela con el acceso directo o con <strong>iniciar_hydisa.bat</strong> y pulsa Reintentar.</p>
        <button id="btnReintentar" class="boton boton--sec">Reintentar</button>
      </section>`;
    raiz.querySelector("#btnReintentar").addEventListener("click", dibujar);
  };

  /* Maneja un error: sin servidor, sesión vencida o mensaje normal */
  const alFallar = (error, zonaMensajes) => {
    if (error.sinServidor) return sinServidor();
    if (error.sesionVencida) return App.mostrarAcceso("Tu sesión terminó. Entra otra vez.");
    zonaMensajes.innerHTML = msg(error.message);
  };

  /* ---------- Con sesión: panel principal ---------- */
  function dibujarPanel() {
    /* Solo se ofrecen las pestañas que la cuenta tiene permitidas (el servidor igual lo comprueba) */
    const pestanas = [["cargar", "Cargar PDF", "cargar_pdf"], ["historial", "Historial", "ver_reportes"]]
      .filter(([, , permiso]) => App.puede(permiso)).map(([clave, nombre]) => [clave, nombre]);
    if (!pestanas.some(([clave]) => clave === pestana) && pestanas.length) pestana = pestanas[0][0];
    raiz.innerHTML = `
      <section class="tarjeta fila-usuario">
        <div><p class="texto-chico">Sesión iniciada</p><strong>${esc(App.api.usuario.nombre)}</strong>
          <p class="texto-chico">${esc(App.api.usuario.correo)}</p></div>
        <button id="btnSalir" class="enlace">Cerrar sesión</button>
      </section>
      ${pestanas.length ? `<div class="pestanas" style="grid-template-columns:repeat(${pestanas.length},1fr)">${pestanas.map(([clave, nombre]) =>
        `<button class="pestana ${pestana === clave ? "pestana--activa" : ""}" data-p="${clave}">${nombre}</button>`).join("")}</div>` : ""}
      <div id="zona"></div>`;

    raiz.querySelector("#btnSalir").addEventListener("click", async () => {
      await App.cerrarSesionCompleta();
    });
    raiz.querySelectorAll(".pestana").forEach((b) =>
      b.addEventListener("click", () => { pestana = b.dataset.p; dibujarPanel(); }));

    if (!pestanas.length) {
      raiz.querySelector("#zona").innerHTML = `<p class="vacio">Tu cuenta aún no tiene permisos habilitados. Pídele al administrador que te los asigne.</p>`;
    } else if (pestana === "historial") dibujarHistorial(); else dibujarCarga();
  }

  /* ---------- Cargar PDF (menú 1) ---------- */
  function dibujarCarga() {
    const zona = raiz.querySelector("#zona");
    zona.innerHTML = `
      <form id="formPdf" class="tarjeta" novalidate>
        <p class="tarjeta__titulo">Sube tu reporte en PDF</p>
        <p class="texto-suave">Solo archivos .pdf de hasta 10 MB con texto (no escaneados). HYDISA busca palabras clave, con o sin tildes, y arma tu ruta de bienestar.</p>
        <label class="archivo">
          ${icono("i-file")}<span id="nombreArchivo">Elegir archivo PDF</span>
          <input id="campoPdf" type="file" accept="application/pdf,.pdf">
        </label>
        <div id="mensajes"></div>
        <button id="btnAnalizar" class="boton" type="submit">Analizar PDF</button>
      </form>`;
    const campo = zona.querySelector("#campoPdf");
    campo.addEventListener("change", () => {
      zona.querySelector("#nombreArchivo").textContent = campo.files[0] ? campo.files[0].name : "Elegir archivo PDF";
    });
    zona.querySelector("#formPdf").addEventListener("submit", async (e) => {
      e.preventDefault();
      const mensajes = zona.querySelector("#mensajes");
      const archivo = campo.files[0];
      if (!archivo) { mensajes.innerHTML = msg("Primero elige un archivo PDF."); return; }
      const boton = zona.querySelector("#btnAnalizar");
      boton.disabled = true; boton.textContent = "Analizando…";
      try {
        const r = await App.api.cargarPdf(archivo);
        App.agregarNotificacion(`Analizaste "${r.nombre_archivo}". Tu ruta está lista.`);
        App.guardar();
        App.aviso(`Reporte ${r.reporte_id} analizado`);
        dibujarDetalle(r.reporte_id, r, true);
      } catch (error) {
        boton.disabled = false; boton.textContent = "Analizar PDF";
        alFallar(error, mensajes);
      }
    });
  }

  /* ---------- Historial (menú 2) ---------- */
  async function dibujarHistorial() {
    const zona = raiz.querySelector("#zona");
    zona.innerHTML = `<p class="vacio">Cargando…</p>`;
    try {
      const { reportes } = await App.api.historial();
      zona.innerHTML = reportes.length ? `<ul class="lista">${reportes.map((r) => `
        <li class="item item--dia"><button class="item__boton" data-id="${Number(r.id)}">
          <span class="item__num">${icono("i-file", "icono")}</span>
          <span class="item__texto"><strong>${esc(r.nombre_archivo)}</strong><small>Reporte N.º ${Number(r.id)} · ${fechaCorta(r.creado_en)}</small></span>
          ${icono("i-chevron", "icono icono--mini")}
        </button></li>`).join("")}</ul>`
        : `<p class="vacio">Todavía no has cargado ningún PDF.</p>`;
      zona.querySelectorAll("[data-id]").forEach((b) =>
        b.addEventListener("click", () => dibujarDetalle(Number(b.dataset.id))));
    } catch (error) { alFallar(error, zona); }
  }

  /* ---------- Detalle: ruta, progreso, palabras clave, marcar, exportar (menú 3, 4, 5) ---------- */
  async function dibujarDetalle(id, datos, recienAnalizado = false) {
    raiz.innerHTML = `<p class="vacio">Cargando…</p>`;
    try {
      if (!datos) datos = { ...(await App.api.verRuta(id)), ...(await App.api.palabras(id)) };
      pintarDetalle(id, datos, recienAnalizado);
    } catch (error) {
      raiz.innerHTML = `<div id="mensajes"></div>`;
      alFallar(error, raiz.querySelector("#mensajes"));
    }
  }

  function pintarDetalle(id, datos, recienAnalizado) {
    const categorias = Object.entries(datos.palabras || {});
    const palabras = categorias.length ? categorias.map(([cat, ps]) => `
      <p class="texto-chico" style="margin-top:10px">${esc(cat)}</p>
      <div class="chips">${Object.entries(ps).map(([p, n]) => `<span class="chip">${esc(p)} <b>×${Number(n)}</b></span>`).join("")}</div>`).join("")
      : `<p class="texto-suave">No se encontraron palabras clave en este PDF.</p>`;

    const items = datos.ruta.map((i) => `
      <li class="item item--dia ${i.cumplida ? "item--hecho" : ""}">
        <div class="item__boton">
          <span class="item__num">${i.cumplida ? icono("i-check") : Number(i.posicion)}</span>
          <span class="item__texto"><strong>${esc(i.actividad)}</strong><small>${esc(i.categoria)} · prioridad ${Number(i.prioridad)}</small></span>
          ${i.cumplida ? `<span class="etiqueta etiqueta--hecho">Cumplida</span>`
            : (App.puede("marcar_actividades") ? `<button class="marcar" data-n="${Number(i.posicion)}">Marcar cumplida</button>` : "")}
        </div>
      </li>`).join("");

    raiz.innerHTML = `
      <button id="btnVolver" class="enlace">${icono("i-back", "icono icono--mini")} Volver</button>
      ${recienAnalizado ? msg(`Reporte ${id} analizado. Tu ruta fue generada.`, "ok") : ""}
      <section class="tarjeta" style="margin-top:10px">
        <p class="tarjeta__titulo">Reporte N.º ${Number(id)}</p>
        <div class="progreso__textos"><span>Progreso</span><span>${Number(datos.progreso)} %</span></div>
        <div class="barra" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Number(datos.progreso)}">
          <div class="barra__relleno" style="width:${Number(datos.progreso)}%"></div></div>
        ${App.puede("exportar_pdf") ? `<button id="btnExportar" class="boton boton--sec">${icono("i-download")} Exportar PDF</button>` : ""}
        <div id="mensajes"></div>
      </section>
      <section class="tarjeta" style="margin-top:12px">
        <p class="tarjeta__titulo">Palabras clave encontradas</p>${palabras}
      </section>
      <p class="subtitulo" style="margin:16px 0 8px">Tu ruta personalizada</p>
      <ul class="lista">${items || `<li class="vacio">Este reporte no generó actividades.</li>`}</ul>
      <p class="texto-chico" style="text-align:center;margin-top:14px">HYDISA no emite diagnósticos, tratamientos ni recomendaciones médicas. La información es educativa y de bienestar.</p>`;

    raiz.querySelector("#btnVolver").addEventListener("click", () => { pestana = "historial"; dibujarPanel(); });

    raiz.querySelectorAll(".marcar").forEach((b) => b.addEventListener("click", async () => {
      b.disabled = true;
      try {
        const nueva = await App.api.marcarActividad(id, Number(b.dataset.n));
        App.aviso("Actividad marcada como cumplida");
        pintarDetalle(id, { ...datos, ...nueva });
      } catch (error) { b.disabled = false; alFallar(error, raiz.querySelector("#mensajes")); }
    }));

    const botonExportar = raiz.querySelector("#btnExportar");
    if (botonExportar) botonExportar.addEventListener("click", async (e) => {
      const boton = e.currentTarget;
      boton.disabled = true;
      try {
        const archivo = await App.api.exportarPdf(id);
        const enlace = document.createElement("a");
        enlace.href = URL.createObjectURL(archivo);
        enlace.download = `ruta_bienestar_${id}.pdf`;
        document.body.appendChild(enlace); enlace.click(); enlace.remove();
        setTimeout(() => URL.revokeObjectURL(enlace.href), 1000);
        App.aviso("PDF descargado");
      } catch (error) { alFallar(error, raiz.querySelector("#mensajes")); }
      boton.disabled = false;
    });
  }

  function dibujar() {
    if (!App.api.token) return App.mostrarAcceso();
    dibujarPanel();
  }

  App.vistas.analisis = {
    titulo: "Mi análisis",
    pintar: () => `<div id="analisis"></div>`,
    activar(c) { raiz = c.querySelector("#analisis"); dibujar(); }
  };
})();
