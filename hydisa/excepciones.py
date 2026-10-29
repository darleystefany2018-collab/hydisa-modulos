"""Errores propios del negocio: así separamos 'error del usuario' de 'error del programa'."""


class HydisaError(Exception):
    """Clase base de todos los errores de HYDISA."""


class DatosInvalidosError(HydisaError):
    """Los datos que ingresó el usuario no cumplen las reglas."""


class CredencialesError(HydisaError):
    """Correo o contraseña incorrectos."""


class ArchivoInvalidoError(HydisaError):
    """El PDF no es válido (RF05, RN-02, RN-04)."""


class PermisoDenegadoError(HydisaError):
    """La cuenta no tiene el rol o el permiso necesario para esta acción."""


class HorarioNoDisponibleError(HydisaError):
    """El horario no existe, ya pasó, se solapa con otro o ya fue reservado."""
