from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sward_shared.auth import build_require_jwt, build_require_service_key

from src.application.use_cases.calcular_indicadores import CalcularIndicadoresUseCase
from src.application.use_cases.consultar_dashboard_docente import (
    ConsultarDashboardDocenteUseCase,
)
from src.application.use_cases.consultar_progreso import ConsultarProgresoUseCase
from src.application.use_cases.consultar_tendencia import ConsultarTendenciaUseCase
from src.application.use_cases.generar_reporte_docente import (
    GenerarReporteDocenteUseCase,
)
from src.application.use_cases.registrar_feedback import RegistrarFeedbackUseCase
from src.application.use_cases.registrar_interaccion import RegistrarInteraccionUseCase
from src.application.use_cases.registrar_quiz_result import RegistrarQuizResultUseCase
from src.infrastructure.adapters.out_.eventbridge_adapter import EventBridgeAdapter
from src.infrastructure.adapters.out_.pdf_reporte_renderer import PdfReporteRenderer
from src.infrastructure.adapters.out_.trazabilidad_postgres_adapter import (
    TrazabilidadPostgresAdapter,
)
from src.infrastructure.adapters.out_.usuarios_rest_adapter import UsuariosRestAdapter
from src.infrastructure.config.settings import settings
from src.infrastructure.db.database import get_session

# Dependencia de autenticación JWT reutilizable, compartida vía sward-shared.
require_jwt = build_require_jwt(settings.secret_key, algorithm=settings.jwt_algorithm)

# Validación entrante de service-key (modo dev permite sin claves configuradas).
require_service_key = build_require_service_key(settings.authorized_service_keys_set)


@lru_cache(maxsize=1)
def get_eventbridge_adapter() -> EventBridgeAdapter:
    return EventBridgeAdapter()


def get_registrar_interaccion_uc(
    session: AsyncSession = Depends(get_session),
    events: EventBridgeAdapter = Depends(get_eventbridge_adapter),
) -> RegistrarInteraccionUseCase:
    return RegistrarInteraccionUseCase(TrazabilidadPostgresAdapter(session), events)


def get_registrar_quiz_result_uc(
    session: AsyncSession = Depends(get_session),
    events: EventBridgeAdapter = Depends(get_eventbridge_adapter),
) -> RegistrarQuizResultUseCase:
    return RegistrarQuizResultUseCase(TrazabilidadPostgresAdapter(session), events)


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
    return ConsultarDashboardDocenteUseCase(
        TrazabilidadPostgresAdapter(session), UsuariosRestAdapter()
    )


def get_generar_reporte_docente_uc(
    session: AsyncSession = Depends(get_session),
) -> GenerarReporteDocenteUseCase:
    dashboard_uc = ConsultarDashboardDocenteUseCase(
        TrazabilidadPostgresAdapter(session), UsuariosRestAdapter()
    )
    return GenerarReporteDocenteUseCase(dashboard_uc, PdfReporteRenderer())


def get_registrar_feedback_uc(
    session: AsyncSession = Depends(get_session),
) -> RegistrarFeedbackUseCase:
    return RegistrarFeedbackUseCase(TrazabilidadPostgresAdapter(session))


def get_consultar_tendencia_uc(
    session: AsyncSession = Depends(get_session),
) -> ConsultarTendenciaUseCase:
    return ConsultarTendenciaUseCase(TrazabilidadPostgresAdapter(session))


def get_trazabilidad_repo(
    session: AsyncSession = Depends(get_session),
) -> TrazabilidadPostgresAdapter:
    return TrazabilidadPostgresAdapter(session)
