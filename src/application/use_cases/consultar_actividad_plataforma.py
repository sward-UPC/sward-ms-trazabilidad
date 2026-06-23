from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from src.domain.ports.out_.trazabilidad_repository_port import (
    TrazabilidadRepositoryPort,
)

_DIAS_ES = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


@dataclass
class PuntoActividad:
    day: str
    sesiones: int


class ConsultarActividadPlataformaUseCase:
    """Actividad real de la plataforma: nº de interacciones por día (N días).

    Los días sin actividad se devuelven en cero (serie continua).
    """

    def __init__(self, repo: TrazabilidadRepositoryPort):
        self._repo = repo

    async def execute(self, days: int, curso_id: UUID | None) -> list[PuntoActividad]:
        hoy = datetime.now(timezone.utc).date()
        desde = hoy - timedelta(days=days - 1)
        actividad = await self._repo.actividad_por_dia(desde, curso_id)
        counts = {a.dia: a.total for a in actividad}

        out: list[PuntoActividad] = []
        for i in range(days):
            d = desde + timedelta(days=i)
            out.append(
                PuntoActividad(
                    day=f"{_DIAS_ES[d.weekday()]} {d.day:02d}",
                    sesiones=counts.get(str(d), 0),
                )
            )
        return out
