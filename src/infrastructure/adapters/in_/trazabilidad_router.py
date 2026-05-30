from uuid import UUID
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from src.application.use_cases.calcular_indicadores import (
    CalcularIndicadoresCommand,
    CalcularIndicadoresUseCase,
)
from src.application.use_cases.consultar_dashboard_docente import (
    ConsultarDashboardDocenteUseCase,
)
from src.application.use_cases.consultar_progreso import (
    ConsultarProgresoCommand,
    ConsultarProgresoUseCase,
)
from src.application.use_cases.registrar_interaccion import (
    RegistrarInteraccionCommand,
    RegistrarInteraccionUseCase,
)
from src.domain.value_objects.nivel_riesgo import TipoInteraccion
from src.infrastructure.adapters.out_.eventbridge_adapter import EventBridgeAdapter
from src.infrastructure.adapters.out_.trazabilidad_postgres_adapter import (
    TrazabilidadPostgresAdapter,
)
from src.infrastructure.db.database import get_session

router = APIRouter(tags=["Trazabilidad"])


class InteraccionRequest(BaseModel):
    estudiante_id: UUID
    curso_id: UUID
    tipo: TipoInteraccion = TipoInteraccion.VISTA
    actividad_id: UUID | None = None
    recurso_id: UUID | None = None
    puntaje: float | None = None
    moodle_event_id: str = ""


@router.post("/interactions", status_code=201)
async def registrar_interaccion(
    body: InteraccionRequest, session: AsyncSession = Depends(get_session)
):
    uc = RegistrarInteraccionUseCase(
        TrazabilidadPostgresAdapter(session), EventBridgeAdapter()
    )
    i = await uc.execute(RegistrarInteraccionCommand(**body.model_dump()))
    return {"id": str(i.id), "tipo": i.tipo, "fecha": i.fecha.isoformat()}


@router.get("/students/{student_id}/progress")
async def get_progress(
    student_id: UUID, courseId: UUID, session: AsyncSession = Depends(get_session)
):
    uc = ConsultarProgresoUseCase(TrazabilidadPostgresAdapter(session))
    p = await uc.execute(
        ConsultarProgresoCommand(estudiante_id=student_id, curso_id=courseId)
    )
    if not p:
        return {
            "estudiante_id": str(student_id),
            "curso_id": str(courseId),
            "sin_actividad": True,
        }
    return {
        "id": str(p.id),
        "porcentaje_avance": p.porcentaje_avance,
        "nivel_riesgo": p.nivel_riesgo,
        "total_interacciones": p.total_interacciones,
        "puntaje_promedio": p.puntaje_promedio,
    }


@router.get("/students/{student_id}/indicators")
async def get_indicators(
    student_id: UUID, courseId: UUID, session: AsyncSession = Depends(get_session)
):
    uc = CalcularIndicadoresUseCase(TrazabilidadPostgresAdapter(session))
    indicadores = await uc.execute(
        CalcularIndicadoresCommand(estudiante_id=student_id, curso_id=courseId)
    )
    return [
        {"nombre": i.nombre, "valor": i.valor, "unidad": i.unidad} for i in indicadores
    ]


@router.get("/students/{student_id}/interactions")
async def get_interactions(
    student_id: UUID,
    courseId: UUID | None = None,
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
):
    repo = TrazabilidadPostgresAdapter(session)
    items = await repo.find_interacciones(student_id, courseId, limit)
    return [
        {
            "id": str(i.id),
            "tipo": i.tipo,
            "fecha": i.fecha.isoformat(),
            "curso_id": str(i.curso_id),
        }
        for i in items
    ]


@router.get("/dashboard/teacher/{course_id}/students-progress")
async def dashboard_docente(
    course_id: UUID, session: AsyncSession = Depends(get_session)
):
    uc = ConsultarDashboardDocenteUseCase(TrazabilidadPostgresAdapter(session))
    progresos = await uc.execute(course_id)
    return [
        {
            "estudiante_id": str(p.estudiante_id),
            "nivel_riesgo": p.nivel_riesgo,
            "puntaje_promedio": p.puntaje_promedio,
            "total_interacciones": p.total_interacciones,
            "recursos_completados": p.recursos_completados,
        }
        for p in progresos
    ]
