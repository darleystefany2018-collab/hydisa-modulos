/* ==================================================================
   ALMACÉN: ESTADO DE LA PERSONA Y GUARDADO
   Para qué sirve: guarda todo lo que la persona hace (días completados,
   registros, sesiones, notificaciones...) en el navegador (localStorage)
   para que no se pierda al cerrar la página.
   OJO: por ahora los datos quedan SOLO en este navegador. Para tenerlos
   en cualquier dispositivo hay que conectarlos a la base de datos.
   ================================================================== */
const CLAVE_BASE = "hydisa_estado_v1";
/* Cada cuenta tiene su propio guardado: si otra persona entra en el mismo computador, no ve tus datos */
const CLAVE_GUARDADO_ACTUAL = () => CLAVE_BASE + (App.api && App.api.usuario ? "_u" + App.api.usuario.id : "");
const TOTAL_DIAS = App.ACTIVIDADES.length;

/* Fecha de hoy como texto "2026-10-22" (en la hora local de la persona) */
App.hoyISO = () => {
  const f = new Date();
  return `${f.getFullYear()}-${String(f.getMonth() + 1).padStart(2, "0")}-${String(f.getDate()).padStart(2, "0")}`;
};

/* Estado de una persona nueva */
function estadoInicial() {
  return {
    usuario: { nombre: "Ana" },
    intencion: App.INTENCIONES[0],
    inicioRuta: App.hoyISO(),
    completados: [],            // números de día ya terminados, ej. [1, 2, 3]
    registros: [],              // {id, fecha, animo, nota}
    sesiones: [],               // {id, fecha, hora, tema}
    notificaciones: [{ id: 1, texto: "¡Bienvenida a HYDISA! Tu ruta de 11 días comienza hoy.", leida: false, fecha: App.hoyISO() }]
  };
}

/* Lee lo guardado (si no hay nada o falla, empieza desde cero) */
App.cargar = () => {
  try {
    const guardado = localStorage.getItem(CLAVE_GUARDADO_ACTUAL());
    App.estado = guardado ? { ...estadoInicial(), ...JSON.parse(guardado) } : estadoInicial();
  } catch (error) {
    App.estado = estadoInicial();
  }
};

/* Guarda el estado y refresca la cabecera (saludo y punto rojo) */
App.guardar = () => {
  try { localStorage.setItem(CLAVE_GUARDADO_ACTUAL(), JSON.stringify(App.estado)); } catch (error) { /* sin almacenamiento: sigue en memoria */ }
  if (App.refrescarCabecera) App.refrescarCabecera();
};

/* Identificador sencillo para registros, sesiones y notificaciones */
App.nuevoId = () => Date.now() + Math.floor(Math.random() * 1000);

/* ---------- Cálculos de la ruta ---------- */
App.diasCompletados = () => App.estado.completados.length;
App.rutaTerminada   = () => App.diasCompletados() >= TOTAL_DIAS;
App.diaActual       = () => Math.min(App.diasCompletados() + 1, TOTAL_DIAS);
App.porcentaje      = () => Math.round((App.diasCompletados() / TOTAL_DIAS) * 100);

/* Fecha (texto) que le corresponde al día n de la ruta */
App.fechaDelDia = (n) => {
  const f = new Date(App.estado.inicioRuta + "T00:00:00");
  f.setDate(f.getDate() + (n - 1));
  return f;
};

/* Marca como terminado el día actual y avisa con una notificación */
App.completarDiaActual = () => {
  if (App.rutaTerminada()) return false;
  const dia = App.diaActual();
  App.estado.completados.push(dia);
  App.agregarNotificacion(App.rutaTerminada()
    ? "🎉 ¡Completaste tu ruta de 11 días! Mira tu evolución."
    : `Completaste el día ${dia}. ¡Sigue así!`);
  App.guardar();
  return true;
};

/* Crea una notificación nueva (aparece con el punto rojo en la campana) */
App.agregarNotificacion = (texto) => {
  App.estado.notificaciones.unshift({ id: App.nuevoId(), texto, leida: false, fecha: App.hoyISO() });
  App.estado.notificaciones = App.estado.notificaciones.slice(0, 30);
};

/* Vuelve la ruta al día 1 (mantiene el nombre y la intención) */
App.reiniciarRuta = () => {
  App.estado.completados = [];
  App.estado.inicioRuta = App.hoyISO();
  App.agregarNotificacion("Reiniciaste tu ruta. ¡Un nuevo comienzo!");
  App.guardar();
};

/* Borra TODO lo guardado y vuelve al estado inicial */
App.borrarTodo = () => {
  try { localStorage.removeItem(CLAVE_GUARDADO_ACTUAL()); } catch (error) { /* nada */ }
  App.estado = estadoInicial();
  App.guardar();
};
