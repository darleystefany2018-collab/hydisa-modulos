/* ==================================================================
   PANTALLA "REGISTRO"
   Para qué sirve: diario de bienestar. La persona elige cómo se siente
   (1 a 5), escribe una nota opcional y la guarda. Puede borrar registros.
   Estos registros alimentan la pantalla "Evolución".
   ================================================================== */
App.vistas.registro = {
  titulo: "Registro",
  pintar() {
    const animos = App.ANIMOS.map((a) => `
      <button type="button" class="animo" data-valor="${a.valor}" aria-pressed="false">
        <span class="animo__emoji">${a.emoji}</span><span class="animo__nombre">${a.nombre}</span>
      </button>`).join("");

    const registros = App.estado.registros.length
      ? App.estado.registros.map((r) => {
          const animo = App.ANIMOS.find((a) => a.valor === r.animo);
          return `<li class="item item--registro">
            <span class="animo__emoji">${animo.emoji}</span>
            <span class="item__texto"><strong>${animo.nombre} · ${App.fechaDeTexto(r.fecha)}</strong>
              <small>${r.nota ? esc(r.nota) : "Sin nota"}</small></span>
            <button class="icono-btn" data-borrar="${r.id}" aria-label="Borrar registro">${icono("i-trash")}</button>
          </li>`;
        }).join("")
      : `<li class="vacio">Aún no tienes registros. ¡Cuéntale a tu diario cómo te sientes!</li>`;

    return `
      <section class="tarjeta">
        <h3 class="tarjeta__titulo">¿Cómo te sientes hoy?</h3>
        <div class="animos">${animos}</div>
        <label class="campo"><span>Nota (opcional)</span>
          <textarea id="notaRegistro" rows="3" maxlength="300" placeholder="¿Qué pasó hoy? ¿Qué necesitas?"></textarea></label>
        <button id="btnGuardarRegistro" class="boton">Guardar registro</button>
      </section>
      <h3 class="subtitulo">Tus registros</h3>
      <ul class="lista">${registros}</ul>`;
  },
  activar(c) {
    let elegido = 0;
    c.querySelectorAll(".animo").forEach((b) => b.addEventListener("click", () => {
      elegido = Number(b.dataset.valor);
      c.querySelectorAll(".animo").forEach((x) => {
        x.classList.toggle("animo--activo", x === b);
        x.setAttribute("aria-pressed", String(x === b));
      });
    }));
    c.querySelector("#btnGuardarRegistro").addEventListener("click", () => {
      if (!elegido) return App.aviso("Elige cómo te sientes");
      App.estado.registros.unshift({ id: App.nuevoId(), fecha: App.hoyISO(), animo: elegido,
                                     nota: c.querySelector("#notaRegistro").value.trim() });
      App.guardar();
      App.aviso("Registro guardado");
      App.mostrar();
    });
    c.querySelectorAll("[data-borrar]").forEach((b) => b.addEventListener("click", () => {
      App.estado.registros = App.estado.registros.filter((r) => String(r.id) !== b.dataset.borrar);
      App.guardar();
      App.mostrar();
    }));
  }
};
