from dataclasses import dataclass
from uuid import UUID

from src.domain.ports.out_.trazabilidad_repository_port import (
    TrazabilidadRepositoryPort,
)

_MAX_ETAPAS = 6


@dataclass
class PuntoEvolucion:
    etapa: str
    dominio: float


class ConsultarEvolucionEstudianteUseCase:
    """Evolución del dominio acumulado a lo largo de la secuencia de actividades.

    Se usa la secuencia (no semanas calendario) porque las notas de Moodle no
    traen fecha de envío fiable; así la curva refleja la evolución real.
    """

    def __init__(self, repo: TrazabilidadRepositoryPort):
        self._repo = repo

    async def execute(
        self, estudiante_id: UUID, curso_id: UUID
    ) -> list[PuntoEvolucion]:
        rows = await self._repo.secuencia_estudiante(estudiante_id, curso_id)
        n = len(rows)
        if n == 0:
            return []
        etapas = min(_MAX_ETAPAS, n)
        tam = n / etapas
        acum_total = 0
        acum_nota = 0.0
        out: list[PuntoEvolucion] = []
        for i, row in enumerate(rows, start=1):
            acum_total += 1
            acum_nota += (
                float(row.nota)
                if row.nota is not None
                else (100.0 if row.is_correct else 0.0)
            )
            if i >= round((len(out) + 1) * tam) or i == n:
                out.append(
                    PuntoEvolucion(
                        etapa=f"E{len(out) + 1}",
                        dominio=round(acum_nota / acum_total, 1),
                    )
                )
                if len(out) >= etapas:
                    break
        return out
