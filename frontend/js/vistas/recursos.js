/* ==================================================================
   PANTALLA "RECURSOS" (acceso rápido "Más")
   Para qué sirve: material de apoyo. Incluye un ejercicio de respiración
   guiada que funciona de verdad (inhala, sostén, exhala) y textos con
   hábitos sencillos. Aquí también se aclara que HYDISA no da diagnósticos.
   ================================================================== */
App.vistas.recursos = {
  titulo: "Recursos",
  pintar() {
    return `<ul class="lista">${App.RECURSOS.map((r) => `
      <li class="item"><button class="item__boton" data-recurso="${r.id}">
        <span class="item__texto"><strong>${r.titulo}</strong><small>${r.resumen}</small></span>
        ${icono("i-chevron")}</button></li>`).join("")}</ul>`;
  },
  activar(c) {
    c.querySelectorAll("[data-recurso]").forEach((b) => b.addEventListener("click", () => {
      const r = App.RECURSOS.find((x) => x.id === b.dataset.recurso);
      if (r.tipo === "respiracion") return App.abrirRespiracion(r.titulo);
      App.abrirHoja(r.titulo, `<ul class="puntos">${r.texto.map((t) => `<li>${esc(t)}</li>`).join("")}</ul>`);
    }));
  }
};

/* Ejercicio de respiración 4-4-4: cambia de fase cada 4 segundos */
App.abrirRespiracion = (titulo) => {
  const fases = [{ texto: "Inhala", clase: "respira--inhala" }, { texto: "Sostén", clase: "respira--sosten" },
                 { texto: "Exhala", clase: "respira--exhala" }];
  let temporizador = null, paso = 0;
  const detener = () => { clearInterval(temporizador); temporizador = null; };

  App.abrirHoja(titulo, `
      <div class="respira-caja"><div id="respira" class="respira"><span id="respiraTexto">Listo</span></div></div>
      <p class="texto-chico" style="text-align:center">Cuatro segundos en cada fase. Hazlo con calma.</p>
      <button id="btnRespirar" class="boton">Comenzar</button>`,
    (cuerpo) => {
      const circulo = cuerpo.querySelector("#respira"), texto = cuerpo.querySelector("#respiraTexto");
      const boton = cuerpo.querySelector("#btnRespirar");
      const siguiente = () => {
        const f = fases[paso % fases.length];
        circulo.className = "respira " + f.clase;
        texto.textContent = f.texto;
        paso++;
      };
      boton.addEventListener("click", () => {
        if (temporizador) { detener(); boton.textContent = "Comenzar"; texto.textContent = "Listo"; circulo.className = "respira"; return; }
        paso = 0; siguiente(); temporizador = setInterval(siguiente, 4000); boton.textContent = "Detener";
      });
    },
    detener);                                              // al cerrar la hoja se detiene el temporizador
};
