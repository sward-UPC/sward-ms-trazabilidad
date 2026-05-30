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
class ProgresoAcademico:
    id: UUID = field(default_factory=uuid4)
    estudiante_id: UUID = field(default_factory=uuid4)
    curso_id: UUID = field(default_factory=uuid4)
    porcentaje_avance: float = 0.0
    nivel_riesgo: NivelRiesgo = NivelRiesgo.BAJO
    total_interacciones: int = 0
    recursos_completados: int = 0
    puntaje_promedio: float = 0.0
    ultima_actividad: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    indicadores: list[IndicadorTrazabilidad] = field(default_factory=list)

    def actualizar(self, nueva_interaccion: "InteraccionAcademica") -> None:  # noqa: F821
        self.total_interacciones += 1
        self.ultima_actividad = datetime.now(timezone.utc)
        self._recalcular_riesgo()

    def _recalcular_riesgo(self) -> None:
        if self.puntaje_promedio < 40 or self.total_interacciones == 0:
            self.nivel_riesgo = NivelRiesgo.CRITICO
        elif self.puntaje_promedio < 60:
            self.nivel_riesgo = NivelRiesgo.ALTO
        elif self.puntaje_promedio < 75:
            self.nivel_riesgo = NivelRiesgo.MEDIO
        else:
            self.nivel_riesgo = NivelRiesgo.BAJO
