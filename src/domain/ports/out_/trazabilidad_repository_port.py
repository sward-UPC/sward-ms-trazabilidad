from abc import ABC, abstractmethod
from uuid import UUID
from datetime import datetime

from src.domain.entities.feedback_docente import FeedbackDocente
from src.domain.entities.interaccion_academica import InteraccionAcademica
from src.domain.entities.progreso_academico import (
    IndicadorTrazabilidad,
    ProgresoAcademico,
    ProgresoHistorial,
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
    @abstractmethod
    async def save_feedback(self, feedback: FeedbackDocente) -> FeedbackDocente: ...
    @abstractmethod
    async def contar_interacciones_recientes(
        self, curso_id: UUID, desde: datetime
    ) -> dict[str, int]:
        """Cuenta interacciones por estudiante (str(uuid)) desde una fecha."""
        ...

    @abstractmethod
    async def find_historial_curso(self, curso_id: UUID) -> list[ProgresoHistorial]: ...
    @abstractmethod
    async def contar_conceptos_en_riesgo(self, curso_id: UUID) -> dict[str, int]:
        """Por estudiante (str(uuid)): nº de conceptos con tasa de acierto < 0.5."""
        ...
