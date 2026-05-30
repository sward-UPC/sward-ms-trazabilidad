from abc import ABC, abstractmethod
from uuid import UUID
from src.domain.entities.interaccion_academica import InteraccionAcademica
from src.domain.entities.progreso_academico import (
    IndicadorTrazabilidad,
    ProgresoAcademico,
)


class TrazabilidadRepositoryPort(ABC):
    @abstractmethod
    async def save_interaccion(
        self, interaccion: InteraccionAcademica
    ) -> InteraccionAcademica: ...
    @abstractmethod
    async def find_interacciones(
        self, estudiante_id: UUID, curso_id: UUID | None = None, limit: int = 50
    ) -> list[InteraccionAcademica]: ...
    @abstractmethod
    async def find_progreso(
        self, estudiante_id: UUID, curso_id: UUID
    ) -> ProgresoAcademico | None: ...
    @abstractmethod
    async def save_progreso(self, progreso: ProgresoAcademico) -> ProgresoAcademico: ...
    @abstractmethod
    async def find_all_progreso_curso(
        self, curso_id: UUID
    ) -> list[ProgresoAcademico]: ...
    @abstractmethod
    async def save_indicador(
        self, indicador: IndicadorTrazabilidad, progreso_id: UUID
    ) -> None: ...
