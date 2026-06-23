from dataclasses import dataclass
from uuid import UUID

from src.domain.entities.feedback_docente import FeedbackDocente
from src.domain.events.feedback_registrado_event import FeedbackRegistradoEvent
from src.application.ports.out_.event_publisher_port import EventPublisherPort
from src.application.ports.out_.trazabilidad_repository_port import (
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
    def __init__(
        self, repo: TrazabilidadRepositoryPort, event_publisher: EventPublisherPort
    ):
        self._repo = repo
        self._event_publisher = event_publisher

    async def execute(self, command: RegistrarFeedbackCommand) -> FeedbackDocente:
        feedback = FeedbackDocente(
            docente_id=command.docente_id,
            estudiante_id=command.estudiante_id,
            curso_id=command.curso_id,
            mensaje=command.mensaje.strip(),
            tipo=command.tipo,
        )
        guardado = await self._repo.save_feedback(feedback)

        # Notifica al estudiante (lo consume lambda-notificaciones desde EventBridge).
        self._event_publisher.publish(
            FeedbackRegistradoEvent(
                feedback_id=guardado.id,
                docente_id=guardado.docente_id,
                estudiante_id=guardado.estudiante_id,
                curso_id=guardado.curso_id,
                tipo=guardado.tipo,
                mensaje=guardado.mensaje,
            )
        )
        return guardado
