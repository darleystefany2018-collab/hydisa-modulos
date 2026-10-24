"""Clases del dominio (POO): representan lo que existe en el negocio."""
from dataclasses import dataclass, field

from .config import CORREO_ADMIN


@dataclass
class Usuario:
    id: int
    nombre: str
    correo: str
    rol: str = "usuario"
    permisos: list = field(default_factory=list)     # claves de config.PERMISOS

    def es_administrador(self):
        """Administrador = rol 'administrador' Y el correo oficial. Se exigen las dos cosas."""
        return self.rol == "administrador" and self.correo == CORREO_ADMIN

    def tiene_permiso(self, permiso):
        """El administrador puede todo; los demás, solo lo que se les asignó."""
        return self.es_administrador() or permiso in self.permisos


@dataclass
class ItemRuta:
    categoria: str
    prioridad: int
    actividad: str
    cumplida: bool = False
