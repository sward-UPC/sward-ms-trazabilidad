"""Fixtures de integración para los endpoints de trazabilidad (in-process).

La app se ejerce con httpx.AsyncClient + ASGITransport (sin servidor).
El repositorio Postgres se sustituye por uno en memoria compartido entre los
casos de uso vía dependency_overrides; se conserva la lógica real de los UC
(actualización de progreso, recálculo de riesgo, ordenamiento del dashboard).
"""

from uuid import UUID

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.application.use_cases.calcular_indicadores import CalcularIndicadoresUseCase
from src.application.use_cases.consultar_dashboard_docente import (
    ConsultarDashboardDocenteUseCase,
)
from src.application.use_cases.consultar_progreso import ConsultarProgresoUseCase
from src.application.use_cases.registrar_interaccion import RegistrarInteraccionUseCase
from src.domain.entities.interaccion_academica import InteraccionAcademica
from src.domain.entities.progreso_academico import (
    IndicadorTrazabilidad,
    ProgresoAcademico,
)
from src.domain.ports.out_.trazabilidad_repository_port import (
    TrazabilidadRepositoryPort,
)
from src.infrastructure.adapters.in_.main import app
from src.infrastructure.dependencies import (
    get_calcular_indicadores_uc,
    get_consultar_progreso_uc,
    get_dashboard_docente_uc,
    get_registrar_interaccion_uc,
)


class FakeTrazabilidadRepo(TrazabilidadRepositoryPort):
    def __init__(self):
        self.interacciones: list[InteraccionAcademica] = []
        self.progresos: dict[tuple[UUID, UUID], ProgresoAcademico] = {}

    async def save_interaccion(
        self, interaccion: InteraccionAcademica
    ) -> InteraccionAcademica:
        self.interacciones.append(interaccion)
        return interaccion

    async def find_interacciones(self, estudiante_id, curso_id=None, limit=50):
        items = [i for i in self.interacciones if i.estudiante_id == estudiante_id]
        if curso_id:
            items = [i for i in items if i.curso_id == curso_id]
        return items[:limit]

    async def find_progreso(self, estudiante_id, curso_id):
        return self.progresos.get((estudiante_id, curso_id))

    async def save_progreso(self, progreso: ProgresoAcademico) -> ProgresoAcademico:
        self.progresos[(progreso.estudiante_id, progreso.curso_id)] = progreso
        return progreso

    async def find_all_progreso_curso(self, curso_id):
        return [p for p in self.progresos.values() if p.curso_id == curso_id]

    async def save_indicador(self, indicador: IndicadorTrazabilidad, progreso_id):
        return None


class _StubEventPublisher:
    def publish(self, event) -> None:  # noqa: ARG002
        return None


@pytest_asyncio.fixture
async def client():
    repo = FakeTrazabilidadRepo()
    events = _StubEventPublisher()

    app.dependency_overrides[get_registrar_interaccion_uc] = lambda: (
        RegistrarInteraccionUseCase(repo, events)
    )
    app.dependency_overrides[get_consultar_progreso_uc] = lambda: (
        ConsultarProgresoUseCase(repo)
    )
    app.dependency_overrides[get_calcular_indicadores_uc] = lambda: (
        CalcularIndicadoresUseCase(repo)
    )
    app.dependency_overrides[get_dashboard_docente_uc] = lambda: (
        ConsultarDashboardDocenteUseCase(repo)
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
