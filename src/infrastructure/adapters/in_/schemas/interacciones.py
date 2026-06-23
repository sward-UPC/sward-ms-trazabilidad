"""Contratos HTTP del registro de interacciones (interacción, quiz, material)."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.domain.value_objects.nivel_riesgo import TipoInteraccion


class InteraccionRequest(BaseModel):
    """Solicitud para registrar una interacción de estudiante."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "estudiante_id": "550e8400-e29b-41d4-a716-446655440000",
                "curso_id": "550e8400-e29b-41d4-a716-446655440001",
                "tipo": "vista",
                "actividad_id": "550e8400-e29b-41d4-a716-446655440002",
                "recurso_id": None,
                "puntaje": None,
                "moodle_event_id": "12345",
            }
        },
    )

    estudiante_id: UUID = Field(
        description="UUID del estudiante",
        example="550e8400-e29b-41d4-a716-446655440000",
    )
    curso_id: UUID = Field(
        description="UUID del curso", example="550e8400-e29b-41d4-a716-446655440001"
    )
    tipo: TipoInteraccion = Field(
        default=TipoInteraccion.VISTA,
        description="Tipo de interacción realizada",
        example="vista",
    )
    actividad_id: UUID | None = Field(
        default=None,
        description="UUID de la actividad asociada (opcional)",
        example="550e8400-e29b-41d4-a716-446655440002",
    )
    recurso_id: UUID | None = Field(
        default=None,
        description="UUID del recurso asociado (opcional)",
        example=None,
    )
    puntaje: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Puntaje de la interacción (opcional, 0-100)",
        example=None,
    )
    moodle_event_id: str = Field(
        default="",
        max_length=128,
        description="ID del evento en Moodle para trazabilidad",
        example="12345",
    )


class InteraccionResponse(BaseModel):
    """Respuesta que contiene información de una interacción registrada."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440003",
                "tipo": "vista",
                "fecha": "2025-05-31T14:30:00Z",
            }
        },
    )

    id: str = Field(
        description="UUID única de la interacción",
        example="550e8400-e29b-41d4-a716-446655440003",
    )
    tipo: str = Field(description="Tipo de interacción registrada", example="vista")
    fecha: str = Field(
        description="Fecha y hora de la interacción en ISO 8601",
        example="2025-05-31T14:30:00Z",
    )


class QuizResultRequest(BaseModel):
    """Resultado de un quiz/práctica generado por el motor de recomendación.

    El ``estudiante_id`` NO va en el body: se toma del JWT (claim ``sub``).
    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "curso_id": "550e8400-e29b-41d4-a716-446655440001",
                "concepto": "Semana 1-2: Fundamentos de Algoritmos",
                "total_preguntas": 4,
                "correctas": 3,
                "tipo_recurso": "quiz_generado",
            }
        },
    )

    curso_id: UUID = Field(
        description="UUID del curso", example="550e8400-e29b-41d4-a716-446655440001"
    )
    concepto: str = Field(
        min_length=1,
        max_length=255,
        description="Concepto/sección Moodle evaluado",
        example="Semana 1-2: Fundamentos de Algoritmos",
    )
    total_preguntas: int = Field(
        gt=0, le=100, description="Total de preguntas del quiz", example=4
    )
    correctas: int = Field(
        ge=0, le=100, description="Preguntas respondidas correctamente", example=3
    )
    tipo_recurso: str = Field(
        default="quiz_generado",
        max_length=50,
        description="Tipo de recurso (modname Moodle); por defecto quiz_generado",
        example="quiz_generado",
    )

    @model_validator(mode="after")
    def _validar_correctas(self) -> "QuizResultRequest":
        if self.correctas > self.total_preguntas:
            raise ValueError("correctas no puede superar total_preguntas")
        return self


class QuizResultResponse(BaseModel):
    """Confirmación del registro del resultado del quiz."""

    registrado: bool = Field(description="True si se registró la interacción")
    nota: float = Field(description="Nota calculada 0-100", example=75.0)
    is_correct: bool = Field(
        description="True si la nota alcanza el umbral de aprobación", example=True
    )


class MaterialCompletadoRequest(BaseModel):
    """Un recurso generado (práctica/lectura/video) que el estudiante completó.

    El ``estudiante_id`` NO va en el body: se toma del JWT (claim ``sub``).
    """

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "curso_id": "550e8400-e29b-41d4-a716-446655440001",
                "concepto": "Semana 1-2: Fundamentos de Algoritmos",
                "tipo": "practica",
                "aprobado": True,
            }
        },
    )

    curso_id: UUID = Field(description="UUID del curso")
    concepto: str = Field(
        min_length=1, max_length=255, description="Concepto/sección Moodle"
    )
    tipo: str = Field(description="practica | lectura | video")
    aprobado: bool = Field(default=True, description="Solo aplica a práctica")

    @model_validator(mode="after")
    def _validar_tipo(self) -> "MaterialCompletadoRequest":
        if self.tipo not in ("practica", "lectura", "video"):
            raise ValueError("tipo debe ser practica, lectura o video")
        return self


class MaterialCompletadoResponse(BaseModel):
    registrado: bool = Field(description="True si se registró la interacción")
    es_vista: bool = Field(
        description="True si fue una vista (lectura/video); False si calificada"
    )
