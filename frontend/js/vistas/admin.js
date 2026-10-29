/* ==================================================================
   PANTALLA "ADMINISTRACIÓN" (el único módulo del administrador)
   Para qué sirve: el administrador (hydisa123@gmail.com) SOLO gestiona:
     - ALERTAS SOS: ve quién pidió ayuda y a qué hora, y las marca como atendidas
       (siempre visibles arriba, se actualizan solas cada 15 segundos),
     - USUARIOS: lista, datos de cada uno, sus reportes y sus permisos,
     - CREAR CUENTA: nuevas cuentas con los permisos que elija,
     - AGENDA: publica un rango libre (o todo el día) que se divide en espacios de 30 min que los usuarios
       reservan desde su módulo de acompañamiento, y ve quién reservó cada uno.
   No tiene cargar PDF, rutas, sesiones propias ni botón SOS.
   SEGURIDAD: esta pantalla solo se muestra si el servidor dijo que la sesión es
   de administrador, pero lo que de verdad protege los datos es el servidor:
   cada llamada a /api/admin/... responde 403 a cualquier otra cuenta.
   ================================================================== */
(() => {
  let raiz = null;                         // envoltorio: alertas (fijas) + contenido (cambia)
  let cont = null;                         // zona que cambia según la pestaña o el detalle
  let temporizador = null;                 // actualización periódica de las alertas
  let catalogo = [];                       // [{clave, nombre}] que manda el servidor
  let pestana = "usuarios";                // "usuarios" | "crear"

  const fecha = (t) => esc(App.fechaHora(t));
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
    cont.innerHTML = `
      <div class="pestanas" style="grid-template-columns:repeat(3,1fr)">
        <button class="pestana ${pestana === "usuarios" ? "pestana--activa" : ""}" data-p="usuarios">Usuarios</button>
        <button class="pestana ${pestana === "crear" ? "pestana--activa" : ""}" data-p="crear">Crear cuenta</button>
        <button class="pestana ${pestana === "agenda" ? "pestana--activa" : ""}" data-p="agenda">Agenda</button>
      </div>
      ${aviso ? msg(aviso, "ok") : ""}
      <div id="zonaAdmin"></div>`;
    cont.querySelectorAll(".pestana").forEach((b) =>
      b.addEventListener("click", () => { pestana = b.dataset.p; dibujar(); }));
    if (pestana === "crear") formularioCrear(); else if (pestana === "agenda") agenda(); else listaUsuarios();
  }

  /* ---------- Lista de usuarios ---------- */
  async function listaUsuarios() {
    const zona = cont.querySelector("#zonaAdmin");
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
    cont.innerHTML = `<p class="vacio">Cargando…</p>`;
    try {
      const { usuario: u, reportes } = await App.api.admin.usuario(id);
      cont.innerHTML = `
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
          ${u.es_admin ? `<p class="texto-chico">Cuenta de gestión: no usa los módulos de acompañamiento, por eso no tiene permisos de usuario.</p>`
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

      cont.querySelector("#btnVolver").addEventListener("click", () => { pestana = "usuarios"; dibujar(); });
      cont.querySelectorAll("[data-reporte]").forEach((b) =>
        b.addEventListener("click", () => verReporte(u, Number(b.dataset.reporte))));
      const guardar = cont.querySelector("#btnGuardarPermisos");
      if (guardar) guardar.addEventListener("click", async () => {
        guardar.disabled = true;
        try {
          await App.api.admin.permisos(u.id, leerCasillas(cont.querySelector("#cajaPermisos")));
          detalleUsuario(u.id, "Permisos actualizados. Rigen desde su próxima acción.");
        } catch (error) { guardar.disabled = false; alFallar(error, cont.querySelector("#mensajes")); }
      });
    } catch (error) {
      cont.innerHTML = `<div id="mensajes"></div>`;
      alFallar(error, cont.querySelector("#mensajes"));
    }
  }

  /* ---------- Ver un reporte de otro usuario (solo lectura) ---------- */
  async function verReporte(u, reporteId) {
    cont.innerHTML = `<p class="vacio">Cargando…</p>`;
    try {
      const d = await App.api.admin.reporte(u.id, reporteId);
      const palabras = Object.entries(d.palabras || {}).map(([cat, ps]) => `
        <p class="texto-chico" style="margin-top:10px">${esc(cat)}</p>
        <div class="chips">${Object.entries(ps).map(([p, n]) => `<span class="chip">${esc(p)} <b>×${Number(n)}</b></span>`).join("")}</div>`).join("")
        || `<p class="texto-suave">No se encontraron palabras clave.</p>`;
      cont.innerHTML = `
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
      cont.querySelector("#btnVolver").addEventListener("click", () => detalleUsuario(u.id));
    } catch (error) {
      cont.innerHTML = `<div id="mensajes"></div>`;
      alFallar(error, cont.querySelector("#mensajes"));
    }
  }

  /* ---------- Crear cuenta nueva con permisos ---------- */
  async function formularioCrear() {
    const zona = cont.querySelector("#zonaAdmin");
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

  /* ---------- Alertas SOS (siempre arriba) ---------- */
  async function refrescarAlertas() {
    const caja = raiz && raiz.querySelector("#alertasSos");
    if (!caja) return;
    try {
      const { pendientes, atendidas } = await App.api.admin.alertas();
      const fila = (a, atendida) => `
        <li class="alerta ${atendida ? "alerta--atendida" : ""}">
          <span class="alerta__marca">${atendida ? icono("i-check") : "SOS"}</span>
          <span class="item__texto"><strong>${esc(a.usuario.nombre)}</strong>
            <small>${esc(a.usuario.correo)} · ${esc(App.fechaHora(a.creado_en))}${atendida ? ` · atendida ${esc(App.fechaHora(a.atendida_en))}` : ""}</small>
            ${a.mensaje ? `<span class="alerta__mensaje">“${esc(a.mensaje)}”</span>` : ""}</span>
          ${atendida ? "" : `<button class="marcar" data-alerta="${Number(a.id)}">Marcar atendida</button>`}
        </li>`;
      caja.innerHTML = pendientes.length ? `
        <section class="tarjeta tarjeta--alerta" role="alert">
          <p class="tarjeta__titulo">Alertas SOS pendientes (${pendientes.length})</p>
          <ul class="lista">${pendientes.map((a) => fila(a, false)).join("")}</ul>
        </section>` : `<p class="texto-chico alertas__vacio">Sin alertas SOS pendientes.</p>`;
      if (atendidas.length) caja.insertAdjacentHTML("beforeend", `
        <details class="alertas__historial"><summary>Atendidas recientes (${atendidas.length})</summary>
          <ul class="lista">${atendidas.map((a) => fila(a, true)).join("")}</ul></details>`);
      caja.querySelectorAll("[data-alerta]").forEach((b) => b.addEventListener("click", async () => {
        b.disabled = true;
        try { await App.api.admin.atenderAlerta(Number(b.dataset.alerta)); App.aviso("Alerta marcada como atendida"); }
        catch (error) { App.aviso(error.message); }
        refrescarAlertas();
      }));
    } catch (error) {
      if (error.sesionVencida) { clearInterval(temporizador); App.mostrarAcceso("Tu sesión terminó. Entra otra vez."); }
      else caja.innerHTML = msg(error.message);
    }
  }

  /* ---------- Agenda: publicar bloques de disponibilidad ---------- */
  const sumarMinutos = (hora, minutos) => {
    const [h, m] = hora.split(":").map(Number);
    const total = h * 60 + m + minutos;
    return `${String(Math.floor(total / 60) % 24).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
  };

  async function agenda(aviso = "") {
    const zona = cont.querySelector("#zonaAdmin");
    zona.innerHTML = `<p class="vacio">Cargando…</p>`;
    try {
      const { bloques, duracion_sesion: duracion, apertura, cierre } = await App.api.admin.agenda();
      const porDia = {};
      bloques.forEach((b) => (porDia[b.fecha] = porDia[b.fecha] || []).push(b));
      const lista = Object.keys(porDia).length ? Object.entries(porDia).map(([f, bs]) => `
        <p class="texto-chico" style="margin:12px 0 6px">${esc(App.fechaDeTexto(f))}</p>
        <ul class="lista">${bs.map((b) => `
          <li class="item item--registro">
            <span class="item__texto"><strong>${esc(b.inicio)} – ${esc(b.fin)}</strong>
              <small>${b.reservado ? `Reservado por ${esc(b.usuario.nombre)} (${esc(b.usuario.correo)})${b.tema ? " · " + esc(b.tema) : ""}` : "Libre"}</small></span>
            ${b.reservado ? `<span class="etiqueta etiqueta--hoy">Reservado</span>`
              : `<button class="icono-btn" data-eliminar="${Number(b.id)}" aria-label="Eliminar bloque">${icono("i-trash")}</button>`}
          </li>`).join("")}</ul>`).join("") : `<p class="vacio">Aún no has publicado horarios.</p>`;

      zona.innerHTML = `
        ${aviso ? msg(aviso, "ok") : ""}
        <form id="formBloque" class="tarjeta" novalidate>
          <p class="tarjeta__titulo">Publicar disponibilidad</p>
          <p class="texto-chico">Elige un rango (por ejemplo 09:00 a 12:00) o todo el día: HYDISA lo divide en espacios de ${Number(duracion)} minutos que los usuarios pueden reservar. Horario de operación: ${esc(apertura)} – ${esc(cierre)}. Las horas son las de este computador.</p>
          <label class="campo"><span>Fecha</span><input name="fecha" type="date" min="${App.hoyISO()}"></label>
          <div class="fila">
            <label class="campo"><span>Inicio</span><input name="inicio" type="time" min="${esc(apertura)}" max="${esc(cierre)}"></label>
            <label class="campo"><span>Fin</span><input name="fin" type="time" min="${esc(apertura)}" max="${esc(cierre)}"></label>
          </div>
          <label class="permiso"><input type="checkbox" name="todo_el_dia"><span>Todo el día (${esc(apertura)} – ${esc(cierre)})</span></label>
          <label class="permiso"><input type="checkbox" name="reemplazar"><span>Reemplazar los espacios libres que se crucen (las citas reservadas no cambian)</span></label>
          <div id="mensajes"></div>
          <button class="boton" type="submit">Publicar disponibilidad</button>
        </form>
        <p class="subtitulo" style="margin:16px 0 0">Bloques publicados</p>${lista}`;

      const f = zona.querySelector("#formBloque");
      f.elements.inicio.addEventListener("change", () => {          // comodidad: sugiere un fin a una duración de cita
        if (f.elements.inicio.value && !f.elements.fin.value) f.elements.fin.value = sumarMinutos(f.elements.inicio.value, Number(duracion));
      });
      f.elements.todo_el_dia.addEventListener("change", () => {     // "todo el día" no necesita inicio ni fin
        const todo = f.elements.todo_el_dia.checked;
        f.elements.inicio.disabled = f.elements.fin.disabled = todo;
      });
      f.addEventListener("submit", async (e) => {
        e.preventDefault();
        const boton = f.querySelector("button[type=submit]");
        boton.disabled = true;
        try {
          const todo = f.elements.todo_el_dia.checked;
          const r = await App.api.admin.publicarRango({
            fecha: f.elements.fecha.value, inicio: todo ? null : f.elements.inicio.value, fin: todo ? null : f.elements.fin.value,
            todo_el_dia: todo, reemplazar: f.elements.reemplazar.checked });
          let texto = `Disponibilidad publicada: ${r.bloques.length} espacio(s) de ${Number(duracion)} min, ya reservables por los usuarios.`;
          if (r.reemplazados) texto += ` Reemplazados: ${r.reemplazados}.`;
          if (r.conservados) texto += ` Citas reservadas conservadas: ${r.conservados}.`;
          if (r.omitidos_pasados) texto += ` Omitidos por ya haber pasado: ${r.omitidos_pasados}.`;
          if (r.sobrante_min) texto += ` Sobraron ${r.sobrante_min} min sin publicar.`;
          App.aviso("Disponibilidad publicada");
          agenda(texto);
        } catch (error) { boton.disabled = false; alFallar(error, f.querySelector("#mensajes")); }
      });
      zona.querySelectorAll("[data-eliminar]").forEach((b) => b.addEventListener("click", async () => {
        if (!confirm("¿Eliminar este bloque libre?")) return;
        try { await App.api.admin.eliminarBloque(Number(b.dataset.eliminar)); App.aviso("Bloque eliminado"); agenda(); }
        catch (error) { alFallar(error, zona); }
      }));
    } catch (error) { alFallar(error, zona); }
  }

  App.vistas.admin = {
    titulo: "Administración",
    pintar: () => App.esAdmin() ? `<div id="admin"></div>`
      : `<p class="vacio">No tienes permiso para ver esta sección.</p>`,
    activar(c) {
      if (!App.esAdmin()) return;
      raiz = c.querySelector("#admin");
      raiz.innerHTML = `<div id="alertasSos"></div><div id="contenidoAdmin"></div>`;
      cont = raiz.querySelector("#contenidoAdmin");
      pestana = "usuarios";
      dibujar();
      refrescarAlertas();
      /* Actualización periódica (sin tiempo real): cada 15 s mientras esta pantalla esté abierta */
      clearInterval(temporizador);
      temporizador = setInterval(refrescarAlertas, 15000);
      App.limpiar = () => clearInterval(temporizador);
    }
  };
})();
