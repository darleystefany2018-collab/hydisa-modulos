/* ==================================================================
   MÓDULO 0 - ACCESO (inicio de sesión)
   Para qué sirve: es lo PRIMERO que ve la persona, antes de toda la
   app, como en cualquier red social. Si no hay sesión abierta se muestra
   esta pantalla a pantalla completa; al entrar, aparece la app.
   Aquí NO se pueden crear cuentas: solo el administrador puede hacerlo,
   desde Administración (después de iniciar sesión con su cuenta). Esa
   regla la aplica el servidor; esta pantalla simplemente no ofrece la opción.
   ================================================================== */
(() => {
  const caja = () => $("pantallaAcceso");

  const mostrarPantalla = (visible) => {
    document.body.classList.toggle("sin-sesion", visible);
    caja().hidden = !visible;
    if (!visible) caja().innerHTML = "";        // no deja el formulario (ni lo escrito) escondido en la página
  };

  /* Muestra la pantalla de acceso (y cierra cualquier ventana de la app) */
  App.mostrarAcceso = (aviso = "") => {
    if (App.cerrarHoja) App.cerrarHoja();
    if (App.abrirMenu) App.abrirMenu(false);
    mostrarPantalla(true);
    dibujar(aviso);
  };

  /* Entra a la app con la sesión ya iniciada */
  App.entrarALaApp = () => {
    App.cargar();                               // carga los datos de ESTA cuenta
    if (App.estado.usuario.nombre === "Ana") App.estado.usuario.nombre = App.api.usuario.nombre.split(" ")[0];
    App.guardar();
    App.pintarNavegacion();                     // el menú muestra "Administración" solo si es administrador
    mostrarPantalla(false);
    if (location.hash !== "#/inicio" && location.hash !== "") location.hash = "#/inicio";
    App.mostrar();
  };

  App.cerrarSesionCompleta = async () => {
    await App.api.cerrarSesion();
    App.mostrarAcceso();
  };

  /* Arranque: si hay una sesión guardada, el servidor la confirma; si no, pide entrar */
  App.iniciarAcceso = async () => {
    if (!App.api.token) return App.mostrarAcceso();
    try {
      const { usuario } = await App.api.llamar("GET", "yo");
      App.api.guardarSesion(App.api.token, usuario);
      App.entrarALaApp();
    } catch (error) {
      App.mostrarAcceso(error.sinServidor
        ? error.message + " Ábrela con iniciar_hydisa.bat o con tu acceso directo."
        : "Tu sesión terminó. Entra otra vez.");
    }
  };

  function dibujar(mensaje = "") {
    caja().innerHTML = `
      <div class="acceso__marco">
        <img class="acceso__logo" src="img/logo-hydisa.png" alt="HYDISA - Healthy Data Analysis">
        <h1 class="acceso__titulo">Bienvenido a HYDISA</h1>
        <p class="acceso__lema">${esc(App.APP.lema)}</p>

        <form id="formAcceso" class="acceso__tarjeta" novalidate>
          <input name="correo" type="email" placeholder="Correo electrónico" autocomplete="email" aria-label="Correo electrónico">
          <div class="acceso__clave">
            <input name="clave" type="password" placeholder="Contraseña" autocomplete="current-password" aria-label="Contraseña">
            <button type="button" id="verClave" class="icono-btn" aria-label="Mostrar u ocultar contraseña">${icono("i-eye")}</button>
          </div>
          <p id="mensajeAcceso" class="mensaje mensaje--error" role="alert" ${mensaje ? "" : "hidden"}>${esc(mensaje)}</p>
          <button id="btnEnviar" class="boton" type="submit">Iniciar sesión</button>
        </form>
        <p class="texto-chico acceso__pie">¿No tienes cuenta? Solicítala al administrador de HYDISA.<br>HYDISA no emite diagnósticos ni recomendaciones médicas.</p>
      </div>`;

    const f = caja().querySelector("#formAcceso");
    f.querySelector("#verClave").addEventListener("click", () => {
      f.elements.clave.type = f.elements.clave.type === "password" ? "text" : "password";
    });
    f.addEventListener("submit", (e) => { e.preventDefault(); enviar(f); });
    f.elements.correo.focus();
  }

  async function enviar(f) {
    const aviso = caja().querySelector("#mensajeAcceso");
    const fallo = (texto) => { aviso.textContent = texto; aviso.hidden = false; };
    const correo = f.elements.correo.value.trim(), clave = f.elements.clave.value;
    if (!correo || !clave) return fallo("Escribe tu correo y tu contraseña.");
    const boton = f.querySelector("#btnEnviar");
    boton.disabled = true; boton.textContent = "Un momento…";
    try {
      const usuario = await App.api.iniciarSesion(correo, clave);
      App.entrarALaApp();
      App.aviso(`Hola de nuevo, ${usuario.nombre.split(" ")[0]}`);
    } catch (error) {
      boton.disabled = false; boton.textContent = "Iniciar sesión";
      fallo(error.sinServidor ? error.message + " Ábrela con iniciar_hydisa.bat o con tu acceso directo." : error.message);
    }
  }
})();
