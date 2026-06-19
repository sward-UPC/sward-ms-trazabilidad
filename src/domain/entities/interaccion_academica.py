from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4
from src.domain.value_objects.nivel_riesgo import TipoInteraccion


@dataclass
class RespuestaActividad:
    id: UUID = field(default_factory=uuid4)
    pregunta_id: str = ""
    respuesta: str = ""
    correcta: bool = False
    puntaje: float = 0.0


@dataclass
class InteraccionAcademica:
    id: UUID = field(default_factory=uuid4)
    estudiante_id: UUID = field(default_factory=uuid4)
    curso_id: UUID = field(default_factory=uuid4)
    actividad_id: UUID | None = None
    recurso_id: UUID | None = None
    tipo: TipoInteraccion = TipoInteraccion.VISTA
    fecha: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    respuestas: list[RespuestaActividad] = field(default_factory=list)
    moodle_event_id: str = ""
    # Concepto/skill (sección Moodle) y corrección, para secuencias SAKT.
    concept_id: str | None = None
    is_correct: bool | None = None
    # Enlace directo al módulo en Moodle.
    url_modulo: str = ""
