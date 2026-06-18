from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from src.application.use_cases.consultar_dashboard_docente import (
    ConsultarDashboardDocenteUseCase,
    EstudianteDashboard,
)
from src.domain.ports.out_.reporte_renderer_port import ReporteRendererPort
from src.domain.value_objects.nivel_riesgo import NivelRiesgo


@dataclass
class ReporteClase:
    """Datos del reporte de progreso de un curso para el docente.

    Incluye el resumen agregado por nivel de riesgo y el detalle por estudiante.
    Es agnóstico al formato de salida (PDF, Excel, etc.).
    """

    curso_id: UUID
    generado_en: datetime
    estudiantes: list[EstudianteDashboard]

    # Resumen agregado (calculado en __post_init__).
    total: int = 0
    criticos: int = 0
    altos: int = 0
    medios: int = 0
    bajos: int = 0
    promedio_dominio: float = 0.0

    def __post_init__(self) -> None:
        self.total = len(self.estudiantes)
        niveles = [e.progreso.nivel_riesgo for e in self.estudiantes]
        self.criticos = niveles.count(NivelRiesgo.CRITICO)
        self.altos = niveles.count(NivelRiesgo.ALTO)
        self.medios = niveles.count(NivelRiesgo.MEDIO)
        self.bajos = niveles.count(NivelRiesgo.BAJO)
        if self.total:
            self.promedio_dominio = round(
                sum(e.progreso.puntaje_promedio for e in self.estudiantes) / self.total,
                1,
            )


class GenerarReporteDocenteUseCase:
    """Genera el reporte de clase (bytes) reutilizando el dashboard docente."""

    def __init__(
        self,
        dashboard_uc: ConsultarDashboardDocenteUseCase,
        renderer: ReporteRendererPort,
    ):
        self._dashboard = dashboard_uc
        self._renderer = renderer

    async def execute(
        self, curso_id: UUID, generado_en: datetime | None = None
    ) -> bytes:
        estudiantes = await self._dashboard.execute(curso_id)
        reporte = ReporteClase(
            curso_id=curso_id,
            generado_en=generado_en or datetime.now(timezone.utc),
            estudiantes=estudiantes,
        )
        return self._renderer.render(reporte)
