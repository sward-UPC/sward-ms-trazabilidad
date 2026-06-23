from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.domain.entities.feedback_docente import FeedbackDocente
from src.domain.entities.interaccion_academica import InteraccionAcademica
from src.domain.entities.progreso_academico import (
    IndicadorTrazabilidad,
    ProgresoAcademico,
    ProgresoHistorial,
)
from src.domain.ports.out_.trazabilidad_repository_port import (
    ActividadDiaria,
    AgregadoEstudiante,
    ConceptoMastery,
    InteraccionLms,
    MetricasPlataforma,
    PreferenciasFormato,
    ProgresoRecomputado,
    SecuenciaInteraccion,
    SecuenciaTendencia,
    TrainingRow,
    TrazabilidadRepositoryPort,
)
from src.domain.value_objects.nivel_riesgo import NivelRiesgo, TipoInteraccion
from src.infrastructure.db.models.trazabilidad_models import (
    FeedbackModel,
    IndicadorModel,
    InteraccionModel,
    ProgresoHistorialModel,
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
            concept_id=i.concept_id,
            is_correct=i.is_correct,
            nota=i.nota,
            url_modulo=i.url_modulo,
            nombre_actividad=i.nombre_actividad,
            tipo_recurso=i.tipo_recurso,
            es_vista=i.es_vista,
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
                concept_id=m.concept_id,
                is_correct=m.is_correct,
                url_modulo=getattr(m, "url_modulo", "") or "",
                nombre_actividad=getattr(m, "nombre_actividad", "") or "",
                tipo_recurso=getattr(m, "tipo_recurso", "") or "",
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
        # Snapshot append-only para la serie temporal de tendencia de clase.
        self._s.add(
            ProgresoHistorialModel(
                estudiante_id=p.estudiante_id,
                curso_id=p.curso_id,
                nivel_riesgo=p.nivel_riesgo.value,
                puntaje_promedio=p.puntaje_promedio,
            )
        )
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

    async def contar_interacciones_recientes(
        self, curso_id: UUID, desde: datetime
    ) -> dict[str, int]:
        rows = await self._s.execute(
            select(InteraccionModel.estudiante_id, func.count())
            .where(
                InteraccionModel.curso_id == curso_id,
                InteraccionModel.fecha >= desde,
            )
            .group_by(InteraccionModel.estudiante_id)
        )
        return {str(est_id): total for est_id, total in rows.all()}

    async def contar_conceptos_en_riesgo(self, curso_id: UUID) -> dict[str, int]:
        rows = await self._s.execute(
            select(
                InteraccionModel.estudiante_id,
                InteraccionModel.concept_id,
                func.avg(case((InteraccionModel.is_correct, 1.0), else_=0.0)),
            )
            .where(
                InteraccionModel.curso_id == curso_id,
                InteraccionModel.concept_id.is_not(None),
                InteraccionModel.is_correct.is_not(None),
            )
            .group_by(InteraccionModel.estudiante_id, InteraccionModel.concept_id)
        )
        counts: dict[str, int] = {}
        for est_id, _concept, ratio in rows.all():
            if ratio is not None and float(ratio) < 0.5:
                counts[str(est_id)] = counts.get(str(est_id), 0) + 1
        return counts

    # --- Sincronización LMS -------------------------------------------------
    async def upsert_interaccion_lms(self, item: InteraccionLms) -> bool:
        if item.moodle_event_id:
            existente = (
                await self._s.execute(
                    select(InteraccionModel)
                    .where(InteraccionModel.moodle_event_id == item.moodle_event_id)
                    .limit(1)
                )
            ).scalar_one_or_none()
            if existente is not None:
                # Idempotente pero auto-corrige: actualiza corrección/nota/concepto
                # por si la nota en Moodle cambió o el registro venía incompleto.
                existente.is_correct = item.es_correcta
                existente.nota = item.nota
                existente.concept_id = item.concepto or None
                if item.url_modulo:
                    existente.url_modulo = item.url_modulo
                if item.nombre_actividad:
                    existente.nombre_actividad = item.nombre_actividad
                if item.tipo_recurso:
                    existente.tipo_recurso = item.tipo_recurso
                existente.es_vista = item.es_vista
                return False

        tipo = TipoInteraccion.COMPLETADO if item.es_correcta else TipoInteraccion.VISTA
        fecha = (
            item.fecha_evento
            if item.fecha_evento.tzinfo
            else item.fecha_evento.replace(tzinfo=timezone.utc)
        )
        self._s.add(
            InteraccionModel(
                estudiante_id=item.estudiante_id,
                curso_id=item.curso_id,
                actividad_id=item.actividad_id,
                concept_id=item.concepto or None,
                is_correct=item.es_correcta,
                nota=item.nota,
                url_modulo=item.url_modulo,
                nombre_actividad=item.nombre_actividad,
                tipo_recurso=item.tipo_recurso,
                es_vista=item.es_vista,
                tipo=tipo.value,
                fecha=fecha,
                moodle_event_id=item.moodle_event_id,
            )
        )
        return True

    async def flush_interacciones_lms(self) -> None:
        await self._s.flush()

    async def agregar_metricas_estudiante(
        self, estudiante_id: UUID, curso_id: UUID
    ) -> AgregadoEstudiante | None:
        fila = (
            await self._s.execute(
                select(
                    func.count(InteraccionModel.id),
                    func.count(InteraccionModel.id).filter(
                        InteraccionModel.is_correct.is_(True)
                    ),
                    func.avg(InteraccionModel.nota),
                    func.max(InteraccionModel.fecha),
                ).where(
                    InteraccionModel.estudiante_id == estudiante_id,
                    InteraccionModel.curso_id == curso_id,
                )
            )
        ).one()
        total = int(fila[0] or 0)
        if total == 0:
            return AgregadoEstudiante(0, 0, None, None)
        return AgregadoEstudiante(
            total=total,
            correctas=int(fila[1] or 0),
            promedio_nota=float(fila[2]) if fila[2] is not None else None,
            ultima_actividad=fila[3],
        )

    async def recomputar_progreso_lms(self, datos: ProgresoRecomputado) -> None:
        prog = (
            await self._s.execute(
                select(ProgresoModel).where(
                    ProgresoModel.estudiante_id == datos.estudiante_id,
                    ProgresoModel.curso_id == datos.curso_id,
                )
            )
        ).scalar_one_or_none()
        if prog is None:
            prog = ProgresoModel(
                estudiante_id=datos.estudiante_id, curso_id=datos.curso_id
            )
            self._s.add(prog)
        prog.total_interacciones = datos.total_interacciones
        prog.recursos_completados = datos.recursos_completados
        prog.puntaje_promedio = datos.puntaje
        prog.porcentaje_avance = datos.puntaje
        prog.nivel_riesgo = datos.nivel_riesgo.value
        if datos.ultima_actividad is not None:
            prog.ultima_actividad = datos.ultima_actividad
        if datos.nombre:
            prog.nombre = datos.nombre
        if datos.correo:
            prog.correo = datos.correo

    async def commit_lms_sync(self) -> None:
        await self._s.commit()

    # --- Lecturas analíticas ------------------------------------------------
    async def calcular_preferencias(
        self, estudiante_id: UUID, curso_id: UUID
    ) -> PreferenciasFormato:
        rows = (
            await self._s.execute(
                select(
                    InteraccionModel.tipo_recurso,
                    InteraccionModel.nota,
                    InteraccionModel.is_correct,
                    InteraccionModel.es_vista,
                    InteraccionModel.url_modulo,
                ).where(
                    InteraccionModel.estudiante_id == estudiante_id,
                    InteraccionModel.curso_id == curso_id,
                )
            )
        ).all()

        # RENDIMIENTO (calificadas): tipo -> [suma de notas, total]
        agregados: dict[str, list[float]] = {}
        # ENGAGEMENT (vistas): tipo -> count de vistas
        vistas_por_tipo: dict[str, int] = {}
        # Recursos ya vistos (url_modulo distintos, no vacíos).
        recursos_vistos: list[str] = []
        vistos_set: set[str] = set()
        for tipo_recurso, nota, is_correct, es_vista, url_modulo in rows:
            if es_vista:
                if tipo_recurso:
                    vistas_por_tipo[tipo_recurso] = (
                        vistas_por_tipo.get(tipo_recurso, 0) + 1
                    )
                if url_modulo and url_modulo not in vistos_set:
                    vistos_set.add(url_modulo)
                    recursos_vistos.append(url_modulo)
                continue
            if not tipo_recurso:
                continue
            valor = float(nota) if nota is not None else (100.0 if is_correct else 0.0)
            acc = agregados.setdefault(tipo_recurso, [0.0, 0.0])
            acc[0] += valor
            acc[1] += 1

        por_tipo = [
            {"tipo": tipo, "promedio": round(suma / total, 1), "total": int(total)}
            for tipo, (suma, total) in agregados.items()
        ]
        por_tipo.sort(key=lambda x: x["promedio"], reverse=True)

        candidatos = [p for p in por_tipo if p["total"] >= 2]
        if not candidatos and por_tipo:
            candidatos = [max(por_tipo, key=lambda x: x["total"])]
        tipo_fuerte = (
            max(candidatos, key=lambda x: x["promedio"])["tipo"] if candidatos else ""
        )
        tipo_debil = (
            min(candidatos, key=lambda x: x["promedio"])["tipo"] if candidatos else ""
        )

        engagement_por_tipo = [
            {"tipo": tipo, "vistas": vistas} for tipo, vistas in vistas_por_tipo.items()
        ]
        engagement_por_tipo.sort(key=lambda x: x["vistas"], reverse=True)
        formato_mas_consumido = (
            engagement_por_tipo[0]["tipo"] if engagement_por_tipo else ""
        )

        return PreferenciasFormato(
            por_tipo=por_tipo,
            tipo_fuerte=tipo_fuerte,
            tipo_debil=tipo_debil,
            engagement_por_tipo=engagement_por_tipo,
            formato_mas_consumido=formato_mas_consumido,
            recursos_vistos=recursos_vistos,
        )

    async def concepto_mastery(
        self, estudiante_id: UUID, curso_id: UUID
    ) -> list[ConceptoMastery]:
        rows = (
            await self._s.execute(
                select(
                    InteraccionModel.concept_id,
                    func.count(InteraccionModel.id),
                    func.count(InteraccionModel.id).filter(
                        InteraccionModel.is_correct.is_(True)
                    ),
                    func.avg(InteraccionModel.nota),
                )
                .where(
                    InteraccionModel.estudiante_id == estudiante_id,
                    InteraccionModel.curso_id == curso_id,
                    InteraccionModel.concept_id.isnot(None),
                )
                .group_by(InteraccionModel.concept_id)
            )
        ).all()
        out: list[ConceptoMastery] = []
        for concepto, total, correctas, prom_nota in rows:
            total = int(total or 0)
            correctas = int(correctas or 0)
            if total == 0:
                continue
            dominio = (
                round(float(prom_nota), 1)
                if prom_nota is not None
                else round(correctas / total * 100, 1)
            )
            out.append(
                ConceptoMastery(
                    concepto=concepto,
                    dominio=dominio,
                    total=total,
                    correctas=correctas,
                )
            )
        out.sort(key=lambda c: c.dominio)
        return out

    async def actividad_por_dia(
        self, desde, curso_id: UUID | None
    ) -> list[ActividadDiaria]:
        condiciones = [func.date(InteraccionModel.fecha) >= desde]
        if curso_id is not None:
            condiciones.append(InteraccionModel.curso_id == curso_id)
        rows = (
            await self._s.execute(
                select(
                    func.date(InteraccionModel.fecha).label("dia"),
                    func.count(InteraccionModel.id),
                )
                .where(*condiciones)
                .group_by(func.date(InteraccionModel.fecha))
            )
        ).all()
        return [
            ActividadDiaria(dia=str(dia), total=int(total or 0)) for dia, total in rows
        ]

    async def secuencia_estudiante(
        self, estudiante_id: UUID, curso_id: UUID
    ) -> list[SecuenciaInteraccion]:
        rows = (
            await self._s.execute(
                select(InteraccionModel.is_correct, InteraccionModel.nota)
                .where(
                    InteraccionModel.estudiante_id == estudiante_id,
                    InteraccionModel.curso_id == curso_id,
                )
                .order_by(InteraccionModel.fecha, InteraccionModel.id)
            )
        ).all()
        return [SecuenciaInteraccion(is_correct=ic, nota=nota) for ic, nota in rows]

    async def secuencia_curso(self, curso_id: UUID) -> list[SecuenciaTendencia]:
        rows = (
            await self._s.execute(
                select(
                    InteraccionModel.estudiante_id,
                    InteraccionModel.is_correct,
                    InteraccionModel.nota,
                )
                .where(InteraccionModel.curso_id == curso_id)
                .order_by(InteraccionModel.fecha, InteraccionModel.id)
            )
        ).all()
        return [
            SecuenciaTendencia(estudiante_id=est, is_correct=ic, nota=nota)
            for est, ic, nota in rows
        ]

    async def metricas_plataforma(self) -> MetricasPlataforma:
        avg = (
            await self._s.execute(select(func.avg(ProgresoModel.puntaje_promedio)))
        ).scalar()
        total = (
            await self._s.execute(select(func.count()).select_from(ProgresoModel))
        ).scalar_one()
        return MetricasPlataforma(
            dominio_promedio=round(float(avg), 1) if avg is not None else None,
            estudiantes_con_progreso=int(total),
        )

    async def training_data(self) -> list[TrainingRow]:
        rows = (
            await self._s.execute(
                select(
                    InteraccionModel.estudiante_id,
                    InteraccionModel.concept_id,
                    InteraccionModel.is_correct,
                    InteraccionModel.fecha,
                    InteraccionModel.tipo_recurso,
                )
                .where(
                    InteraccionModel.concept_id.isnot(None),
                    InteraccionModel.concept_id != "",
                    InteraccionModel.es_vista.is_(False),
                )
                .order_by(InteraccionModel.estudiante_id, InteraccionModel.fecha)
            )
        ).all()
        return [
            TrainingRow(
                estudiante_id=est,
                concepto=concepto,
                correcta=bool(correcta),
                fecha=fecha,
                tipo_recurso=tipo_recurso or "",
            )
            for est, concepto, correcta, fecha, tipo_recurso in rows
        ]

    async def find_historial_curso(self, curso_id: UUID) -> list[ProgresoHistorial]:
        rows = await self._s.execute(
            select(ProgresoHistorialModel)
            .where(ProgresoHistorialModel.curso_id == curso_id)
            .order_by(ProgresoHistorialModel.registrado_en.asc())
        )
        return [
            ProgresoHistorial(
                estudiante_id=m.estudiante_id,
                curso_id=m.curso_id,
                nivel_riesgo=NivelRiesgo(m.nivel_riesgo),
                puntaje_promedio=m.puntaje_promedio,
                registrado_en=m.registrado_en,
            )
            for m in rows.scalars().all()
        ]


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
        nombre=getattr(m, "nombre", "") or "",
        correo=getattr(m, "correo", "") or "",
        ultima_actividad=m.ultima_actividad,
    )
