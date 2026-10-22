/* ==================================================================
   PANTALLA "ACTIVIDAD" (botón "Comenzar actividad")
   Para qué sirve: muestra la actividad de hoy con un temporizador
   (iniciar, pausar, reiniciar) y el botón para marcarla como completada,
   que avanza la ruta, el porcentaje y crea una notificación.
   ================================================================== */
App.vistas.actividad = {
  titulo: "Actividad de hoy",
  pintar() {
    if (App.rutaTerminada()) {
      return `<section class="tarjeta"><p class="actividad__titulo">🎉 ¡Ya completaste tu ruta!</p>
              <p class="actividad__descripcion">Puedes empezar una nueva desde tu perfil.</p>
              <button class="boton" data-ir="evolucion">Ver mi evolución</button></section>`;
    }
    const dia = App.diaActual();
    const a = App.ACTIVIDADES[dia - 1];
    return `
      <section class="tarjeta">
        <p class="texto-chico">Día ${dia} de ${TOTAL_DIAS} · ${a.tipo}</p>
        <h3 class="actividad__titulo">${esc(a.titulo)}</h3>
        <p class="actividad__descripcion">${esc(a.descripcion)}</p>
        <div class="reloj" id="reloj" aria-live="off">${App.formatoTiempo(a.minutos * 60)}</div>
        <div class="fila">
          <button id="btnIniciar" class="boton boton--sec">Iniciar</button>
          <button id="btnReiniciar" class="boton boton--sec">Reiniciar</button>
        </div>
        <button id="btnCompletar" class="boton">Marcar como completada ${icono("i-check")}</button>
      </section>`;
  },
  activar(c) {
    if (App.rutaTerminada()) return;
    const total = App.ACTIVIDADES[App.diaActual() - 1].minutos * 60;
    let restante = total, reloj = null;
    const pantalla = c.querySelector("#reloj"), boton = c.querySelector("#btnIniciar");

    const parar = () => { clearInterval(reloj); reloj = null; boton.textContent = "Iniciar"; };
    App.limpiar = parar;                                   // el router lo llama al salir de la pantalla

    boton.addEventListener("click", () => {
      if (reloj) return parar();                           // si corría, se pausa
      if (restante <= 0) restante = total;
      boton.textContent = "Pausar";
      reloj = setInterval(() => {
        restante--;
        pantalla.textContent = App.formatoTiempo(restante);
        if (restante <= 0) { parar(); App.aviso("¡Tiempo cumplido! Ya puedes marcarla como completada."); }
      }, 1000);
    });
    c.querySelector("#btnReiniciar").addEventListener("click", () => {
      parar(); restante = total; pantalla.textContent = App.formatoTiempo(total);
    });
    c.querySelector("#btnCompletar").addEventListener("click", () => {
      App.completarDiaActual();
      App.aviso("¡Actividad completada!");
      App.navegar("inicio");
    });
  }
};

/* Convierte segundos en "10:00" */
App.formatoTiempo = (seg) => `${String(Math.floor(seg / 60)).padStart(2, "0")}:${String(seg % 60).padStart(2, "0")}`;
