from uuid import UUID

from src.application.ports.out_.trazabilidad_repository_port import (
    ConceptoMastery,
    TrazabilidadRepositoryPort,
)


class ConsultarConceptoMasteryUseCase:
    """Dominio real por concepto/sección del curso para un estudiante.

    Agrupa las interacciones por concepto y calcula la tasa de acierto/dominio,
    ordenadas de peor a mejor. Alimenta el radar y las recomendaciones.
    """

    def __init__(self, repo: TrazabilidadRepositoryPort):
        self._repo = repo

    async def execute(
        self, estudiante_id: UUID, curso_id: UUID
    ) -> list[ConceptoMastery]:
        return await self._repo.concepto_mastery(estudiante_id, curso_id)
