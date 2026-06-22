from dataclasses import dataclass, field
from uuid import UUID, uuid4

from sward_shared.events.domain_event import DomainEvent


@dataclass
class FeedbackRegistradoEvent(DomainEvent):
    """El docente envió retroalimentación a un estudiante. Lo consume
    lambda-notificaciones para crear la notificación del estudiante."""

    feedback_id: UUID = field(default_factory=uuid4)
    docente_id: UUID = field(default_factory=uuid4)
    estudiante_id: UUID = field(default_factory=uuid4)
    curso_id: UUID = field(default_factory=uuid4)
    tipo: str = "general"
    mensaje: str = ""
    source: str = "sward-ms-trazabilidad"

    @property
    def event_type(self) -> str:
        return "sward.trazabilidad.FeedbackRegistrado"
