/* ==================================================================
   COMPONENTE COMPARTIDO: LISTA DE DÍAS CON HORAS DESPLEGABLES
   Para qué sirve: es la misma forma de ver la agenda para la persona que
   reserva (vistas/acompanamiento.js) y para el administrador
   (vistas/admin.js, pestaña Agenda). Primero se ven solo los días; al
   elegir uno se despliegan sus horas (uno abierto a la vez).
   Lo que cambia entre una vista y otra se pasa como parámetro:
     resumen(bloquesDelDia) -> texto bajo la fecha ("3 horarios libres")
     hora(bloque)           -> HTML de cada hora (botón de reservar, de cita, etc.)
   `estado` = { dia: null } guarda qué día está abierto; así se conserva
   cuando la pantalla se vuelve a dibujar tras reservar o cancelar.
   ================================================================== */
App.agendaDias = {
  /* Devuelve el HTML de la lista. `bloques` debe venir ordenado por fecha y hora (el servidor ya lo hace). */
  html(bloques, estado, { resumen, hora }) {
    const porDia = {};
    bloques.forEach((b) => (porDia[b.fecha] = porDia[b.fecha] || []).push(b));
    if (!porDia[estado.dia]) estado.dia = null;                   // el día abierto ya no tiene horas
    return `<ul class="agenda-dias">${Object.entries(porDia).map(([fecha, delDia]) => {
      const abierto = fecha === estado.dia;
      return `
      <li class="agenda-dia ${abierto ? "agenda-dia--abierto" : ""}">
        <button class="agenda-dia__boton" data-dia="${esc(fecha)}" aria-expanded="${abierto}">
          <span class="item__texto"><strong>${esc(App.fechaDeTexto(fecha))}</strong><small>${esc(resumen(delDia))}</small></span>
          ${icono("i-chevron", "icono icono--mini agenda-dia__flecha")}
        </button>
        <div class="horarios agenda-dia__horas" ${abierto ? "" : "hidden"}>${delDia.map(hora).join("")}</div>
      </li>`; }).join("")}</ul>`;
  },

  /* Conecta los botones de los días dentro de `raiz` (abrir/cerrar sin pedir datos otra vez al servidor) */
  activar(raiz, estado) {
    raiz.querySelectorAll("[data-dia]").forEach((boton) => boton.addEventListener("click", () => {
      estado.dia = estado.dia === boton.dataset.dia ? null : boton.dataset.dia;
      raiz.querySelectorAll(".agenda-dia").forEach((li) => {
        const abierto = li.querySelector("[data-dia]").dataset.dia === estado.dia;
        li.classList.toggle("agenda-dia--abierto", abierto);
        li.querySelector("[data-dia]").setAttribute("aria-expanded", abierto);
        li.querySelector(".agenda-dia__horas").hidden = !abierto;
      });
    }));
  }
};
