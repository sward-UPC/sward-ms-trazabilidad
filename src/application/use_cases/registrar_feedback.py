from dataclasses import dataclass
from uuid import UUID

from src.domain.entities.feedback_docente import FeedbackDocente
from src.domain.ports.out_.trazabilidad_repository_port import (
    TrazabilidadRepositoryPort,
)


@dataclass
class RegistrarFeedbackCommand:
    docente_id: UUID
    estudiante_id: UUID
    curso_id: UUID
    mensaje: str
    tipo: str = "general"


class RegistrarFeedbackUseCase:
    def __init__(self, repo: TrazabilidadRepositoryPort):
        self._repo = repo

    async def execute(self, command: RegistrarFeedbackCommand) -> FeedbackDocente:
        feedback = FeedbackDocente(
            docente_id=command.docente_id,
            estudiante_id=command.estudiante_id,
            curso_id=command.curso_id,
            mensaje=command.mensaje.strip(),
            tipo=command.tipo,
        )
        return await self._repo.save_feedback(feedback)
