from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.domain.entities.feedback_docente import FeedbackDocente
from src.domain.entities.interaccion_academica import InteraccionAcademica
from src.domain.entities.progreso_academico import (
    IndicadorTrazabilidad,
    ProgresoAcademico,
)
from src.domain.ports.out_.trazabilidad_repository_port import (
    TrazabilidadRepositoryPort,
)
from src.domain.value_objects.nivel_riesgo import NivelRiesgo, TipoInteraccion
from src.infrastructure.db.models.trazabilidad_models import (
    FeedbackModel,
    IndicadorModel,
    InteraccionModel,
    ProgresoModel,
)


class TrazabilidadPostgresAdapter(TrazabilidadRepositoryPort):
    def __init__(self, session: AsyncSession):
        self._s = session

    async def save_interaccion(self, i: InteraccionAcademica) -> InteraccionAcademica:
        m = InteraccionModel(
            id=i.id,
            estudiante_id=i.estudiante_id,
            curso_id=i.curso_id,
            actividad_id=i.actividad_id,
            recurso_id=i.recurso_id,
            tipo=i.tipo.value,
            fecha=i.fecha,
            moodle_event_id=i.moodle_event_id,
        )
        self._s.add(m)
        await self._s.flush()
        return i

    async def find_interacciones(
        self, estudiante_id: UUID, curso_id: UUID | None = None, limit: int = 50
    ) -> list[InteraccionAcademica]:
        q = select(InteraccionModel).where(
            InteraccionModel.estudiante_id == estudiante_id
        )
        if curso_id:
            q = q.where(InteraccionModel.curso_id == curso_id)
        q = q.order_by(InteraccionModel.fecha.desc()).limit(limit)
        r = await self._s.execute(q)
        return [
            InteraccionAcademica(
                id=m.id,
                estudiante_id=m.estudiante_id,
                curso_id=m.curso_id,
                actividad_id=m.actividad_id,
                recurso_id=m.recurso_id,
                tipo=TipoInteraccion(m.tipo),
                fecha=m.fecha,
            )
            for m in r.scalars().all()
        ]

    async def find_progreso(
        self, estudiante_id: UUID, curso_id: UUID
    ) -> ProgresoAcademico | None:
        r = await self._s.execute(
            select(ProgresoModel).where(
                ProgresoModel.estudiante_id == estudiante_id,
                ProgresoModel.curso_id == curso_id,
            )
        )
        m = r.scalar_one_or_none()
        return _progreso_to_entity(m) if m else None

    async def save_progreso(self, p: ProgresoAcademico) -> ProgresoAcademico:
        r = await self._s.execute(select(ProgresoModel).where(ProgresoModel.id == p.id))
        m = r.scalar_one_or_none()
        if m:
            m.porcentaje_avance = p.porcentaje_avance
            m.nivel_riesgo = p.nivel_riesgo.value
            m.total_interacciones = p.total_interacciones
            m.recursos_completados = p.recursos_completados
            m.puntaje_promedio = p.puntaje_promedio
            m.ultima_actividad = p.ultima_actividad
        else:
            m = ProgresoModel(
                id=p.id,
                estudiante_id=p.estudiante_id,
                curso_id=p.curso_id,
                porcentaje_avance=p.porcentaje_avance,
                nivel_riesgo=p.nivel_riesgo.value,
                total_interacciones=p.total_interacciones,
                recursos_completados=p.recursos_completados,
                puntaje_promedio=p.puntaje_promedio,
                ultima_actividad=p.ultima_actividad,
            )
            self._s.add(m)
        await self._s.flush()
        return p

    async def find_all_progreso_curso(self, curso_id: UUID) -> list[ProgresoAcademico]:
        r = await self._s.execute(
            select(ProgresoModel).where(ProgresoModel.curso_id == curso_id)
        )
        return [_progreso_to_entity(m) for m in r.scalars().all()]

    async def save_indicador(
        self, indicador: IndicadorTrazabilidad, progreso_id: UUID
    ) -> None:
        self._s.add(
            IndicadorModel(
                progreso_id=progreso_id,
                nombre=indicador.nombre,
                valor=indicador.valor,
                unidad=indicador.unidad,
            )
        )
        await self._s.flush()

    async def save_feedback(self, f: FeedbackDocente) -> FeedbackDocente:
        self._s.add(
            FeedbackModel(
                id=f.id,
                docente_id=f.docente_id,
                estudiante_id=f.estudiante_id,
                curso_id=f.curso_id,
                mensaje=f.mensaje,
                tipo=f.tipo,
                created_at=f.created_at,
            )
        )
        await self._s.flush()
        return f


def _progreso_to_entity(m: ProgresoModel) -> ProgresoAcademico:
    return ProgresoAcademico(
        id=m.id,
        estudiante_id=m.estudiante_id,
        curso_id=m.curso_id,
        porcentaje_avance=m.porcentaje_avance,
        nivel_riesgo=NivelRiesgo(m.nivel_riesgo),
        total_interacciones=m.total_interacciones,
        recursos_completados=m.recursos_completados,
        puntaje_promedio=m.puntaje_promedio,
        ultima_actividad=m.ultima_actividad,
    )
