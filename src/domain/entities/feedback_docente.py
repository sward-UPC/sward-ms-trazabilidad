from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass
class FeedbackDocente:
    """Retroalimentación de un docente hacia un estudiante (EP005)."""

    docente_id: UUID
    estudiante_id: UUID
    curso_id: UUID
    mensaje: str
    tipo: str = "general"
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
