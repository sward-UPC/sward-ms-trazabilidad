"""Contratos HTTP del endpoint interno de sincronización LMS (Moodle → SWARD)."""

from datetime import datetime

from pydantic import BaseModel, Field


class LmsInteraccionItem(BaseModel):
    moodle_user_id: str
    moodle_course_id: str
    moodle_activity_id: str
    nombre: str = ""
    correo: str = ""
    concepto: str = ""
    es_correcta: bool = False
    nota: float = 0.0
    url_modulo: str = ""
    nombre_actividad: str = ""
    tipo_recurso: str = ""
    es_vista: bool = False
    fecha_evento: datetime
    moodle_event_id: str = ""


class LmsSyncRequest(BaseModel):
    interacciones: list[LmsInteraccionItem]


class LmsSyncResponse(BaseModel):
    """Resultado de la sincronización LMS (idempotente)."""

    procesadas: int = Field(description="Interacciones nuevas persistidas", ge=0)
    omitidas: int = Field(
        description="Interacciones omitidas por deduplicación (ya existían)", ge=0
    )


class TrainingRowResponse(BaseModel):
    """Fila del dataset de entrenamiento SAKT (knowledge tracing)."""

    estudiante_id: str = Field(description="UUID del estudiante")
    concepto: str = Field(description="Concepto/sección de Moodle (skill)")
    correcta: bool = Field(description="True si la interacción fue correcta")
    orden: str = Field(description="Marca temporal ISO para ordenar la secuencia")
    tipo_recurso: str = Field(
        description="Tipo de recurso (habilita el SAKT format-aware)"
    )
