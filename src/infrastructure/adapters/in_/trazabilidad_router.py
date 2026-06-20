from datetime import datetime, timezone
from io import BytesIO
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sward_shared.identidad import moodle_uuid as _moodle_id

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
from src.application.use_cases.consultar_tendencia import ConsultarTendenciaUseCase
from src.application.use_cases.generar_reporte_docente import (
    GenerarReporteDocenteUseCase,
)
from src.application.use_cases.registrar_feedback import (
    RegistrarFeedbackCommand,
    RegistrarFeedbackUseCase,
)
from src.application.use_cases.registrar_interaccion import (
    RegistrarInteraccionCommand,
    RegistrarInteraccionUseCase,
)
from src.domain.value_objects.nivel_riesgo import TipoInteraccion
from src.infrastructure.adapters.out_.trazabilidad_postgres_adapter import (
    TrazabilidadPostgresAdapter,
)
from src.infrastructure.db.database import get_session
from src.infrastructure.dependencies import (
    get_calcular_indicadores_uc,
    get_consultar_progreso_uc,
    get_consultar_tendencia_uc,
    get_dashboard_docente_uc,
    get_generar_reporte_docente_uc,
    get_registrar_feedback_uc,
    get_registrar_interaccion_uc,
    get_trazabilidad_repo,
    require_jwt,
    require_service_key,
)

# La derivación Moodle→UUID vive en sward_shared.identidad (_moodle_id, importado arriba).


# Todos los endpoints de trazabilidad exigen un JWT de acceso válido.
router = APIRouter(tags=["Trazabilidad"], dependencies=[Depends(require_jwt)])


class InteraccionRequest(BaseModel):
    """Solicitud para registrar una interacción de estudiante."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "estudiante_id": "550e8400-e29b-41d4-a716-446655440000",
                "curso_id": "550e8400-e29b-41d4-a716-446655440001",
                "tipo": "vista",
                "actividad_id": "550e8400-e29b-41d4-a716-446655440002",
                "recurso_id": None,
                "puntaje": None,
                "moodle_event_id": "12345",
            }
        },
    )

    estudiante_id: UUID = Field(
        description="UUID del estudiante",
        example="550e8400-e29b-41d4-a716-446655440000",
    )
    curso_id: UUID = Field(
        description="UUID del curso", example="550e8400-e29b-41d4-a716-446655440001"
    )
    tipo: TipoInteraccion = Field(
        default=TipoInteraccion.VISTA,
        description="Tipo de interacción realizada",
        example="vista",
    )
    actividad_id: UUID | None = Field(
        default=None,
        description="UUID de la actividad asociada (opcional)",
        example="550e8400-e29b-41d4-a716-446655440002",
    )
    recurso_id: UUID | None = Field(
        default=None,
        description="UUID del recurso asociado (opcional)",
        example=None,
    )
    puntaje: float | None = Field(
        default=None,
        ge=0,
        le=100,
        description="Puntaje de la interacción (opcional, 0-100)",
        example=None,
    )
    moodle_event_id: str = Field(
        default="",
        max_length=128,
        description="ID del evento en Moodle para trazabilidad",
        example="12345",
    )


class InteraccionResponse(BaseModel):
    """Respuesta que contiene información de una interacción registrada."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440003",
                "tipo": "vista",
                "fecha": "2025-05-31T14:30:00Z",
            }
        },
    )

    id: str = Field(
        description="UUID única de la interacción",
        example="550e8400-e29b-41d4-a716-446655440003",
    )
    tipo: str = Field(description="Tipo de interacción registrada", example="vista")
    fecha: str = Field(
        description="Fecha y hora de la interacción en ISO 8601",
        example="2025-05-31T14:30:00Z",
    )


class ProgresoResponse(BaseModel):
    """Respuesta que contiene información del progreso de un estudiante."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440004",
                "porcentaje_avance": 65.5,
                "nivel_riesgo": "bajo",
                "total_interacciones": 45,
                "puntaje_promedio": 78.5,
            }
        },
    )

    id: str = Field(
        description="UUID del registro de progreso",
        example="550e8400-e29b-41d4-a716-446655440004",
    )
    porcentaje_avance: float = Field(
        description="Porcentaje de avance en el curso", ge=0, le=100, example=65.5
    )
    nivel_riesgo: str = Field(
        description="Nivel de riesgo académico (bajo, medio, alto, critico)",
        example="bajo",
    )
    total_interacciones: int = Field(
        description="Cantidad total de interacciones", ge=0, example=45
    )
    puntaje_promedio: float = Field(
        description="Puntaje promedio en actividades", ge=0, le=100, example=78.5
    )


class IndicadorResponse(BaseModel):
    """Respuesta que contiene un indicador de desempeño."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "nombre": "Participación",
                "valor": 85.0,
                "unidad": "porcentaje",
            }
        },
    )

    nombre: str = Field(
        description="Nombre del indicador", max_length=100, example="Participación"
    )
    valor: float = Field(description="Valor del indicador", example=85.0)
    unidad: str = Field(
        description="Unidad de medida del indicador",
        max_length=50,
        example="porcentaje",
    )


class EstudianteProgressResponse(BaseModel):
    """Respuesta que contiene el progreso de un estudiante en el dashboard docente."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "estudiante_id": "550e8400-e29b-41d4-a716-446655440000",
                "nombre": "Ana",
                "apellido": "Quispe",
                "correo": "ana.quispe@upc.edu.pe",
                "nivel_riesgo": "medio",
                "puntaje_promedio": 72.0,
                "total_interacciones": 38,
                "recursos_completados": 12,
            }
        },
    )

    estudiante_id: str = Field(
        description="UUID del estudiante",
        example="550e8400-e29b-41d4-a716-446655440000",
    )
    nombre: str = Field(default="", description="Nombre del estudiante", example="Ana")
    apellido: str = Field(
        default="", description="Apellido del estudiante", example="Quispe"
    )
    correo: str = Field(
        default="",
        description="Correo institucional del estudiante",
        example="ana.quispe@upc.edu.pe",
    )
    nivel_riesgo: str = Field(description="Nivel de riesgo académico", example="medio")
    puntaje_promedio: float = Field(
        description="Puntaje promedio del estudiante", ge=0, le=100, example=72.0
    )
    total_interacciones: int = Field(
        description="Cantidad total de interacciones", ge=0, example=38
    )
    recursos_completados: int = Field(
        description="Cantidad de recursos completados", ge=0, example=12
    )
    engagement: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Índice de engagement (actividad de los últimos 30 días)",
        example=60,
    )
    conceptos_en_riesgo: int = Field(
        default=0,
        ge=0,
        description="Nº de conceptos (secciones) con tasa de acierto < 0.5",
        example=2,
    )
    registrado_en_sward: bool = Field(
        default=False,
        description="True si el estudiante tiene cuenta en SWARD; False si solo está en Moodle",
        example=True,
    )
    ultima_actividad: str = Field(
        default="",
        description="Fecha/hora de la última actividad (ISO 8601)",
        example="2026-06-18T12:00:00Z",
    )


@router.post(
    "/interactions",
    status_code=status.HTTP_201_CREATED,
    response_model=InteraccionResponse,
    responses={
        201: {
            "description": "Interacción registrada exitosamente",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440003",
                        "tipo": "vista",
                        "fecha": "2025-05-31T14:30:00Z",
                    }
                }
            },
        },
        400: {"description": "Solicitud inválida. Parámetros incorrectos."},
        401: {"description": "No autorizado. JWT inválido o expirado."},
        422: {"description": "Entidad no procesable. Validación de datos fallida."},
        500: {"description": "Error interno del servidor."},
    },
)
async def registrar_interaccion(
    body: InteraccionRequest = Body(
        ..., description="Datos de la interacción a registrar"
    ),
    uc: RegistrarInteraccionUseCase = Depends(get_registrar_interaccion_uc),
):
    """Registra una nueva interacción de estudiante en el curso.

    **Flujo:** 1. Valida JWT 2. Registra interacción en base de datos 3. Retorna confirmación

    **SLA:** <100ms | **Auth:** JWT | **Rate Limit:** 300 req/min
    """
    i = await uc.execute(RegistrarInteraccionCommand(**body.model_dump()))
    return {"id": str(i.id), "tipo": i.tipo, "fecha": i.fecha.isoformat()}


@router.get(
    "/students/{student_id}/progress",
    status_code=status.HTTP_200_OK,
    response_model=ProgresoResponse,
    responses={
        200: {
            "description": "Progreso obtenido exitosamente",
            "content": {
                "application/json": {
                    "example": {
                        "id": "550e8400-e29b-41d4-a716-446655440004",
                        "porcentaje_avance": 65.5,
                        "nivel_riesgo": "bajo",
                        "total_interacciones": 45,
                        "puntaje_promedio": 78.5,
                    }
                }
            },
        },
        401: {"description": "No autorizado. JWT inválido o expirado."},
        404: {"description": "Estudiante o curso no encontrado."},
        500: {"description": "Error interno del servidor."},
    },
)
async def get_progress(
    student_id: UUID = Path(..., description="UUID del estudiante"),
    courseId: UUID = Query(..., description="UUID del curso"),
    uc: ConsultarProgresoUseCase = Depends(get_consultar_progreso_uc),
):
    """Obtiene el progreso de un estudiante en un curso específico.

    **Flujo:** 1. Valida JWT 2. Consulta base de datos 3. Calcula métricas de progreso 4. Retorna información

    **SLA:** <150ms | **Auth:** JWT | **Rate Limit:** 120 req/min
    """
    p = await uc.execute(
        ConsultarProgresoCommand(estudiante_id=student_id, curso_id=courseId)
    )
    if not p:
        return {
            "id": str(student_id),
            "porcentaje_avance": 0.0,
            "nivel_riesgo": "alto",
            "total_interacciones": 0,
            "puntaje_promedio": 0.0,
        }
    return {
        "id": str(p.id),
        "porcentaje_avance": p.porcentaje_avance,
        "nivel_riesgo": p.nivel_riesgo,
        "total_interacciones": p.total_interacciones,
        "puntaje_promedio": p.puntaje_promedio,
    }


@router.get(
    "/students/{student_id}/indicators",
    status_code=status.HTTP_200_OK,
    response_model=list[IndicadorResponse],
    responses={
        200: {
            "description": "Indicadores obtenidos exitosamente",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "nombre": "Participación",
                            "valor": 85.0,
                            "unidad": "porcentaje",
                        }
                    ]
                }
            },
        },
        401: {"description": "No autorizado. JWT inválido o expirado."},
        404: {"description": "Estudiante o curso no encontrado."},
        500: {"description": "Error interno del servidor."},
    },
)
async def get_indicators(
    student_id: UUID = Path(..., description="UUID del estudiante"),
    courseId: UUID = Query(..., description="UUID del curso"),
    uc: CalcularIndicadoresUseCase = Depends(get_calcular_indicadores_uc),
):
    """Obtiene los indicadores de desempeño de un estudiante en un curso.

    **Flujo:** 1. Valida JWT 2. Calcula indicadores 3. Retorna lista de indicadores

    **SLA:** <200ms | **Auth:** JWT | **Rate Limit:** 120 req/min
    """
    indicadores = await uc.execute(
        CalcularIndicadoresCommand(estudiante_id=student_id, curso_id=courseId)
    )
    return [
        {"nombre": i.nombre, "valor": i.valor, "unidad": i.unidad} for i in indicadores
    ]


async def _get_interactions_handler(
    student_id: UUID,
    courseId: UUID | None,
    limit: int,
    repo: TrazabilidadPostgresAdapter,
) -> list[dict]:
    items = await repo.find_interacciones(student_id, courseId, limit)
    return [
        {
            "id": str(i.id),
            "actividad_id": str(i.actividad_id) if i.actividad_id else None,
            "concept_id": i.concept_id,
            "is_correct": i.is_correct,
            "tipo": i.tipo.value,
            "fecha": i.fecha.isoformat(),
            "curso_id": str(i.curso_id),
            "url_modulo": i.url_modulo,
            "nombre_actividad": i.nombre_actividad,
        }
        for i in items
    ]


@router.get(
    "/students/{student_id}/interactions",
    status_code=status.HTTP_200_OK,
    responses={
        200: {"description": "Interacciones obtenidas exitosamente"},
        401: {"description": "No autorizado. JWT inválido o expirado."},
        404: {"description": "Estudiante no encontrado."},
        500: {"description": "Error interno del servidor."},
    },
)
async def get_interactions(
    student_id: UUID = Path(..., description="UUID del estudiante"),
    courseId: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    repo: TrazabilidadPostgresAdapter = Depends(get_trazabilidad_repo),
):
    """Obtiene el historial de interacciones de un estudiante (auth JWT).

    **SLA:** <200ms | **Auth:** JWT | **Rate Limit:** 120 req/min
    """
    return await _get_interactions_handler(student_id, courseId, limit, repo)


@router.get("/students/{student_id}/concept-mastery", status_code=status.HTTP_200_OK)
async def get_concept_mastery(
    student_id: UUID = Path(..., description="UUID del estudiante"),
    courseId: UUID = Query(..., description="UUID del curso"),
    session: AsyncSession = Depends(get_session),
):
    """Dominio real por concepto/sección del curso para un estudiante.

    Agrupa las interacciones por ``concept_id`` (sección de Moodle) y calcula la
    tasa de acierto. Alimenta el radar, las barras y las recomendaciones del
    detalle del estudiante. Orden: peores primero.
    """
    from sqlalchemy import func as sa_func
    from sqlalchemy import select as sa_select

    from src.infrastructure.db.models.trazabilidad_models import InteraccionModel

    rows = (
        await session.execute(
            sa_select(
                InteraccionModel.concept_id,
                sa_func.count(InteraccionModel.id),
                sa_func.count(InteraccionModel.id).filter(
                    InteraccionModel.is_correct.is_(True)
                ),
                sa_func.avg(InteraccionModel.nota),
            )
            .where(
                InteraccionModel.estudiante_id == student_id,
                InteraccionModel.curso_id == courseId,
                InteraccionModel.concept_id.isnot(None),
            )
            .group_by(InteraccionModel.concept_id)
        )
    ).all()
    out = []
    for concepto, total, correctas, prom_nota in rows:
        total = int(total or 0)
        correctas = int(correctas or 0)
        if total == 0:
            continue
        # Dominio continuo = promedio de la nota; fallback a % aciertos si no hay.
        dominio = (
            round(float(prom_nota), 1)
            if prom_nota is not None
            else round(correctas / total * 100, 1)
        )
        out.append(
            {
                "concepto": concepto,
                "dominio": dominio,
                "total": total,
                "correctas": correctas,
            }
        )
    out.sort(key=lambda x: x["dominio"])
    return out


@router.get("/dashboard/platform-activity", status_code=status.HTTP_200_OK)
async def platform_activity(
    days: int = Query(7, ge=1, le=30, description="Días hacia atrás a incluir"),
    courseId: UUID | None = Query(None, description="Filtra por curso (opcional)"),
    session: AsyncSession = Depends(get_session),
):
    """Actividad real de la plataforma: # de interacciones por día (últimos N días).

    Alimenta el gráfico de actividad del panel de administración con datos
    reales. Los días sin actividad se devuelven en cero (serie continua).
    """
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import func as sa_func
    from sqlalchemy import select as sa_select

    from src.infrastructure.db.models.trazabilidad_models import InteraccionModel

    hoy = datetime.now(timezone.utc).date()
    desde = hoy - timedelta(days=days - 1)

    condiciones = [sa_func.date(InteraccionModel.fecha) >= desde]
    if courseId is not None:
        condiciones.append(InteraccionModel.curso_id == courseId)

    rows = (
        await session.execute(
            sa_select(
                sa_func.date(InteraccionModel.fecha).label("dia"),
                sa_func.count(InteraccionModel.id),
            )
            .where(*condiciones)
            .group_by(sa_func.date(InteraccionModel.fecha))
        )
    ).all()
    counts = {str(dia): int(total or 0) for dia, total in rows}

    dias_es = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    out = []
    for i in range(days):
        d = desde + timedelta(days=i)
        out.append({"day": f"{dias_es[d.weekday()]} {d.day:02d}", "sesiones": counts.get(str(d), 0)})
    return out


@router.get("/students/{student_id}/weekly-progress", status_code=status.HTTP_200_OK)
async def get_weekly_progress(
    student_id: UUID = Path(..., description="UUID del estudiante"),
    courseId: UUID = Query(..., description="UUID del curso"),
    session: AsyncSession = Depends(get_session),
):
    """Evolución del dominio: dominio acumulado (running % de aciertos) a lo
    largo de la secuencia de actividades, en hasta 6 etapas.

    Se usa la secuencia (no semanas calendario) porque las notas de Moodle no
    traen fecha de envío fiable; así la curva refleja la evolución real.
    """
    from sqlalchemy import select as sa_select

    from src.infrastructure.db.models.trazabilidad_models import InteraccionModel

    rows = (
        await session.execute(
            sa_select(InteraccionModel.is_correct, InteraccionModel.nota)
            .where(
                InteraccionModel.estudiante_id == student_id,
                InteraccionModel.curso_id == courseId,
            )
            .order_by(InteraccionModel.fecha, InteraccionModel.id)
        )
    ).all()
    n = len(rows)
    if n == 0:
        return []
    etapas = min(6, n)
    tam = n / etapas
    acum_total = 0
    acum_nota = 0.0  # suma de notas (o 0/100 si no hay nota) para el promedio acumulado
    out = []
    for i, (is_correct, nota) in enumerate(rows, start=1):
        acum_total += 1
        acum_nota += float(nota) if nota is not None else (100.0 if is_correct else 0.0)
        if i >= round((len(out) + 1) * tam) or i == n:
            out.append(
                {
                    "etapa": f"E{len(out) + 1}",
                    "dominio": round(acum_nota / acum_total, 1),
                }
            )
            if len(out) >= etapas:
                break
    return out


# ---------------------------------------------------------------------------
# Schemas para el endpoint interno de sincronización LMS
# ---------------------------------------------------------------------------


class LmsInteraccionItem(BaseModel):
    moodle_user_id: str
    moodle_course_id: str
    moodle_activity_id: str
    nombre: str = ""
    correo: str = ""
    concepto: str = ""
    es_correcta: bool = False
    nota: float = 0.0
    url_modulo: str = ""
    nombre_actividad: str = ""
    fecha_evento: datetime
    moodle_event_id: str = ""


class LmsSyncRequest(BaseModel):
    interacciones: list[LmsInteraccionItem]


# Router interno: autenticación por service-key (sin JWT de usuario).
internal_router = APIRouter(
    tags=["LMS — Interno"], dependencies=[Depends(require_service_key)]
)


@internal_router.post("/internal/lms-sync", status_code=202)
async def lms_sync(
    body: LmsSyncRequest,
    session: AsyncSession = Depends(get_session),
):
    """Recibe interacciones desde ms-integracion-lms y las persiste.

    Convierte los IDs numéricos de Moodle a UUIDs determinísticos (uuid5) y
    realiza deduplicación por ``moodle_event_id``.

    **Auth:** X-Service-Key | **Idempotente:** sí (omite eventos ya procesados)
    """
    from sqlalchemy import func as sa_func
    from sqlalchemy import select as sa_select

    from src.domain.value_objects.nivel_riesgo import NivelRiesgo, TipoInteraccion
    from src.infrastructure.db.models.trazabilidad_models import (
        InteraccionModel,
        ProgresoModel,
    )

    procesadas = 0
    omitidas = 0
    # (estudiante_id, curso_id) afectados -> para recomputar su progreso.
    afectados: set[tuple] = set()
    # estudiante_id -> (nombre, correo) más reciente visto en este lote.
    perfiles: dict = {}
    for item in body.interacciones:
        est_id = _moodle_id("user", item.moodle_user_id)
        cur_id = _moodle_id("course", item.moodle_course_id)
        afectados.add((est_id, cur_id))
        if item.nombre or item.correo:
            perfiles[est_id] = (item.nombre, item.correo)

        if item.moodle_event_id:
            existente = (
                await session.execute(
                    sa_select(InteraccionModel)
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
                omitidas += 1
                continue

        tipo = TipoInteraccion.COMPLETADO if item.es_correcta else TipoInteraccion.VISTA
        fecha = (
            item.fecha_evento
            if item.fecha_evento.tzinfo
            else item.fecha_evento.replace(tzinfo=timezone.utc)
        )
        m = InteraccionModel(
            estudiante_id=est_id,
            curso_id=cur_id,
            actividad_id=_moodle_id("activity", item.moodle_activity_id),
            concept_id=item.concepto or None,
            is_correct=item.es_correcta,
            nota=item.nota,
            url_modulo=item.url_modulo,
            nombre_actividad=item.nombre_actividad,
            tipo=tipo.value,
            fecha=fecha,
            moodle_event_id=item.moodle_event_id,
        )
        session.add(m)
        procesadas += 1

    # Persiste las interacciones para poder agregarlas (mismo commit).
    await session.flush()

    # Recomputa academic_progress por estudiante/curso desde TODAS sus interacciones.
    for est_id, cur_id in afectados:
        fila = (
            await session.execute(
                sa_select(
                    sa_func.count(InteraccionModel.id),
                    sa_func.count(InteraccionModel.id).filter(
                        InteraccionModel.is_correct.is_(True)
                    ),
                    sa_func.avg(InteraccionModel.nota),
                    sa_func.max(InteraccionModel.fecha),
                ).where(
                    InteraccionModel.estudiante_id == est_id,
                    InteraccionModel.curso_id == cur_id,
                )
            )
        ).one()
        total, correctas, prom_nota, ultima = (
            int(fila[0] or 0),
            int(fila[1] or 0),
            fila[2],
            fila[3],
        )
        if total == 0:
            continue
        # Dominio = promedio de la nota real (continuo). Si no hay notas, cae al
        # % de aciertos para no romper datos antiguos.
        puntaje = (
            round(float(prom_nota), 1)
            if prom_nota is not None
            else round(correctas / total * 100, 1)
        )
        if puntaje < 40:
            riesgo = NivelRiesgo.CRITICO
        elif puntaje < 55:
            riesgo = NivelRiesgo.ALTO
        elif puntaje < 70:
            riesgo = NivelRiesgo.MEDIO
        else:
            riesgo = NivelRiesgo.BAJO
        nombre, correo = perfiles.get(est_id, ("", ""))

        prog = (
            await session.execute(
                sa_select(ProgresoModel).where(
                    ProgresoModel.estudiante_id == est_id,
                    ProgresoModel.curso_id == cur_id,
                )
            )
        ).scalar_one_or_none()
        if prog is None:
            prog = ProgresoModel(estudiante_id=est_id, curso_id=cur_id)
            session.add(prog)
        prog.total_interacciones = total
        prog.recursos_completados = correctas
        prog.puntaje_promedio = puntaje
        prog.porcentaje_avance = puntaje
        prog.nivel_riesgo = riesgo.value
        if ultima is not None:
            prog.ultima_actividad = ultima
        if nombre:
            prog.nombre = nombre
        if correo:
            prog.correo = correo

    await session.commit()
    return {"procesadas": procesadas, "omitidas": omitidas}


@internal_router.get(
    "/internal/students/{student_id}/interactions",
    status_code=status.HTTP_200_OK,
)
async def get_interactions_internal(
    student_id: UUID = Path(..., description="UUID del estudiante"),
    courseId: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    repo: TrazabilidadPostgresAdapter = Depends(get_trazabilidad_repo),
):
    """Obtiene interacciones de un estudiante (auth service-key, s2s).

    Usado por ms-recomendacion para construir la secuencia SAKT.
    """
    return await _get_interactions_handler(student_id, courseId, limit, repo)


@internal_router.get("/internal/metrics/platform", status_code=status.HTTP_200_OK)
async def get_platform_metrics(
    session: AsyncSession = Depends(get_session),
):
    """Métricas agregadas de toda la plataforma (s2s, auth service-key).

    Usado por ms-usuarios para el KPI "Dominio Plataforma" del panel admin.
    Promedia ``puntaje_promedio`` sobre todos los progresos académicos.
    """
    from sqlalchemy import func as sa_func
    from sqlalchemy import select as sa_select

    from src.infrastructure.db.models.trazabilidad_models import ProgresoModel

    avg = (
        await session.execute(sa_select(sa_func.avg(ProgresoModel.puntaje_promedio)))
    ).scalar()
    total = (
        await session.execute(sa_select(sa_func.count()).select_from(ProgresoModel))
    ).scalar_one()
    return {
        "dominio_promedio": round(float(avg), 1) if avg is not None else None,
        "estudiantes_con_progreso": int(total),
    }


@router.get(
    "/dashboard/teacher/{course_id}/students-progress",
    status_code=status.HTTP_200_OK,
    response_model=list[EstudianteProgressResponse],
    responses={
        200: {
            "description": "Progreso de estudiantes obtenido exitosamente",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "estudiante_id": "550e8400-e29b-41d4-a716-446655440000",
                            "nivel_riesgo": "medio",
                            "puntaje_promedio": 72.0,
                            "total_interacciones": 38,
                            "recursos_completados": 12,
                        }
                    ]
                }
            },
        },
        401: {"description": "No autorizado. JWT inválido o expirado."},
        403: {"description": "Acceso denegado. No es docente del curso."},
        404: {"description": "Curso no encontrado."},
        500: {"description": "Error interno del servidor."},
    },
)
async def dashboard_docente(
    course_id: UUID = Path(..., description="UUID del curso"),
    uc: ConsultarDashboardDocenteUseCase = Depends(get_dashboard_docente_uc),
):
    """Obtiene el dashboard de progreso de todos los estudiantes para un docente.

    **Flujo:** 1. Valida JWT 2. Verifica permisos de docente 3. Calcula métricas agregadas 4. Retorna dashboard

    **SLA:** <300ms | **Auth:** JWT | **Rate Limit:** 60 req/min
    """
    estudiantes = await uc.execute(course_id)
    return [
        {
            "estudiante_id": str(e.progreso.estudiante_id),
            "nombre": e.nombre,
            "apellido": e.apellido,
            "correo": e.correo,
            "nivel_riesgo": e.progreso.nivel_riesgo,
            "puntaje_promedio": e.progreso.puntaje_promedio,
            "total_interacciones": e.progreso.total_interacciones,
            "recursos_completados": e.progreso.recursos_completados,
            "engagement": e.engagement,
            "conceptos_en_riesgo": e.conceptos_en_riesgo,
            "registrado_en_sward": e.registrado_en_sward,
            "ultima_actividad": (
                e.progreso.ultima_actividad.isoformat()
                if e.progreso.ultima_actividad
                else ""
            ),
        }
        for e in estudiantes
    ]


class TendenciaResponse(BaseModel):
    """Punto semanal de la tendencia de la clase (histórico real)."""

    week: str = Field(description="Semana ISO", example="2026-S24")
    promedio: float = Field(description="Puntaje promedio de la semana", example=68.5)
    riesgoAlto: int = Field(  # noqa: N815 (contrato camelCase con el frontend)
        description="Estudiantes en riesgo alto/crítico esa semana", example=3
    )


@router.get(
    "/dashboard/teacher/{course_id}/trend",
    response_model=list[TendenciaResponse],
    responses={
        200: {"description": "Tendencia semanal histórica de la clase"},
        401: {"description": "No autorizado. JWT inválido o expirado."},
    },
)
async def tendencia_docente(
    course_id: UUID = Path(..., description="UUID del curso"),
    uc: ConsultarTendenciaUseCase = Depends(get_consultar_tendencia_uc),
) -> list[dict]:
    """Tendencia semanal del curso a partir del historial real de progreso.

    **Auth:** JWT
    """
    puntos = await uc.execute(course_id)
    return [
        {"week": p.week, "promedio": p.promedio, "riesgoAlto": p.riesgo_alto}
        for p in puntos
    ]


@router.get(
    "/dashboard/teacher/{course_id}/report",
    responses={
        200: {
            "description": "Reporte PDF del progreso de la clase",
            "content": {"application/pdf": {}},
        },
        401: {"description": "No autorizado. JWT inválido o expirado."},
        404: {"description": "Curso no encontrado."},
        500: {"description": "Error interno del servidor."},
    },
)
async def reporte_docente_pdf(
    course_id: UUID = Path(..., description="UUID del curso"),
    uc: GenerarReporteDocenteUseCase = Depends(get_generar_reporte_docente_uc),
) -> StreamingResponse:
    """Genera y descarga el reporte de progreso de la clase en PDF.

    El PDF incluye cabecera SWARD, un resumen agregado por nivel de riesgo y el
    detalle por estudiante (nombre, correo, riesgo, dominio, interacciones).

    **Auth:** JWT | **Content-Type:** application/pdf
    """
    pdf = await uc.execute(course_id)
    filename = f"reporte_clase_{course_id}.pdf"
    return StreamingResponse(
        BytesIO(pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


class FeedbackRequest(BaseModel):
    """Retroalimentación del docente hacia un estudiante."""

    model_config = ConfigDict(extra="forbid")

    estudiante_id: UUID = Field(description="UUID del estudiante destinatario")
    curso_id: UUID = Field(description="UUID del curso")
    mensaje: str = Field(
        min_length=1, max_length=1000, description="Mensaje de retroalimentación"
    )
    tipo: str = Field(
        default="general",
        pattern="^(encouragement|correction|resource|general)$",
        description="Tipo de retroalimentación",
    )


class FeedbackResponse(BaseModel):
    id: str
    estudiante_id: str
    tipo: str
    created_at: datetime


@router.post(
    "/dashboard/teacher/feedback",
    status_code=status.HTTP_201_CREATED,
    response_model=FeedbackResponse,
    responses={
        201: {"description": "Retroalimentación registrada"},
        401: {"description": "No autorizado. JWT inválido o expirado."},
        422: {"description": "Datos inválidos."},
    },
)
async def registrar_feedback(
    body: FeedbackRequest,
    user: dict = Depends(require_jwt),
    uc: RegistrarFeedbackUseCase = Depends(get_registrar_feedback_uc),
) -> FeedbackResponse:
    """Registra retroalimentación del docente autenticado hacia un estudiante.

    El `docente_id` se toma del JWT (claim `sub`), no del body.

    **Auth:** JWT (docente)
    """
    feedback = await uc.execute(
        RegistrarFeedbackCommand(
            docente_id=UUID(user["sub"]),
            estudiante_id=body.estudiante_id,
            curso_id=body.curso_id,
            mensaje=body.mensaje,
            tipo=body.tipo,
        )
    )
    return FeedbackResponse(
        id=str(feedback.id),
        estudiante_id=str(feedback.estudiante_id),
        tipo=feedback.tipo,
        created_at=feedback.created_at,
    )
