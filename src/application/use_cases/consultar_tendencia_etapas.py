from collections import defaultdict
from dataclasses import dataclass
from uuid import UUID

from src.domain.ports.out_.trazabilidad_repository_port import (
    TrazabilidadRepositoryPort,
)

_MAX_ETAPAS = 6
# Dominio acumulado por debajo de este valor => estudiante en riesgo alto.
_UMBRAL_RIESGO = 50


@dataclass
class PuntoTendenciaEtapa:
    week: str
    promedio: float
    riesgo_alto: int


class ConsultarTendenciaEtapasUseCase:
    """Tendencia del curso a lo largo de la SECUENCIA de actividades (6 etapas).

    Se usa la secuencia (no semanas calendario) porque las notas de Moodle no
    traen fecha de envío fiable; así la curva refleja datos reales desde la
    primera sincronización.

    NOTA: difiere de ``ConsultarTendenciaUseCase`` (que agrega por semana ISO el
    historial de snapshots). Ambas conviven hasta unificar el contrato con el
    frontend; ver el PR.
    """

    def __init__(self, repo: TrazabilidadRepositoryPort):
        self._repo = repo

    async def execute(self, curso_id: UUID) -> list[PuntoTendenciaEtapa]:
        rows = await self._repo.secuencia_curso(curso_id)
        n = len(rows)
        if n == 0:
            return []

        etapas = min(_MAX_ETAPAS, n)
        tam = n / etapas
        suma_est: dict = defaultdict(float)
        cnt_est: dict = defaultdict(int)
        total_nota = 0.0
        total_cnt = 0
        out: list[PuntoTendenciaEtapa] = []
        for i, row in enumerate(rows, start=1):
            val = (
                float(row.nota)
                if row.nota is not None
                else (100.0 if row.is_correct else 0.0)
            )
            suma_est[row.estudiante_id] += val
            cnt_est[row.estudiante_id] += 1
            total_nota += val
            total_cnt += 1
            if i >= round((len(out) + 1) * tam) or i == n:
                en_riesgo = sum(
                    1 for e in cnt_est if suma_est[e] / cnt_est[e] < _UMBRAL_RIESGO
                )
                out.append(
                    PuntoTendenciaEtapa(
                        week=f"Sem {len(out) + 1}",
                        promedio=round(total_nota / total_cnt, 1),
                        riesgo_alto=en_riesgo,
                    )
                )
                if len(out) >= etapas:
                    break
        return out
