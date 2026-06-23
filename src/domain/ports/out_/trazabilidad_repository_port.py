from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID
from datetime import datetime

from src.domain.entities.feedback_docente import FeedbackDocente
from src.domain.entities.interaccion_academica import InteraccionAcademica
from src.domain.entities.progreso_academico import (
    IndicadorTrazabilidad,
    ProgresoAcademico,
    ProgresoHistorial,
)
from src.domain.value_objects.nivel_riesgo import NivelRiesgo


@dataclass
class InteraccionLms:
    """Interacción del LMS lista para persistir (IDs ya resueltos a UUID)."""

    estudiante_id: UUID
    curso_id: UUID
    actividad_id: UUID
    fecha_evento: datetime
    concepto: str = ""
    es_correcta: bool = False
    nota: float = 0.0
    url_modulo: str = ""
    nombre_actividad: str = ""
    tipo_recurso: str = ""
    es_vista: bool = False
    moodle_event_id: str = ""


@dataclass
class AgregadoEstudiante:
    """Métricas agregadas de un estudiante/curso desde sus interacciones."""

    total: int
    correctas: int
    promedio_nota: float | None
    ultima_actividad: datetime | None


@dataclass
class ProgresoRecomputado:
    """Snapshot de progreso recomputado por la sincronización del LMS."""

    estudiante_id: UUID
    curso_id: UUID
    total_interacciones: int
    recursos_completados: int
    puntaje: float
    nivel_riesgo: NivelRiesgo
    ultima_actividad: datetime | None
    nombre: str = ""
    correo: str = ""


@dataclass
class PreferenciasFormato:
    """Preferencias de formato del estudiante (rendimiento + engagement)."""

    por_tipo: list[dict]
    tipo_fuerte: str
    tipo_debil: str
    engagement_por_tipo: list[dict]
    formato_mas_consumido: str
    recursos_vistos: list[str]


@dataclass
class ConceptoMastery:
    concepto: str
    dominio: float
    total: int
    correctas: int


@dataclass
class ActividadDiaria:
    """Nº de interacciones de un día concreto (clave ISO date)."""

    dia: str
    total: int


@dataclass
class SecuenciaInteraccion:
    """Par (is_correct, nota) de una interacción, ordenada por fecha."""

    is_correct: bool | None
    nota: float | None


@dataclass
class SecuenciaTendencia:
    """Interacción de un curso para la tendencia (incluye estudiante)."""

    estudiante_id: UUID
    is_correct: bool | None
    nota: float | None


@dataclass
class MetricasPlataforma:
    dominio_promedio: float | None
    estudiantes_con_progreso: int


@dataclass
class TrainingRow:
    estudiante_id: UUID
    concepto: str
    correcta: bool
    fecha: datetime
    tipo_recurso: str


class TrazabilidadRepositoryPort(ABC):
    @abstractmethod
    async def save_interaccion(
        self, interaccion: InteraccionAcademica
    ) -> InteraccionAcademica: ...
    @abstractmethod
    async def find_interacciones(
        self, estudiante_id: UUID, curso_id: UUID | None = None, limit: int = 50
    ) -> list[InteraccionAcademica]: ...
    @abstractmethod
    async def find_progreso(
        self, estudiante_id: UUID, curso_id: UUID
    ) -> ProgresoAcademico | None: ...
    @abstractmethod
    async def save_progreso(self, progreso: ProgresoAcademico) -> ProgresoAcademico: ...
    @abstractmethod
    async def find_all_progreso_curso(
        self, curso_id: UUID
    ) -> list[ProgresoAcademico]: ...
    @abstractmethod
    async def save_indicador(
        self, indicador: IndicadorTrazabilidad, progreso_id: UUID
    ) -> None: ...
    @abstractmethod
    async def save_feedback(self, feedback: FeedbackDocente) -> FeedbackDocente: ...
    @abstractmethod
    async def contar_interacciones_recientes(
        self, curso_id: UUID, desde: datetime
    ) -> dict[str, int]:
        """Cuenta interacciones por estudiante (str(uuid)) desde una fecha."""
        ...

    @abstractmethod
    async def find_historial_curso(self, curso_id: UUID) -> list[ProgresoHistorial]: ...
    @abstractmethod
    async def contar_conceptos_en_riesgo(self, curso_id: UUID) -> dict[str, int]:
        """Por estudiante (str(uuid)): nº de conceptos con tasa de acierto < 0.5."""
        ...

    # --- Sincronización LMS -------------------------------------------------
    @abstractmethod
    async def upsert_interaccion_lms(self, item: "InteraccionLms") -> bool:
        """Inserta o actualiza (dedup por ``moodle_event_id``) una interacción.

        Devuelve ``True`` si fue una inserción nueva; ``False`` si actualizó una
        ya existente.
        """
        ...

    @abstractmethod
    async def flush_interacciones_lms(self) -> None:
        """Vuelca las interacciones pendientes sin cerrar la transacción."""
        ...

    @abstractmethod
    async def agregar_metricas_estudiante(
        self, estudiante_id: UUID, curso_id: UUID
    ) -> "AgregadoEstudiante | None":
        """Agrega total/correctas/promedio/última desde todas sus interacciones."""
        ...

    @abstractmethod
    async def recomputar_progreso_lms(self, datos: "ProgresoRecomputado") -> None:
        """Upsert directo del progreso del estudiante (sin snapshot de historial)."""
        ...

    @abstractmethod
    async def commit_lms_sync(self) -> None:
        """Confirma la transacción de la sincronización del LMS."""
        ...

    # --- Lecturas analíticas ------------------------------------------------
    @abstractmethod
    async def calcular_preferencias(
        self, estudiante_id: UUID, curso_id: UUID
    ) -> "PreferenciasFormato":
        """Preferencias de formato (rendimiento por tipo + engagement de vistas)."""
        ...

    @abstractmethod
    async def concepto_mastery(
        self, estudiante_id: UUID, curso_id: UUID
    ) -> "list[ConceptoMastery]":
        """Dominio por concepto/sección (peores primero)."""
        ...

    @abstractmethod
    async def actividad_por_dia(
        self, desde, curso_id: UUID | None
    ) -> "list[ActividadDiaria]":
        """Nº de interacciones por día desde una fecha (opcionalmente por curso)."""
        ...

    @abstractmethod
    async def secuencia_estudiante(
        self, estudiante_id: UUID, curso_id: UUID
    ) -> "list[SecuenciaInteraccion]":
        """Secuencia (is_correct, nota) ordenada por fecha de un estudiante/curso."""
        ...

    @abstractmethod
    async def secuencia_curso(self, curso_id: UUID) -> "list[SecuenciaTendencia]":
        """Secuencia de interacciones del curso ordenada por fecha (con estudiante)."""
        ...

    @abstractmethod
    async def metricas_plataforma(self) -> "MetricasPlataforma":
        """Dominio promedio y nº de estudiantes con progreso en toda la plataforma."""
        ...

    @abstractmethod
    async def training_data(self) -> "list[TrainingRow]":
        """Interacciones calificadas con concepto, ordenadas para entrenar el SAKT."""
        ...
