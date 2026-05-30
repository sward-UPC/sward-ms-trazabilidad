from dataclasses import dataclass
from uuid import UUID
from src.domain.entities.progreso_academico import IndicadorTrazabilidad
from src.domain.ports.out_.trazabilidad_repository_port import (
    TrazabilidadRepositoryPort,
)


@dataclass
class CalcularIndicadoresCommand:
    estudiante_id: UUID
    curso_id: UUID


class CalcularIndicadoresUseCase:
    def __init__(self, repo: TrazabilidadRepositoryPort):
        self._repo = repo

    async def execute(
        self, cmd: CalcularIndicadoresCommand
    ) -> list[IndicadorTrazabilidad]:
        progreso = await self._repo.find_progreso(cmd.estudiante_id, cmd.curso_id)
        if not progreso:
            return []
        indicadores = [
            IndicadorTrazabilidad(
                nombre="total_interacciones",
                valor=progreso.total_interacciones,
                unidad="count",
            ),
            IndicadorTrazabilidad(
                nombre="puntaje_promedio",
                valor=progreso.puntaje_promedio,
                unidad="puntos",
            ),
            IndicadorTrazabilidad(
                nombre="recursos_completados",
                valor=progreso.recursos_completados,
                unidad="count",
            ),
            IndicadorTrazabilidad(
                nombre="porcentaje_avance", valor=progreso.porcentaje_avance, unidad="%"
            ),
        ]
        for ind in indicadores:
            await self._repo.save_indicador(ind, progreso.id)
        return indicadores
