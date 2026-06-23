from abc import ABC, abstractmethod


class LmsClientPort(ABC):
    @abstractmethod
    async def obtener_interacciones(
        self, curso_id: str | None = None, user_id: str | None = None
    ) -> list[dict]: ...
    @abstractmethod
    async def obtener_calificaciones(
        self, curso_id: str | None = None, user_id: str | None = None
    ) -> list[dict]: ...
