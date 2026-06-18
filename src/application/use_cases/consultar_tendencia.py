from collections import defaultdict
from dataclasses import dataclass
from uuid import UUID

from src.domain.ports.out_.trazabilidad_repository_port import (
    TrazabilidadRepositoryPort,
)
from src.domain.value_objects.nivel_riesgo import NivelRiesgo

_RIESGO_ALTO = {NivelRiesgo.ALTO, NivelRiesgo.CRITICO}


@dataclass
class PuntoTendencia:
    """Punto semanal de la tendencia de la clase (datos históricos reales)."""

    week: str
    promedio: float
    riesgo_alto: int


class ConsultarTendenciaUseCase:
    """Agrega el historial de progreso del curso por semana ISO.

    `promedio` = puntaje promedio de los snapshots de la semana.
    `riesgo_alto` = nº de estudiantes distintos en riesgo alto/crítico esa semana.
    """

    def __init__(self, repo: TrazabilidadRepositoryPort):
        self._repo = repo

    async def execute(self, curso_id: UUID) -> list[PuntoTendencia]:
        historial = await self._repo.find_historial_curso(curso_id)
        por_semana: dict[tuple[int, int], list] = defaultdict(list)
        for h in historial:
            year, week, _ = h.registrado_en.isocalendar()
            por_semana[(year, week)].append(h)

        puntos: list[PuntoTendencia] = []
        for year, week in sorted(por_semana):
            items = por_semana[(year, week)]
            promedio = round(sum(i.puntaje_promedio for i in items) / len(items), 1)
            en_riesgo = {
                i.estudiante_id for i in items if i.nivel_riesgo in _RIESGO_ALTO
            }
            puntos.append(
                PuntoTendencia(
                    week=f"{year}-S{week:02d}",
                    promedio=promedio,
                    riesgo_alto=len(en_riesgo),
                )
            )
        return puntos
