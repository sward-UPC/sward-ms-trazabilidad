from dataclasses import dataclass, field
from uuid import UUID, uuid4

from sward_shared.events.domain_event import DomainEvent


@dataclass
class RiesgoActualizadoEvent(DomainEvent):
    """Se emite cuando el progreso recalculado deja al estudiante en riesgo alto/crítico.

    Permite a lambda-alertas generar la alerta docente sin depender del flujo de
    recomendación. Lleva los mismos campos que consume la lambda.
    """

    estudiante_id: UUID = field(default_factory=uuid4)
    curso_id: UUID = field(default_factory=uuid4)
    nivel_riesgo: str = "alto"
    source: str = "sward-ms-trazabilidad"

    @property
    def event_type(self) -> str:
        return "sward.trazabilidad.RiesgoActualizado"
