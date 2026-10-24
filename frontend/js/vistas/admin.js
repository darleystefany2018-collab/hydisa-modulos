/* ==================================================================
   PANTALLA "ADMINISTRACIÓN" (solo para el administrador)
   Para qué sirve: el administrador (hydisa123@gmail.com) puede
     - ver la lista de usuarios y los datos de cada uno (sus reportes y rutas),
     - CREAR CUENTAS nuevas y elegir qué permisos tiene cada una,
     - cambiar los permisos de un usuario cuando quiera.
   SEGURIDAD: esta pantalla solo se muestra si el servidor dijo que la
   sesión es de administrador, pero lo que de verdad protege los datos es
   el servidor: cada llamada a /api/admin/... responde 403 a cualquier otra
   cuenta, aunque alguien abra esta pantalla a mano o llame a la API.
   ================================================================== */
(() => {
  let raiz = null;
  let catalogo = [];                       // [{clave, nombre}] que manda el servidor
  let pestana = "usuarios";                // "usuarios" | "crear"

  const fecha = (t) => esc(String(t).slice(0, 10));
  const msg = (texto, tipo = "error") => `<p class="mensaje mensaje--${tipo}" role="alert">${esc(texto)}</p>`;

  const alFallar = (error, zona) => {
    if (error.sesionVencida) return App.mostrarAcceso("Tu sesión terminó. Entra otra vez.");
    if (error.sinServidor) { zona.innerHTML = msg(error.message + " Ábrela con iniciar_hydisa.bat."); return; }
    zona.innerHTML = msg(error.message);
  };

  /* Casillas de permisos (checked = lista de claves marcadas) */
  const casillas = (marcadas, bloqueado = false) => catalogo.map((p) => `
    <label class="permiso">
      <input type="checkbox" name="permiso" value="${esc(p.clave)}" ${marcadas.includes(p.clave) ? "checked" : ""} ${bloqueado ? "disabled" : ""}>
      <span>${esc(p.nombre)}</span>
    </label>`).join("");
  const leerCasillas = (contenedor) => [...contenedor.querySelectorAll("input[name=permiso]:checked")].map((i) => i.value);

  /* ---------- Estructura con pestañas ---------- */
  function dibujar(aviso = "") {
    raiz.innerHTML = `
      <div class="pestanas">
        <button class="pestana ${pestana === "usuarios" ? "pestana--activa" : ""}" data-p="usuarios">Usuarios</button>
        <button class="pestana ${pestana === "crear" ? "pestana--activa" : ""}" data-p="crear">Crear cuenta</button>
      </div>
      ${aviso ? msg(aviso, "ok") : ""}
      <div id="zonaAdmin"></div>`;
    raiz.querySelectorAll(".pestana").forEach((b) =>
      b.addEventListener("click", () => { pestana = b.dataset.p; dibujar(); }));
    if (pestana === "crear") formularioCrear(); else listaUsuarios();
  }

  /* ---------- Lista de usuarios ---------- */
  async function listaUsuarios() {
    const zona = raiz.querySelector("#zonaAdmin");
    zona.innerHTML = `<p class="vacio">Cargando…</p>`;
    try {
      const r = await App.api.admin.usuarios();
      catalogo = r.catalogo;
      zona.innerHTML = `<ul class="lista">${r.usuarios.map((u) => `
        <li class="item item--dia"><button class="item__boton" data-id="${Number(u.id)}">
          <span class="item__num">${icono(u.es_admin ? "i-shield" : "i-user")}</span>
          <span class="item__texto"><strong>${esc(u.nombre)}</strong>
            <small>${esc(u.correo)} · ${Number(u.n_reportes)} reporte(s)</small></span>
          ${u.es_admin ? `<span class="etiqueta etiqueta--hoy">Admin</span>` : icono("i-chevron", "icono icono--mini")}
        </button></li>`).join("")}</ul>`;
      zona.querySelectorAll("[data-id]").forEach((b) =>
        b.addEventListener("click", () => detalleUsuario(Number(b.dataset.id))));
    } catch (error) { alFallar(error, zona); }
  }

  /* ---------- Detalle de un usuario: datos, permisos y reportes ---------- */
  async function detalleUsuario(id, aviso = "") {
    raiz.innerHTML = `<p class="vacio">Cargando…</p>`;
    try {
      const { usuario: u, reportes } = await App.api.admin.usuario(id);
      raiz.innerHTML = `
        <button id="btnVolver" class="enlace">${icono("i-back", "icono icono--mini")} Volver a usuarios</button>
        ${aviso ? msg(aviso, "ok") : ""}
        <section class="tarjeta" style="margin-top:10px">
          <p class="tarjeta__titulo">${esc(u.nombre)}</p>
          <p class="texto-suave">${esc(u.correo)}</p>
          <p class="texto-chico">Rol: ${u.es_admin ? "Administrador" : "Usuario"} · Cuenta N.º ${Number(u.id)}</p>
        </section>
        <section class="tarjeta" style="margin-top:12px" id="cajaPermisos">
          <p class="tarjeta__titulo">Permisos</p>
          ${casillas(u.permisos, u.es_admin)}
          ${u.es_admin ? `<p class="texto-chico">El administrador siempre tiene todos los permisos.</p>`
            : `<button id="btnGuardarPermisos" class="boton">Guardar permisos</button>`}
          <div id="mensajes"></div>
        </section>
        <p class="subtitulo" style="margin:16px 0 8px">Reportes de este usuario</p>
        ${reportes.length ? `<ul class="lista">${reportes.map((r) => `
          <li class="item item--dia"><button class="item__boton" data-reporte="${Number(r.id)}">
            <span class="item__num">${icono("i-file")}</span>
            <span class="item__texto"><strong>${esc(r.nombre_archivo)}</strong><small>Reporte N.º ${Number(r.id)} · ${fecha(r.creado_en)}</small></span>
            ${icono("i-chevron", "icono icono--mini")}
          </button></li>`).join("")}</ul>` : `<p class="vacio">Este usuario aún no ha cargado reportes.</p>`}`;

      raiz.querySelector("#btnVolver").addEventListener("click", () => { pestana = "usuarios"; dibujar(); });
      raiz.querySelectorAll("[data-reporte]").forEach((b) =>
        b.addEventListener("click", () => verReporte(u, Number(b.dataset.reporte))));
      const guardar = raiz.querySelector("#btnGuardarPermisos");
      if (guardar) guardar.addEventListener("click", async () => {
        guardar.disabled = true;
        try {
          await App.api.admin.permisos(u.id, leerCasillas(raiz.querySelector("#cajaPermisos")));
          detalleUsuario(u.id, "Permisos actualizados. Rigen desde su próxima acción.");
        } catch (error) { guardar.disabled = false; alFallar(error, raiz.querySelector("#mensajes")); }
      });
    } catch (error) {
      raiz.innerHTML = `<div id="mensajes"></div>`;
      alFallar(error, raiz.querySelector("#mensajes"));
    }
  }

  /* ---------- Ver un reporte de otro usuario (solo lectura) ---------- */
  async function verReporte(u, reporteId) {
    raiz.innerHTML = `<p class="vacio">Cargando…</p>`;
    try {
      const d = await App.api.admin.reporte(u.id, reporteId);
      const palabras = Object.entries(d.palabras || {}).map(([cat, ps]) => `
        <p class="texto-chico" style="margin-top:10px">${esc(cat)}</p>
        <div class="chips">${Object.entries(ps).map(([p, n]) => `<span class="chip">${esc(p)} <b>×${Number(n)}</b></span>`).join("")}</div>`).join("")
        || `<p class="texto-suave">No se encontraron palabras clave.</p>`;
      raiz.innerHTML = `
        <button id="btnVolver" class="enlace">${icono("i-back", "icono icono--mini")} Volver a ${esc(u.nombre.split(" ")[0])}</button>
        <section class="tarjeta" style="margin-top:10px">
          <p class="tarjeta__titulo">Reporte N.º ${Number(reporteId)} · ${esc(u.nombre)}</p>
          <div class="progreso__textos"><span>Progreso</span><span>${Number(d.progreso)} %</span></div>
          <div class="barra"><div class="barra__relleno" style="width:${Number(d.progreso)}%"></div></div>
        </section>
        <section class="tarjeta" style="margin-top:12px"><p class="tarjeta__titulo">Palabras clave</p>${palabras}</section>
        <p class="subtitulo" style="margin:16px 0 8px">Ruta</p>
        <ul class="lista">${d.ruta.map((i) => `
          <li class="item item--dia ${i.cumplida ? "item--hecho" : ""}"><div class="item__boton">
            <span class="item__num">${i.cumplida ? icono("i-check") : Number(i.posicion)}</span>
            <span class="item__texto"><strong>${esc(i.actividad)}</strong><small>${esc(i.categoria)} · prioridad ${Number(i.prioridad)}</small></span>
            ${i.cumplida ? `<span class="etiqueta etiqueta--hecho">Cumplida</span>` : ""}
          </div></li>`).join("")}</ul>`;
      raiz.querySelector("#btnVolver").addEventListener("click", () => detalleUsuario(u.id));
    } catch (error) {
      raiz.innerHTML = `<div id="mensajes"></div>`;
      alFallar(error, raiz.querySelector("#mensajes"));
    }
  }

  /* ---------- Crear cuenta nueva con permisos ---------- */
  async function formularioCrear() {
    const zona = raiz.querySelector("#zonaAdmin");
    try {
      if (!catalogo.length) catalogo = (await App.api.admin.usuarios()).catalogo;
    } catch (error) { return alFallar(error, zona); }
    zona.innerHTML = `
      <form id="formCrear" class="tarjeta" novalidate>
        <p class="tarjeta__titulo">Nueva cuenta</p>
        <label class="campo"><span>Nombre completo</span><input name="nombre" type="text" maxlength="60" autocomplete="off"></label>
        <label class="campo"><span>Correo</span><input name="correo" type="email" autocomplete="off"></label>
        <label class="campo"><span>Contraseña inicial (mínimo 8 caracteres)</span><input name="clave" type="text" autocomplete="off"></label>
        <p class="texto-chico">Permisos de la cuenta</p>
        ${casillas(catalogo.map((p) => p.clave))}
        <div id="mensajes"></div>
        <button class="boton" type="submit">Crear cuenta</button>
      </form>`;
    const f = zona.querySelector("#formCrear");
    f.addEventListener("submit", async (e) => {
      e.preventDefault();
      const boton = f.querySelector("button[type=submit]");
      boton.disabled = true;
      try {
        const { usuario } = await App.api.admin.crear({
          nombre: f.elements.nombre.value, correo: f.elements.correo.value,
          clave: f.elements.clave.value, permisos: leerCasillas(f) });
        pestana = "usuarios";
        App.aviso("Cuenta creada");
        detalleUsuario(usuario.id, `Cuenta creada para ${usuario.nombre}. Entrégale su correo y contraseña inicial.`);
      } catch (error) { boton.disabled = false; alFallar(error, f.querySelector("#mensajes")); }
    });
  }

  App.vistas.admin = {
    titulo: "Administración",
    pintar: () => App.esAdmin() ? `<div id="admin"></div>`
      : `<p class="vacio">No tienes permiso para ver esta sección.</p>`,
    activar(c) {
      if (!App.esAdmin()) return;
      raiz = c.querySelector("#admin");
      pestana = "usuarios";
      dibujar();
    }
  };
})();
