/* ==================================================================
   MÓDULO 0 - ACCESO (inicio de sesión y crear cuenta)
   Para qué sirve: es lo PRIMERO que ve la persona, antes de toda la
   app, como en cualquier red social. Si no hay sesión abierta se muestra
   esta pantalla a pantalla completa; al entrar, aparece la app.
     main.py  2. Iniciar sesión  -> formulario "Iniciar sesión"
     main.py  1. Registrarse     -> formulario "Crear cuenta nueva"
   Los datos viajan al servidor de Python (App.api) y se guardan en la
   base de datos; la contraseña nunca se guarda en texto plano.
   ================================================================== */
(() => {
  let modo = "entrar";                         // "entrar" | "crear"
  const caja = () => $("pantallaAcceso");

  const mostrarPantalla = (visible) => {
    document.body.classList.toggle("sin-sesion", visible);
    caja().hidden = !visible;
  };

  /* Muestra la pantalla de acceso (y cierra cualquier ventana de la app) */
  App.mostrarAcceso = (aviso = "") => {
    if (App.cerrarHoja) App.cerrarHoja();
    if (App.abrirMenu) App.abrirMenu(false);
    mostrarPantalla(true);
    dibujar(aviso, "error");
  };

  /* Entra a la app con la sesión ya iniciada */
  App.entrarALaApp = () => {
    App.cargar();                               // carga los datos de ESTA cuenta
    if (App.estado.usuario.nombre === "Ana") App.estado.usuario.nombre = App.api.usuario.nombre.split(" ")[0];
    App.guardar();
    mostrarPantalla(false);
    if (location.hash !== "#/inicio" && location.hash !== "") location.hash = "#/inicio";
    App.mostrar();
  };

  App.cerrarSesionCompleta = async () => {
    await App.api.cerrarSesion();
    modo = "entrar";
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
      App.mostrarAcceso(error.sinServidor ? "" : "Tu sesión terminó. Entra otra vez.");
      if (error.sinServidor) dibujar(error.message + " Ábrela con iniciar_hydisa.bat o con tu acceso directo.", "error");
    }
  };

  function dibujar(mensaje = "", tipo = "error") {
    const entrar = modo === "entrar";
    caja().innerHTML = `
      <div class="acceso__marco">
        <img class="acceso__logo" src="img/logo-hydisa.png" alt="HYDISA - Healthy Data Analysis">
        <h1 class="acceso__titulo">${entrar ? "Bienvenido a HYDISA" : "Crea tu cuenta"}</h1>
        <p class="acceso__lema">${esc(App.APP.lema)}</p>

        <form id="formAcceso" class="acceso__tarjeta" novalidate>
          ${entrar ? "" : `<input name="nombre" type="text" placeholder="Nombre completo" autocomplete="name" maxlength="60" aria-label="Nombre completo">`}
          <input name="correo" type="email" placeholder="Correo electrónico" autocomplete="email" aria-label="Correo electrónico">
          <div class="acceso__clave">
            <input name="clave" type="password" placeholder="Contraseña${entrar ? "" : " (mínimo 8 caracteres)"}" autocomplete="${entrar ? "current-password" : "new-password"}" aria-label="Contraseña">
            <button type="button" id="verClave" class="icono-btn" aria-label="Mostrar u ocultar contraseña">${icono("i-eye")}</button>
          </div>
          ${entrar ? "" : `<input name="confirmar" type="password" placeholder="Repite la contraseña" autocomplete="new-password" aria-label="Repite la contraseña">`}
          <p id="mensajeAcceso" class="mensaje mensaje--${tipo}" role="alert" ${mensaje ? "" : "hidden"}>${esc(mensaje)}</p>
          <button id="btnEnviar" class="boton" type="submit">${entrar ? "Iniciar sesión" : "Registrarme"}</button>
          <div class="acceso__o"><span>o</span></div>
          <button id="btnCambiar" type="button" class="boton boton--sec">${entrar ? "Crear cuenta nueva" : "Ya tengo una cuenta"}</button>
        </form>
        <p class="texto-chico acceso__pie">Tus datos se guardan de forma segura. HYDISA no emite diagnósticos ni recomendaciones médicas.</p>
      </div>`;

    const f = caja().querySelector("#formAcceso");
    f.querySelector("#verClave").addEventListener("click", () => {
      const campo = f.elements.clave;
      campo.type = campo.type === "password" ? "text" : "password";
    });
    f.querySelector("#btnCambiar").addEventListener("click", () => { modo = entrar ? "crear" : "entrar"; dibujar(); });
    f.addEventListener("submit", (e) => { e.preventDefault(); enviar(f, entrar); });
    (f.elements.nombre || f.elements.correo).focus();
  }

  async function enviar(f, entrar) {
    const aviso = caja().querySelector("#mensajeAcceso");
    const fallo = (texto) => { aviso.className = "mensaje mensaje--error"; aviso.textContent = texto; aviso.hidden = false; };
    const correo = f.elements.correo.value.trim(), clave = f.elements.clave.value;
    if (!correo || !clave) return fallo("Escribe tu correo y tu contraseña.");
    if (!entrar) {
      if (!f.elements.nombre.value.trim()) return fallo("Escribe tu nombre.");
      if (clave !== f.elements.confirmar.value) return fallo("Las contraseñas no coinciden.");
    }
    const boton = f.querySelector("#btnEnviar");
    boton.disabled = true; boton.textContent = "Un momento…";
    try {
      if (!entrar) await App.api.registrar(f.elements.nombre.value, correo, clave);
      await App.api.iniciarSesion(correo, clave);
      modo = "entrar";
      App.entrarALaApp();
      if (!entrar) { App.agregarNotificacion("¡Cuenta creada! Ya puedes cargar tu primer PDF."); App.guardar(); }
      App.aviso(entrar ? `Hola de nuevo, ${App.api.usuario.nombre.split(" ")[0]}` : "¡Cuenta creada!");
    } catch (error) {
      boton.disabled = false; boton.textContent = entrar ? "Iniciar sesión" : "Registrarme";
      fallo(error.sinServidor ? error.message + " Ábrela con iniciar_hydisa.bat o con tu acceso directo." : error.message);
    }
  }
})();
