from uuid import UUID
from src.domain.entities.progreso_academico import ProgresoAcademico
from src.domain.ports.out_.trazabilidad_repository_port import (
    TrazabilidadRepositoryPort,
)
from src.domain.value_objects.nivel_riesgo import NivelRiesgo


class ConsultarDashboardDocenteUseCase:
    def __init__(self, repo: TrazabilidadRepositoryPort):
        self._repo = repo

    async def execute(self, curso_id: UUID) -> list[ProgresoAcademico]:
        progresos = await self._repo.find_all_progreso_curso(curso_id)
        # Ordenar por nivel de riesgo descendente (crítico primero)
        orden = {
            NivelRiesgo.CRITICO: 0,
            NivelRiesgo.ALTO: 1,
            NivelRiesgo.MEDIO: 2,
            NivelRiesgo.BAJO: 3,
        }
        return sorted(progresos, key=lambda p: orden.get(p.nivel_riesgo, 4))
