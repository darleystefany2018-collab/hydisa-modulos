"""Errores propios del negocio: así separamos 'error del usuario' de 'error del programa'."""


class HydisaError(Exception):
    """Clase base de todos los errores de HYDISA."""


class DatosInvalidosError(HydisaError):
    """Los datos que ingresó el usuario no cumplen las reglas."""


class CredencialesError(HydisaError):
    """Correo o contraseña incorrectos."""


class ArchivoInvalidoError(HydisaError):
    """El PDF no es válido (RF05, RN-02, RN-04)."""