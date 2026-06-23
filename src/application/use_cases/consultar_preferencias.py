from uuid import UUID

from src.domain.ports.out_.trazabilidad_repository_port import (
    PreferenciasFormato,
    TrazabilidadRepositoryPort,
)


class ConsultarPreferenciasUseCase:
    """Preferencias de formato del estudiante (rendimiento + engagement).

    Reusado por la ruta JWT (frontend) y la interna (s2s con ms-recomendacion).
    """

    def __init__(self, repo: TrazabilidadRepositoryPort):
        self._repo = repo

    async def execute(self, estudiante_id: UUID, curso_id: UUID) -> PreferenciasFormato:
        return await self._repo.calcular_preferencias(estudiante_id, curso_id)
