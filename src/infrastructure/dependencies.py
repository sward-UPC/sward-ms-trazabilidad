from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.calcular_indicadores import CalcularIndicadoresUseCase
from src.application.use_cases.consultar_dashboard_docente import (
    ConsultarDashboardDocenteUseCase,
)
from src.application.use_cases.consultar_progreso import ConsultarProgresoUseCase
from src.application.use_cases.registrar_interaccion import RegistrarInteraccionUseCase
from src.infrastructure.adapters.out_.eventbridge_adapter import EventBridgeAdapter
from src.infrastructure.adapters.out_.trazabilidad_postgres_adapter import (
    TrazabilidadPostgresAdapter,
)
from src.infrastructure.db.database import get_session


@lru_cache(maxsize=1)
def get_eventbridge_adapter() -> EventBridgeAdapter:
    return EventBridgeAdapter()


def get_registrar_interaccion_uc(
    session: AsyncSession = Depends(get_session),
    events: EventBridgeAdapter = Depends(get_eventbridge_adapter),
) -> RegistrarInteraccionUseCase:
    return RegistrarInteraccionUseCase(TrazabilidadPostgresAdapter(session), events)


def get_consultar_progreso_uc(
    session: AsyncSession = Depends(get_session),
) -> ConsultarProgresoUseCase:
    return ConsultarProgresoUseCase(TrazabilidadPostgresAdapter(session))


def get_calcular_indicadores_uc(
    session: AsyncSession = Depends(get_session),
) -> CalcularIndicadoresUseCase:
    return CalcularIndicadoresUseCase(TrazabilidadPostgresAdapter(session))


def get_dashboard_docente_uc(
    session: AsyncSession = Depends(get_session),
) -> ConsultarDashboardDocenteUseCase:
    return ConsultarDashboardDocenteUseCase(TrazabilidadPostgresAdapter(session))
