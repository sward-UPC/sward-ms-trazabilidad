"""Contratos Pydantic (Request/Response) del adaptador de entrada HTTP.

Separados de las rutas para cumplir la convención hexagonal de inbound
adapters: los handlers quedan delgados y los contratos viven aquí.
"""

from datetime import datetime
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


class ProgresoResponse(BaseModel):
    """Respuesta que contiene información del progreso de un estudiante."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440004",
                "porcentaje_avance": 65.5,
                "nivel_riesgo": "bajo",
                "total_interacciones": 45,
                "puntaje_promedio": 78.5,
            }
        },
    )

    id: str = Field(
        description="UUID del registro de progreso",
        example="550e8400-e29b-41d4-a716-446655440004",
    )
    porcentaje_avance: float = Field(
        description="Porcentaje de avance en el curso", ge=0, le=100, example=65.5
    )
    nivel_riesgo: str = Field(
        description="Nivel de riesgo académico (bajo, medio, alto, critico)",
        example="bajo",
    )
    total_interacciones: int = Field(
        description="Cantidad total de interacciones", ge=0, example=45
    )
    puntaje_promedio: float = Field(
        description="Puntaje promedio en actividades", ge=0, le=100, example=78.5
    )


class IndicadorResponse(BaseModel):
    """Respuesta que contiene un indicador de desempeño."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "nombre": "Participación",
                "valor": 85.0,
                "unidad": "porcentaje",
            }
        },
    )

    nombre: str = Field(
        description="Nombre del indicador", max_length=100, example="Participación"
    )
    valor: float = Field(description="Valor del indicador", example=85.0)
    unidad: str = Field(
        description="Unidad de medida del indicador",
        max_length=50,
        example="porcentaje",
    )


class EstudianteProgressResponse(BaseModel):
    """Respuesta que contiene el progreso de un estudiante en el dashboard docente."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "estudiante_id": "550e8400-e29b-41d4-a716-446655440000",
                "nombre": "Ana",
                "apellido": "Quispe",
                "correo": "ana.quispe@upc.edu.pe",
                "nivel_riesgo": "medio",
                "puntaje_promedio": 72.0,
                "total_interacciones": 38,
                "recursos_completados": 12,
            }
        },
    )

    estudiante_id: str = Field(
        description="UUID del estudiante",
        example="550e8400-e29b-41d4-a716-446655440000",
    )
    nombre: str = Field(default="", description="Nombre del estudiante", example="Ana")
    apellido: str = Field(
        default="", description="Apellido del estudiante", example="Quispe"
    )
    correo: str = Field(
        default="",
        description="Correo institucional del estudiante",
        example="ana.quispe@upc.edu.pe",
    )
    nivel_riesgo: str = Field(description="Nivel de riesgo académico", example="medio")
    puntaje_promedio: float = Field(
        description="Puntaje promedio del estudiante", ge=0, le=100, example=72.0
    )
    total_interacciones: int = Field(
        description="Cantidad total de interacciones", ge=0, example=38
    )
    recursos_completados: int = Field(
        description="Cantidad de recursos completados", ge=0, example=12
    )
    engagement: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Índice de engagement (actividad de los últimos 30 días)",
        example=60,
    )
    conceptos_en_riesgo: int = Field(
        default=0,
        ge=0,
        description="Nº de conceptos (secciones) con tasa de acierto < 0.5",
        example=2,
    )
    registrado_en_sward: bool = Field(
        default=False,
        description="True si el estudiante tiene cuenta en SWARD; False si solo está en Moodle",
        example=True,
    )
    ultima_actividad: str = Field(
        default="",
        description="Fecha/hora de la última actividad (ISO 8601)",
        example="2026-06-18T12:00:00Z",
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


# ---------------------------------------------------------------------------
# Schemas para el endpoint interno de sincronización LMS
# ---------------------------------------------------------------------------


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


class TendenciaResponse(BaseModel):
    """Punto semanal de la tendencia de la clase (histórico real)."""

    week: str = Field(description="Semana ISO", example="2026-S24")
    promedio: float = Field(description="Puntaje promedio de la semana", example=68.5)
    riesgoAlto: int = Field(  # noqa: N815 (contrato camelCase con el frontend)
        description="Estudiantes en riesgo alto/crítico esa semana", example=3
    )


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
