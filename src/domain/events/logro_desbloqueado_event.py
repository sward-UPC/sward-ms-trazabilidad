from dataclasses import dataclass, field
from uuid import UUID, uuid4

from sward_shared.events.domain_event import DomainEvent


@dataclass
class LogroDesbloqueadoEvent(DomainEvent):
    """El alumno alcanzó un hito (racha de días o recursos completados).
    Lo consume lambda-notificaciones para felicitar al estudiante.

    `event_id` se setea determinístico (uuid5) al construirlo para que el hito
    notifique UNA sola vez (idempotencia en la lambda)."""

    estudiante_id: UUID = field(default_factory=uuid4)
    tipo: str = "racha"  # racha | recursos
    valor: int = 0
    source: str = "sward-ms-trazabilidad"

    @property
    def event_type(self) -> str:
        return "sward.trazabilidad.LogroDesbloqueado"
