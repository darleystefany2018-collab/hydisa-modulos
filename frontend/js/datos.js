/* ==================================================================
   DATOS FIJOS DE LA APLICACIÓN
   Para qué sirve: guarda el contenido que no cambia (las 11 actividades
   de la ruta, los recursos y las secciones del menú). Más adelante este
   contenido puede venir de la base de datos de Supabase.
   ================================================================== */

/* Objeto global "App": aquí cuelgan todas las piezas de la aplicación */
const App = { vistas: {}, estado: null };

App.APP = {
  nombre: "HYDISA",
  lema: "Tu espacio para volver a ti",
  frase: "“Pequeñas acciones, grandes cambios”"
};

/* Las 11 actividades de la ruta: una por día (sin contenido médico) */
App.ACTIVIDADES = [
  { titulo: "Respira y llega",              minutos: 5,  tipo: "Respiración", descripcion: "Tres minutos de respiración lenta para llegar al momento presente." },
  { titulo: "Un paseo consciente",          minutos: 15, tipo: "Movimiento",  descripcion: "Camina sin prisa y fíjate en tres sonidos y tres colores a tu alrededor." },
  { titulo: "Tres cosas que agradezco",     minutos: 10, tipo: "Reflexión",   descripcion: "Escribe tres cosas, por pequeñas que sean, que hoy te hicieron bien." },
  { titulo: "Conecta con tu momento presente", minutos: 10, tipo: "Reflexión", descripcion: "Un ejercicio breve para reconocer cómo te sientes hoy y qué necesitas." },
  { titulo: "Pausa sin pantallas",          minutos: 10, tipo: "Descanso",    descripcion: "Aléjate del celular y la computadora. Mira por la ventana o toma agua." },
  { titulo: "Estiramiento suave",           minutos: 8,  tipo: "Movimiento",  descripcion: "Estira cuello, hombros y espalda con movimientos lentos, sin forzar." },
  { titulo: "Mapa de emociones",            minutos: 10, tipo: "Reflexión",   descripcion: "Anota qué emociones sentiste esta semana y qué las despertó." },
  { titulo: "Prepara tu descanso",          minutos: 5,  tipo: "Hábitos",     descripcion: "Deja listo tu espacio para dormir: luz baja, orden y agua cerca." },
  { titulo: "Lectura tranquila",            minutos: 15, tipo: "Mente",       descripcion: "Lee algo que disfrutes, sin buscar nada más que el gusto de leer." },
  { titulo: "Un gesto amable",              minutos: 10, tipo: "Conexión",    descripcion: "Escríbele o llama a alguien para decirle algo bonito." },
  { titulo: "Mira tu camino",               minutos: 10, tipo: "Reflexión",   descripcion: "Repasa lo que lograste en estos días y elige tu próximo pequeño paso." }
];

/* Intenciones sugeridas (la persona también puede escribir la suya) */
App.INTENCIONES = [
  "Recuperar mi equilibrio en la vida cotidiana.",
  "Dormir mejor y descansar más.",
  "Manejar el estrés con calma.",
  "Crear una rutina de bienestar que pueda sostener."
];

/* Estados de ánimo del registro diario (valor de 1 a 5) */
App.ANIMOS = [
  { valor: 1, emoji: "😞", nombre: "Muy bajo" },
  { valor: 2, emoji: "😕", nombre: "Bajo" },
  { valor: 3, emoji: "😐", nombre: "Regular" },
  { valor: 4, emoji: "🙂", nombre: "Bien" },
  { valor: 5, emoji: "😊", nombre: "Muy bien" }
];

/* Temas disponibles para agendar una sesión de acompañamiento */
App.TEMAS_SESION = ["Orientación sobre mi ruta", "Hábitos de descanso", "Manejo del estrés", "Seguimiento de mi progreso"];

/* Recursos de la sección "Más". tipo "texto" = se lee, "respiracion" = ejercicio guiado */
App.RECURSOS = [
  { id: "respiracion", titulo: "Respiración guiada", resumen: "Un ejercicio de 4-4-4 para calmarte.", tipo: "respiracion" },
  { id: "descanso", titulo: "Ideas para descansar mejor", resumen: "Hábitos sencillos antes de dormir.", tipo: "texto",
    texto: ["Intenta acostarte y levantarte a horas parecidas.", "Baja las luces y las pantallas 30 minutos antes de dormir.", "Prepara tu espacio: ordenado, fresco y en silencio.", "Si te cuesta dormir, prueba la respiración guiada."] },
  { id: "pausas", titulo: "Pausas activas", resumen: "Tres movimientos de un minuto.", tipo: "texto",
    texto: ["Gira lentamente los hombros hacia atrás, diez veces.", "Inclina el cuello hacia cada lado y mantén 10 segundos.", "Ponte de pie, estira los brazos hacia arriba y respira profundo."] },
  { id: "aviso", titulo: "Importante", resumen: "Qué hace y qué no hace HYDISA.", tipo: "texto",
    texto: ["HYDISA es una herramienta de acompañamiento para fortalecer hábitos saludables.", "No emite diagnósticos, tratamientos, prescripciones ni interpretaciones médicas.", "Si algo te preocupa sobre tu salud, consulta a un profesional."] }
];

/* Secciones de la app. "navegacion" = las 5 de la barra inferior */
App.SECCIONES = [
  { id: "inicio",         nombre: "Inicio",         icono: "i-home",     navegacion: true },
  { id: "ruta",           nombre: "Mi ruta",        icono: "i-leaf",     navegacion: true },
  { id: "registro",       nombre: "Registro",       icono: "i-book",     navegacion: true },
  { id: "evolucion",      nombre: "Evolución",      icono: "i-chart",    navegacion: true },
  { id: "perfil",         nombre: "Perfil",         icono: "i-user",     navegacion: true },
  { id: "admin",          nombre: "Administración", icono: "i-shield",   navegacion: false, soloAdmin: true },
  { id: "analisis",       nombre: "Mi análisis",    icono: "i-file",     navegacion: false },
  { id: "calendario",     nombre: "Calendario",     icono: "i-calendar", navegacion: false },
  { id: "acompanamiento", nombre: "Acompañamiento", icono: "i-heart",    navegacion: false },
  { id: "recursos",       nombre: "Recursos",       icono: "i-more",     navegacion: false }
];
