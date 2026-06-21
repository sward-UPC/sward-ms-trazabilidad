from datetime import datetime, timedelta, timezone
from uuid import UUID

from src.domain.ports.out_.trazabilidad_repository_port import (
    TrazabilidadRepositoryPort,
)

# La racha se calcula en hora de Perú (UTC-5, sin horario de verano) para que "hoy"
# coincida con la del estudiante.
PERU_TZ = timezone(timedelta(hours=-5))


class ConsultarRachaUseCase:
    """Racha GLOBAL de días consecutivos con actividad (en todos los cursos).

    A diferencia del resto del panel (por curso), la racha de estudio es global:
    cualquier interacción del alumno cuenta. Solo "vive" si el último día activo es
    hoy o ayer; si es más antiguo, la racha está rota (0).
    """

    def __init__(self, repo: TrazabilidadRepositoryPort):
        self._repo = repo

    async def execute(self, estudiante_id: UUID) -> int:
        # curso_id=None → interacciones de TODOS los cursos del estudiante.
        interacciones = await self._repo.find_interacciones(
            estudiante_id, curso_id=None, limit=1000
        )

        dias: set = set()
        for i in interacciones:
            f = i.fecha
            if f.tzinfo is None:
                f = f.replace(tzinfo=timezone.utc)
            dias.add(f.astimezone(PERU_TZ).date())

        if not dias:
            return 0

        hoy = datetime.now(PERU_TZ).date()
        dias_ord = sorted(dias, reverse=True)
        ultimo = dias_ord[0]

        # Si el último día activo es más viejo que ayer, la racha está rota.
        if (hoy - ultimo).days > 1:
            return 0

        racha = 1
        actual = ultimo
        for d in dias_ord[1:]:
            if (actual - d).days == 1:
                racha += 1
                actual = d
            else:
                break
        return racha
