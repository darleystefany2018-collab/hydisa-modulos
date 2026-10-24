/* ==================================================================
   API: CONEXIÓN CON EL SERVIDOR DE PYTHON (servidor.py)
   Para qué sirve: es el "teléfono" entre la pantalla y las clases de
   Python. Cada función de main.py (registrar, iniciar sesión, cargar
   PDF, historial, ver ruta, marcar actividad, exportar PDF) se pide
   aquí con App.api.llamar(...).
   La sesión (token) se guarda en el navegador para no pedir la
   contraseña en cada visita.
   ================================================================== */
const CLAVE_SESION = "hydisa_sesion_v1";

App.api = {
  /* Si la página se abrió con http://127.0.0.1:8000 usa esa misma dirección;
     si se abrió con doble clic en index.html (file://) apunta al servidor local. */
  base: location.protocol.startsWith("http") ? "" : "http://127.0.0.1:8000",
  token: null,
  usuario: null,

  /* Recupera la sesión guardada */
  cargarSesion() {
    try {
      const guardado = JSON.parse(localStorage.getItem(CLAVE_SESION) || "null");
      if (guardado) { this.token = guardado.token; this.usuario = guardado.usuario; }
    } catch (e) { /* sin almacenamiento: la sesión dura solo esta visita */ }
  },
  guardarSesion(token, usuario) {
    this.token = token; this.usuario = usuario;
    try { localStorage.setItem(CLAVE_SESION, JSON.stringify({ token, usuario })); } catch (e) { /* nada */ }
  },
  borrarSesion() {
    this.token = null; this.usuario = null;
    try { localStorage.removeItem(CLAVE_SESION); } catch (e) { /* nada */ }
  },

  /* Hace una petición. Opciones: json (objeto), cuerpo (archivo), cabeceras, blob (descarga).
     Lanza Error con el mensaje del servidor; error.codigo trae el número HTTP.
     Si el servidor no responde, error.sinServidor = true. */
  async llamar(metodo, ruta, { json, cuerpo, cabeceras = {}, blob = false } = {}) {
    const opciones = { method: metodo, headers: { ...cabeceras } };
    if (this.token) opciones.headers.Authorization = "Bearer " + this.token;
    if (json !== undefined) { opciones.headers["Content-Type"] = "application/json"; opciones.body = JSON.stringify(json); }
    if (cuerpo !== undefined) opciones.body = cuerpo;

    let respuesta;
    try {
      respuesta = await fetch(this.base + "/api/" + ruta, opciones);
    } catch (e) {
      const error = new Error("No se pudo conectar con el servidor de HYDISA.");
      error.sinServidor = true;
      throw error;
    }
    if (!respuesta.ok) {
      let mensaje = "Ocurrió un error inesperado.";
      try { mensaje = (await respuesta.json()).error || mensaje; } catch (e) { /* sin detalle */ }
      /* 401 con sesión guardada = el servidor se reinició: pedir iniciar sesión otra vez */
      const error = new Error(mensaje);
      error.codigo = respuesta.status;
      if (respuesta.status === 401 && this.token) { this.borrarSesion(); error.sesionVencida = true; }
      throw error;
    }
    return blob ? respuesta.blob() : respuesta.json();
  },

  /* ----- Una función por cada opción de main.py ----- */
  async iniciarSesion(correo, clave) {
    const r = await this.llamar("POST", "login", { json: { correo, clave } });
    this.guardarSesion(r.token, r.usuario);
    return r.usuario;
  },
  async cerrarSesion() {
    try { await this.llamar("POST", "logout"); } catch (e) { /* da igual */ }
    this.borrarSesion();
  },
  cargarPdf: (archivo) => App.api.llamar("POST", "reportes", {
    cuerpo: archivo, cabeceras: { "X-Nombre-Archivo": encodeURIComponent(archivo.name), "Content-Type": "application/pdf" } }),
  historial: () => App.api.llamar("GET", "reportes"),
  verRuta: (id) => App.api.llamar("GET", `reportes/${id}/ruta`),
  palabras: (id) => App.api.llamar("GET", `reportes/${id}/palabras`),
  marcarActividad: (id, n) => App.api.llamar("POST", `reportes/${id}/actividades/${n}/cumplir`),
  exportarPdf: (id) => App.api.llamar("GET", `reportes/${id}/pdf`, { blob: true }),

  /* ----- Administración (el servidor responde 403 a quien no sea administrador) ----- */
  admin: {
    usuarios: () => App.api.llamar("GET", "admin/usuarios"),
    usuario: (id) => App.api.llamar("GET", `admin/usuarios/${id}`),
    crear: (datos) => App.api.llamar("POST", "admin/usuarios", { json: datos }),
    permisos: (id, lista) => App.api.llamar("POST", `admin/usuarios/${id}/permisos`, { json: { permisos: lista } }),
    reporte: (id, reporteId) => App.api.llamar("GET", `admin/usuarios/${id}/reportes/${reporteId}`)
  }
};

/* OJO: estas dos preguntas solo sirven para mostrar u ocultar botones.
   La seguridad real está en el servidor, que revisa el rol y los permisos en cada solicitud. */
App.esAdmin = () => !!(App.api.usuario && App.api.usuario.es_admin);
App.puede = (permiso) => !!(App.api.usuario && (App.api.usuario.es_admin || (App.api.usuario.permisos || []).includes(permiso)));

App.api.cargarSesion();
