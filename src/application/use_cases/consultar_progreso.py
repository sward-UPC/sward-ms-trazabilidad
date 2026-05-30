from dataclasses import dataclass
from uuid import UUID
from src.domain.entities.progreso_academico import ProgresoAcademico
from src.domain.ports.out_.trazabilidad_repository_port import (
    TrazabilidadRepositoryPort,
)


@dataclass
class ConsultarProgresoCommand:
    estudiante_id: UUID
    curso_id: UUID


class ConsultarProgresoUseCase:
    def __init__(self, repo: TrazabilidadRepositoryPort):
        self._repo = repo

    async def execute(self, cmd: ConsultarProgresoCommand) -> ProgresoAcademico | None:
        return await self._repo.find_progreso(cmd.estudiante_id, cmd.curso_id)
