from abc import ABC, abstractmethod
from uuid import UUID


class UsuariosClientPort(ABC):
    @abstractmethod
    async def obtener_perfiles(self, ids: list[UUID]) -> dict[str, dict]:
        """Retorna un mapa {str(uuid): {nombre, apellido, correo, ...}}.

        Los IDs sin perfil simplemente no aparecen en el mapa.
        """
        ...
