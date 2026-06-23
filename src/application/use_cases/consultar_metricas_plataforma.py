from src.application.ports.out_.trazabilidad_repository_port import (
    MetricasPlataforma,
    TrazabilidadRepositoryPort,
)


class ConsultarMetricasPlataformaUseCase:
    """Métricas agregadas de toda la plataforma (KPI "Dominio Plataforma")."""

    def __init__(self, repo: TrazabilidadRepositoryPort):
        self._repo = repo

    async def execute(self) -> MetricasPlataforma:
        return await self._repo.metricas_plataforma()
