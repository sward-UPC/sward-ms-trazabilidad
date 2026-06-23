from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4
from src.domain.value_objects.nivel_riesgo import NivelRiesgo


@dataclass
class IndicadorTrazabilidad:
    nombre: str = ""
    valor: float = 0.0
    unidad: str = ""


@dataclass
class ProgresoHistorial:
    """Punto histórico del progreso de un estudiante (para series temporales)."""

    estudiante_id: UUID
    curso_id: UUID
    nivel_riesgo: NivelRiesgo
    puntaje_promedio: float
    registrado_en: datetime


@dataclass
class ProgresoAcademico:
    id: UUID = field(default_factory=uuid4)
    estudiante_id: UUID = field(default_factory=uuid4)
    curso_id: UUID = field(default_factory=uuid4)
    porcentaje_avance: float = 0.0
    nivel_riesgo: NivelRiesgo = NivelRiesgo.BAJO
    total_interacciones: int = 0
    recursos_completados: int = 0
    puntaje_promedio: float = 0.0
    # Nombre/correo del estudiante en Moodle (fallback si no está en SWARD).
    nombre: str = ""
    correo: str = ""
    ultima_actividad: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    indicadores: list[IndicadorTrazabilidad] = field(default_factory=list)

    def actualizar(self, nueva_interaccion: "InteraccionAcademica") -> None:  # noqa: F821
        self.total_interacciones += 1
        self.ultima_actividad = datetime.now(timezone.utc)
        self._recalcular_riesgo()

    def _recalcular_riesgo(self) -> None:
        self.nivel_riesgo = NivelRiesgo.por_puntaje(
            self.puntaje_promedio, self.total_interacciones
        )
