"""Clases del dominio (POO): representan lo que existe en el negocio."""
from dataclasses import dataclass


@dataclass
class Usuario:
    id: int
    nombre: str
    correo: str
    rol: str = "usuario"

    def es_administrador(self):
        return self.rol == "administrador"


@dataclass
class ItemRuta:
    categoria: str
    prioridad: int
    actividad: str
    cumplida: bool = False