"""Fixtures de integración para los endpoints de trazabilidad (in-process).

La app se ejerce con httpx.AsyncClient + ASGITransport (sin servidor).
El repositorio Postgres se sustituye por uno en memoria compartido entre los
casos de uso vía dependency_overrides; se conserva la lógica real de los UC
(actualización de progreso, recálculo de riesgo, ordenamiento del dashboard).
"""

from datetime import datetime, timezone
from uuid import UUID

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.application.use_cases.calcular_indicadores import CalcularIndicadoresUseCase
from src.application.use_cases.consultar_dashboard_docente import (
    ConsultarDashboardDocenteUseCase,
)
from src.application.use_cases.consultar_progreso import ConsultarProgresoUseCase
from src.application.use_cases.generar_reporte_docente import (
    GenerarReporteDocenteUseCase,
)
from src.application.use_cases.registrar_feedback import RegistrarFeedbackUseCase
from src.application.use_cases.registrar_interaccion import RegistrarInteraccionUseCase
from src.application.use_cases.registrar_quiz_result import RegistrarQuizResultUseCase
from src.domain.entities.interaccion_academica import InteraccionAcademica
from src.domain.entities.progreso_academico import (
    IndicadorTrazabilidad,
    ProgresoAcademico,
    ProgresoHistorial,
)
from src.domain.ports.out_.trazabilidad_repository_port import (
    TrazabilidadRepositoryPort,
)
from src.domain.ports.out_.usuarios_client_port import UsuariosClientPort
from src.infrastructure.adapters.in_.main import app
from src.infrastructure.adapters.out_.pdf_reporte_renderer import PdfReporteRenderer
from src.infrastructure.dependencies import (
    get_calcular_indicadores_uc,
    get_consultar_progreso_uc,
    get_dashboard_docente_uc,
    get_generar_reporte_docente_uc,
    get_registrar_feedback_uc,
    get_registrar_interaccion_uc,
    get_registrar_quiz_result_uc,
    require_jwt,
)

FAKE_PAYLOAD = {
    "sub": "00000000-0000-0000-0000-000000000001",
    "rol": "docente",
    "permisos": ["leer"],
    "type": "access",
}


class FakeTrazabilidadRepo(TrazabilidadRepositoryPort):
    def __init__(self):
        self.interacciones: list[InteraccionAcademica] = []
        self.progresos: dict[tuple[UUID, UUID], ProgresoAcademico] = {}
        self.feedbacks: list = []
        self.historial: list[ProgresoHistorial] = []

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
        self.historial.append(
            ProgresoHistorial(
                estudiante_id=progreso.estudiante_id,
                curso_id=progreso.curso_id,
                nivel_riesgo=progreso.nivel_riesgo,
                puntaje_promedio=progreso.puntaje_promedio,
                registrado_en=datetime.now(timezone.utc),
            )
        )
        return progreso

    async def find_all_progreso_curso(self, curso_id):
        return [p for p in self.progresos.values() if p.curso_id == curso_id]

    async def save_indicador(self, indicador: IndicadorTrazabilidad, progreso_id):
        return None

    async def save_feedback(self, feedback):
        self.feedbacks.append(feedback)
        return feedback

    async def contar_interacciones_recientes(self, curso_id, desde):
        counts: dict[str, int] = {}
        for i in self.interacciones:
            if i.curso_id == curso_id and i.fecha >= desde:
                counts[str(i.estudiante_id)] = counts.get(str(i.estudiante_id), 0) + 1
        return counts

    async def find_historial_curso(self, curso_id):
        return [h for h in self.historial if h.curso_id == curso_id]

    async def contar_conceptos_en_riesgo(self, curso_id):
        agg: dict[str, dict[str, list[int]]] = {}
        for i in self.interacciones:
            cid = getattr(i, "concept_id", None)
            ic = getattr(i, "is_correct", None)
            if i.curso_id == curso_id and cid and ic is not None:
                a = agg.setdefault(str(i.estudiante_id), {}).setdefault(cid, [0, 0])
                a[1] += 1
                a[0] += 1 if ic else 0
        counts: dict[str, int] = {}
        for est, conceptos in agg.items():
            n = sum(1 for cor, tot in conceptos.values() if tot and cor / tot < 0.5)
            if n:
                counts[est] = n
        return counts

    # --- Métodos analíticos / LMS (no ejercidos por los tests in-memory) -----
    async def upsert_interaccion_lms(self, item):
        raise NotImplementedError

    async def flush_interacciones_lms(self):
        raise NotImplementedError

    async def agregar_metricas_estudiante(self, estudiante_id, curso_id):
        raise NotImplementedError

    async def recomputar_progreso_lms(self, datos):
        raise NotImplementedError

    async def commit_lms_sync(self):
        raise NotImplementedError

    async def calcular_preferencias(self, estudiante_id, curso_id):
        raise NotImplementedError

    async def concepto_mastery(self, estudiante_id, curso_id):
        raise NotImplementedError

    async def actividad_por_dia(self, desde, curso_id):
        raise NotImplementedError

    async def secuencia_estudiante(self, estudiante_id, curso_id):
        raise NotImplementedError

    async def secuencia_curso(self, curso_id):
        raise NotImplementedError

    async def metricas_plataforma(self):
        raise NotImplementedError

    async def training_data(self):
        raise NotImplementedError


class _FakeUsuariosClient(UsuariosClientPort):
    """Simula ms-usuarios: enriquece cualquier UUID con un perfil sintético."""

    async def obtener_perfiles(self, ids: list[UUID]) -> dict[str, dict]:
        return {
            str(i): {
                "nombre": "Est",
                "apellido": "Prueba",
                "correo": f"{i}@upc.edu.pe",
            }
            for i in ids
        }


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
    app.dependency_overrides[get_registrar_quiz_result_uc] = lambda: (
        RegistrarQuizResultUseCase(repo, events)
    )
    app.dependency_overrides[get_consultar_progreso_uc] = lambda: (
        ConsultarProgresoUseCase(repo)
    )
    app.dependency_overrides[get_calcular_indicadores_uc] = lambda: (
        CalcularIndicadoresUseCase(repo)
    )
    app.dependency_overrides[get_dashboard_docente_uc] = lambda: (
        ConsultarDashboardDocenteUseCase(repo, _FakeUsuariosClient())
    )
    app.dependency_overrides[get_generar_reporte_docente_uc] = lambda: (
        GenerarReporteDocenteUseCase(
            ConsultarDashboardDocenteUseCase(repo, _FakeUsuariosClient()),
            PdfReporteRenderer(),
        )
    )
    app.dependency_overrides[get_registrar_feedback_uc] = lambda: (
        RegistrarFeedbackUseCase(repo, events)
    )
    # Sobreescribe la validación JWT por un payload fake (autenticación simulada).
    app.dependency_overrides[require_jwt] = lambda: FAKE_PAYLOAD

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def anon_client():
    """Cliente sin override de auth: los endpoints protegidos exigen token real."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
