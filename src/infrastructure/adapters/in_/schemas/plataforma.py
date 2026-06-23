"""Contratos HTTP de métricas/actividad agregada de la plataforma (admin/s2s)."""

from pydantic import BaseModel, Field


class ActividadDiariaResponse(BaseModel):
    """Nº de interacciones de un día (serie continua del panel de admin)."""

    day: str = Field(description="Fecha ISO (YYYY-MM-DD)", example="2026-06-15")
    sesiones: int = Field(description="Interacciones registradas ese día", ge=0)


class MetricasPlataformaResponse(BaseModel):
    """Métricas agregadas de toda la plataforma (KPI 'Dominio Plataforma')."""

    dominio_promedio: float | None = Field(
        description="Promedio de puntaje sobre todos los progresos (None si no hay datos)"
    )
    estudiantes_con_progreso: int = Field(
        description="Estudiantes con al menos un progreso académico", ge=0
    )
