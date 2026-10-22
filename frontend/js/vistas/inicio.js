/* ==================================================================
   PANTALLA DE INICIO
   Reúne cinco módulos:
     MÓDULO 3 - Bienvenida: logo de HYDISA, lema y frase que inspira.
     MÓDULO 4 - Intención personal: la que eligió la persona (se puede cambiar).
     MÓDULO 5 - Progreso de la ruta: círculos por día, día actual y porcentaje.
     MÓDULO 6 - Actividad principal: la actividad de hoy y el botón para comenzar.
     MÓDULO 7 - Accesos rápidos: atajos a evolución, calendario, acompañamiento y más.
   ================================================================== */
App.vistas.inicio = {
  pintar() {
    const e = App.estado;
    const dia = App.diaActual();
    const terminada = App.rutaTerminada();
    const act = App.ACTIVIDADES[dia - 1];

    /* MÓDULO 5: un círculo por día (hecho, actual o pendiente) */
    let circulos = "";
    for (let n = 1; n <= TOTAL_DIAS; n++) {
      if (e.completados.includes(n))      circulos += `<li class="dia dia--hecho">${icono("i-check")}</li>`;
      else if (n === dia && !terminada)   circulos += `<li class="dia dia--actual" aria-current="step">${n}</li>`;
      else                                circulos += `<li class="dia">${n}</li>`;
    }

    /* MÓDULO 6: actividad de hoy, o mensaje final si ya terminó */
    const actividad = terminada ? `
      <div class="actividad__fin">
        <p class="actividad__titulo">🎉 ¡Completaste tu ruta!</p>
        <p class="actividad__descripcion">Mira cómo te fue en tu evolución o empieza una ruta nueva desde tu perfil.</p>
      </div>
      <button class="boton" data-ir="evolucion">Ver mi evolución ${icono("i-arrow")}</button>` : `
      <div class="actividad__cuerpo">
        <div class="actividad__imagen" aria-hidden="true">${App.ilustracion}</div>
        <div>
          <h3 class="actividad__titulo">${esc(act.titulo)}</h3>
          <p class="actividad__descripcion">${esc(act.descripcion)}</p>
          <div class="actividad__datos">
            <span>${icono("i-clock", "icono icono--chico")} ${act.minutos} minutos</span>
            <span>${icono("i-leaf", "icono icono--chico")} ${act.tipo}</span>
          </div>
        </div>
      </div>
      <button class="boton" data-ir="actividad">Comenzar actividad ${icono("i-arrow")}</button>`;

    /* MÓDULO 7: cuatro atajos */
    const accesos = [
      { ir: "evolucion",      icono: "i-chart",    nombre: "Mi evolución",   detalle: "Ver mi progreso" },
      { ir: "calendario",     icono: "i-calendar", nombre: "Calendario",     detalle: "Toda la ruta" },
      { ir: "acompanamiento", icono: "i-heart",    nombre: "Acompañamiento", detalle: "Mis sesiones" },
      { ir: "recursos",       icono: "i-more",     nombre: "Más",            detalle: "Recursos" }
    ].map((a) => `
      <button class="acceso" data-ir="${a.ir}">
        ${icono(a.icono)}<span class="acceso__nombre">${a.nombre}</span><span class="acceso__detalle">${a.detalle}</span>
      </button>`).join("");

    return `
      <!-- MÓDULO 3: BIENVENIDA -->
      <section class="bienvenida">
        <img class="logo" src="img/logo-hydisa.png" alt="HYDISA - Healthy Data Analysis. Analizamos datos, cuidamos vidas.">
        <h1 class="solo-lectores">${App.APP.nombre}</h1>
        <p class="bienvenida__lema">${App.APP.lema}</p>
        <p class="frase">${icono("i-leaf", "icono icono--chico")}<span>${App.APP.frase}</span></p>
      </section>

      <!-- MÓDULO 4: INTENCIÓN PERSONAL -->
      <section class="tarjeta intencion">
        <div class="intencion__icono">${icono("i-sun")}</div>
        <div>
          <p class="texto-chico">Tu intención actual</p>
          <p class="intencion__texto">${esc(e.intencion)}</p>
          <button id="btnCambiarIntencion" class="enlace">Cambiar intención ${icono("i-chevron", "icono icono--mini")}</button>
        </div>
      </section>

      <!-- MÓDULO 5: PROGRESO DE LA RUTA -->
      <section class="tarjeta">
        <h2 class="tarjeta__titulo">Tu ruta de ${TOTAL_DIAS} días</h2>
        <ol class="dias">${circulos}</ol>
        <div class="progreso__textos">
          <span>${terminada ? "Ruta completa" : `Día ${dia} de ${TOTAL_DIAS}`}</span>
          <span>${App.porcentaje()} % completado</span>
        </div>
        <div class="barra" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${App.porcentaje()}">
          <div class="barra__relleno" style="width:${App.porcentaje()}%"></div>
        </div>
      </section>

      <!-- MÓDULO 6: ACTIVIDAD PRINCIPAL -->
      <section class="tarjeta actividad">
        <div class="actividad__cabecera">
          <span class="actividad__etiqueta">
            <span class="actividad__hoja">${icono("i-leaf", "icono icono--chico")}</span>Actividad de hoy
          </span>
          <span class="texto-chico">${terminada ? "" : `Día ${dia}`}</span>
        </div>
        ${actividad}
        <button class="enlace enlace--centro" data-ir="ruta">Ver todas las actividades ${icono("i-chevron", "icono icono--mini")}</button>
      </section>

      <!-- MÓDULO 7: ACCESOS RÁPIDOS -->
      <section class="accesos" aria-label="Accesos rápidos">${accesos}</section>`;
  },
  activar(c) {
    c.querySelector("#btnCambiarIntencion").addEventListener("click", () => App.abrirIntencion());
  }
};

/* Ilustración de la actividad (después puede cambiarse por una foto real) */
App.ilustracion = `
  <svg viewBox="0 0 120 120" width="100%" height="100%" preserveAspectRatio="xMidYMid slice">
    <defs><linearGradient id="fondoImg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#efe3cf"/><stop offset="1" stop-color="#d9c4a3"/></linearGradient></defs>
    <rect width="120" height="120" fill="url(#fondoImg)"/>
    <path d="M80 70c-2-24 8-42 26-46 4 22-6 40-26 46z" fill="#5d8a5f"/>
    <path d="M84 72c-14-12-16-28-8-40 14 8 16 26 8 40z" fill="#7aa06f"/>
    <rect x="66" y="64" width="34" height="26" rx="6" fill="#f3ece0"/>
    <rect x="10" y="78" width="70" height="34" rx="4" fill="#4a4137" transform="rotate(-8 10 78)"/>
    <rect x="14" y="76" width="66" height="30" rx="3" fill="#f6efe3" transform="rotate(-8 14 76)"/>
    <path d="M24 90h40M26 98h30" stroke="#cdbfa6" stroke-width="2" transform="rotate(-8 24 90)"/>
  </svg>`;
