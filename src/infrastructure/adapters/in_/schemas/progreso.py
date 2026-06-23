"""Contratos HTTP de progreso/indicadores del estudiante y tendencia de clase."""

from pydantic import BaseModel, ConfigDict, Field


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


class TendenciaResponse(BaseModel):
    """Punto semanal de la tendencia de la clase (histórico real)."""

    week: str = Field(description="Semana ISO", example="2026-S24")
    promedio: float = Field(description="Puntaje promedio de la semana", example=68.5)
    riesgoAlto: int = Field(  # noqa: N815 (contrato camelCase con el frontend)
        description="Estudiantes en riesgo alto/crítico esa semana", example=3
    )
