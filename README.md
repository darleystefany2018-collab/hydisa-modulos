# HYDISA – Módulos de software

Proyecto de la Actividad 1 (Programación de módulos de software) del
Tecnólogo en Análisis y Desarrollo de Software – SENA, ficha 3316209.

HYDISA procesa reportes PDF del dispositivo Healy y genera una ruta
personalizada de bienestar. **No emite diagnósticos médicos.**

## Módulos
- `hydisa/servicio_usuarios.py`: registro e inicio de sesión (RF01, RF02)
- `hydisa/servicio_pdf.py`: validar y leer PDF (RF04–RF06)
- `hydisa/motor_reglas.py`: clasifica palabras clave y genera la ruta
- `hydisa/servicio_reportes.py`: historial, progreso y exportar PDF (RF16)
- `hydisa/base_datos.py`: acceso a la base de datos (SQLite)

## Cómo ejecutarlo
```
py -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
py main.py
```
## Base de datos

Por defecto usa SQLite local. Para usar PostgreSQL en la nube (Supabase),
crea un archivo `.env` en la carpeta principal con una línea:

```
DATABASE_URL=postgresql://usuario:contraseña@servidor:5432/postgres
```

El archivo `.env` **no se sube a GitHub** porque contiene la contraseña.

## Pruebas
```
py -m unittest discover -s tests -v
```

## Integrantes
Darley Sthefany Guevara  Herrera, Dennis Yeraldin Pamplona Mahecha,
Iván Camilo Ochoa, Diego Andrés Ramos Jimenez