"""Contratos HTTP de la retroalimentación docente → estudiante."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FeedbackRequest(BaseModel):
    """Retroalimentación del docente hacia un estudiante."""

    model_config = ConfigDict(extra="forbid")

    estudiante_id: UUID = Field(description="UUID del estudiante destinatario")
    curso_id: UUID = Field(description="UUID del curso")
    mensaje: str = Field(
        min_length=1, max_length=1000, description="Mensaje de retroalimentación"
    )
    tipo: str = Field(
        default="general",
        pattern="^(encouragement|correction|resource|general)$",
        description="Tipo de retroalimentación",
    )


class FeedbackResponse(BaseModel):
    id: str
    estudiante_id: str
    tipo: str
    created_at: datetime
