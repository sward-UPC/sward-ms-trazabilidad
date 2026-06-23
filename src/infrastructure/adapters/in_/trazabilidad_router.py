from io import BytesIO
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path, Query, status
from fastapi.responses import StreamingResponse

from src.application.use_cases.calcular_indicadores import (
    CalcularIndicadoresCommand,
    CalcularIndicadoresUseCase,
)
from src.application.use_cases.consultar_actividad_plataforma import (
    ConsultarActividadPlataformaUseCase,
)
from src.application.use_cases.consultar_concepto_mastery import (
    ConsultarConceptoMasteryUseCase,
)
from src.application.use_cases.consultar_dashboard_docente import (
    ConsultarDashboardDocenteUseCase,
)
from src.application.use_cases.consultar_evolucion_estudiante import (
    ConsultarEvolucionEstudianteUseCase,
)
from src.application.use_cases.consultar_metricas_plataforma import (
    ConsultarMetricasPlataformaUseCase,
)
from src.application.use_cases.consultar_preferencias import (
    ConsultarPreferenciasUseCase,
)
from src.application.use_cases.consultar_progreso import (
    ConsultarProgresoCommand,
    ConsultarProgresoUseCase,
)
from src.application.use_cases.consultar_tendencia_etapas import (
    ConsultarTendenciaEtapasUseCase,
)
from src.application.use_cases.exportar_training_data import ExportarTrainingDataUseCase
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
from src.application.use_cases.registrar_quiz_result import (
    RegistrarQuizResultCommand,
    RegistrarQuizResultUseCase,
)
from src.application.use_cases.registrar_material_completado import (
    RegistrarMaterialCompletadoCommand,
    RegistrarMaterialCompletadoUseCase,
)
from src.application.use_cases.consultar_racha import ConsultarRachaUseCase
from src.application.use_cases.sincronizar_lms import (
    LmsInteraccionDTO,
    SincronizarLmsCommand,
    SincronizarLmsUseCase,
)
from src.infrastructure.adapters.in_.mappers import _serializar_preferencias
from src.infrastructure.adapters.in_.schemas import (
    ActividadDiariaResponse,
    ConceptoMasteryResponse,
    EstudianteProgressResponse,
    EvolucionEtapaResponse,
    FeedbackRequest,
    FeedbackResponse,
    IndicadorResponse,
    InteraccionRequest,
    InteraccionResponse,
    LmsSyncRequest,
    LmsSyncResponse,
    MaterialCompletadoRequest,
    MaterialCompletadoResponse,
    MetricasPlataformaResponse,
    ProgresoResponse,
    QuizResultRequest,
    QuizResultResponse,
    RachaResponse,
    TendenciaResponse,
    TrainingRowResponse,
)
from src.infrastructure.adapters.out_.trazabilidad_postgres_adapter import (
    TrazabilidadPostgresAdapter,
)
from src.infrastructure.dependencies import (
    get_calcular_indicadores_uc,
    get_consultar_actividad_plataforma_uc,
    get_consultar_concepto_mastery_uc,
    get_consultar_evolucion_estudiante_uc,
    get_consultar_metricas_plataforma_uc,
    get_consultar_preferencias_uc,
    get_consultar_progreso_uc,
    get_consultar_tendencia_etapas_uc,
    get_dashboard_docente_uc,
    get_exportar_training_data_uc,
    get_generar_reporte_docente_uc,
    get_registrar_feedback_uc,
    get_registrar_interaccion_uc,
    get_registrar_quiz_result_uc,
    get_registrar_material_completado_uc,
    get_consultar_racha_uc,
    get_sincronizar_lms_uc,
    get_trazabilidad_repo,
    require_jwt,
    require_service_key,
)


# Todos los endpoints de trazabilidad exigen un JWT de acceso válido.
router = APIRouter(tags=["Trazabilidad"], dependencies=[Depends(require_jwt)])


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


@router.post(
    "/interactions/quiz-result",
    status_code=status.HTTP_201_CREATED,
    response_model=QuizResultResponse,
    responses={
        201: {"description": "Resultado del quiz registrado como interacción"},
        401: {"description": "No autorizado. JWT inválido o expirado."},
        422: {"description": "Datos inválidos (p.ej. correctas > total_preguntas)."},
        500: {"description": "Error interno del servidor."},
    },
)
async def registrar_quiz_result(
    body: QuizResultRequest,
    user: dict = Depends(require_jwt),
    uc: RegistrarQuizResultUseCase = Depends(get_registrar_quiz_result_uc),
) -> QuizResultResponse:
    """Registra el resultado de un quiz/práctica generado como interacción CALIFICADA.

    Cierra el loop de feedback del SAKT: la interacción entra al dataset de
    entrenamiento (``es_vista=False``, ``concept_id`` poblado). El
    ``estudiante_id`` se toma del JWT (claim ``sub``), nunca del body.

    **Auth:** JWT (estudiante)
    """
    guardada = await uc.execute(
        RegistrarQuizResultCommand(
            estudiante_id=UUID(user["sub"]),
            curso_id=body.curso_id,
            concepto=body.concepto,
            total_preguntas=body.total_preguntas,
            correctas=body.correctas,
            tipo_recurso=body.tipo_recurso,
        )
    )
    return QuizResultResponse(
        registrado=True,
        nota=guardada.nota if guardada.nota is not None else 0.0,
        is_correct=bool(guardada.is_correct),
    )


@router.post(
    "/interactions/material-completed",
    status_code=status.HTTP_201_CREATED,
    response_model=MaterialCompletadoResponse,
    responses={
        201: {"description": "Recurso completado registrado como interacción"},
        401: {"description": "No autorizado. JWT inválido o expirado."},
        422: {"description": "Datos inválidos (tipo desconocido)."},
        500: {"description": "Error interno del servidor."},
    },
)
async def registrar_material_completado(
    body: MaterialCompletadoRequest,
    user: dict = Depends(require_jwt),
    uc: RegistrarMaterialCompletadoUseCase = Depends(
        get_registrar_material_completado_uc
    ),
) -> MaterialCompletadoResponse:
    """Registra un recurso generado completado como interacción.

    - **práctica** → calificada (``es_vista=False``) → alimenta el SAKT.
    - **lectura / video** → vista (``es_vista=True``) → señal de preferencia.

    El ``estudiante_id`` se toma del JWT (claim ``sub``), nunca del body.

    **Auth:** JWT (estudiante)
    """
    guardada = await uc.execute(
        RegistrarMaterialCompletadoCommand(
            estudiante_id=UUID(user["sub"]),
            curso_id=body.curso_id,
            concepto=body.concepto,
            tipo=body.tipo,
            aprobado=body.aprobado,
        )
    )
    return MaterialCompletadoResponse(
        registrado=True,
        es_vista=bool(guardada.es_vista),
    )


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
            "tipo_recurso": i.tipo_recurso,
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


@router.get(
    "/students/{student_id}/streak",
    status_code=status.HTTP_200_OK,
    response_model=RachaResponse,
)
async def get_streak(
    student_id: UUID = Path(..., description="UUID del estudiante"),
    uc: ConsultarRachaUseCase = Depends(get_consultar_racha_uc),
):
    """Racha GLOBAL de días consecutivos con actividad (en todos los cursos).

    La racha de estudio no es por curso: cualquier interacción del alumno cuenta.
    Solo vive si el último día activo es hoy o ayer (hora de Perú).

    **Auth:** JWT
    """
    dias = await uc.execute(student_id)
    return {"dias_racha": dias}


@router.get(
    "/students/{student_id}/concept-mastery",
    status_code=status.HTTP_200_OK,
    response_model=list[ConceptoMasteryResponse],
)
async def get_concept_mastery(
    student_id: UUID = Path(..., description="UUID del estudiante"),
    courseId: UUID = Query(..., description="UUID del curso"),
    uc: ConsultarConceptoMasteryUseCase = Depends(get_consultar_concepto_mastery_uc),
):
    """Dominio real por concepto/sección del curso para un estudiante.

    Agrupa las interacciones por ``concept_id`` (sección de Moodle) y calcula la
    tasa de acierto. Alimenta el radar, las barras y las recomendaciones del
    detalle del estudiante. Orden: peores primero.
    """
    conceptos = await uc.execute(student_id, courseId)
    return [
        {
            "concepto": c.concepto,
            "dominio": c.dominio,
            "total": c.total,
            "correctas": c.correctas,
        }
        for c in conceptos
    ]


@router.get(
    "/dashboard/platform-activity",
    status_code=status.HTTP_200_OK,
    response_model=list[ActividadDiariaResponse],
)
async def platform_activity(
    days: int = Query(7, ge=1, le=30, description="Días hacia atrás a incluir"),
    courseId: UUID | None = Query(None, description="Filtra por curso (opcional)"),
    uc: ConsultarActividadPlataformaUseCase = Depends(
        get_consultar_actividad_plataforma_uc
    ),
):
    """Actividad real de la plataforma: # de interacciones por día (últimos N días).

    Alimenta el gráfico de actividad del panel de administración con datos
    reales. Los días sin actividad se devuelven en cero (serie continua).
    """
    puntos = await uc.execute(days, courseId)
    return [{"day": p.day, "sesiones": p.sesiones} for p in puntos]


@router.get(
    "/students/{student_id}/weekly-progress",
    status_code=status.HTTP_200_OK,
    response_model=list[EvolucionEtapaResponse],
)
async def get_weekly_progress(
    student_id: UUID = Path(..., description="UUID del estudiante"),
    courseId: UUID = Query(..., description="UUID del curso"),
    uc: ConsultarEvolucionEstudianteUseCase = Depends(
        get_consultar_evolucion_estudiante_uc
    ),
):
    """Evolución del dominio: dominio acumulado (running % de aciertos) a lo
    largo de la secuencia de actividades, en hasta 6 etapas.

    Se usa la secuencia (no semanas calendario) porque las notas de Moodle no
    traen fecha de envío fiable; así la curva refleja la evolución real.
    """
    puntos = await uc.execute(student_id, courseId)
    return [{"etapa": p.etapa, "dominio": p.dominio} for p in puntos]


@router.get("/students/{student_id}/preferences", status_code=status.HTTP_200_OK)
async def get_preferences(
    student_id: UUID = Path(..., description="UUID del estudiante"),
    courseId: UUID = Query(..., description="UUID del curso"),
    uc: ConsultarPreferenciasUseCase = Depends(get_consultar_preferencias_uc),
):
    """Preferencia de formato del estudiante (en qué tipo de recurso rinde mejor).

    **Auth:** JWT
    """
    return _serializar_preferencias(await uc.execute(student_id, courseId))


# Router interno: autenticación por service-key (sin JWT de usuario).
internal_router = APIRouter(
    tags=["LMS — Interno"], dependencies=[Depends(require_service_key)]
)


@internal_router.get("/internal/students/{student_id}/preferences")
async def get_preferences_internal(
    student_id: UUID = Path(..., description="UUID del estudiante"),
    courseId: UUID = Query(..., description="UUID del curso"),
    uc: ConsultarPreferenciasUseCase = Depends(get_consultar_preferencias_uc),
):
    """Gemelo interno de ``/students/{id}/preferences`` para consumo s2s.

    Lo usa ms-recomendacion para que el motor SAKT priorice el formato en el que
    el estudiante rinde/consume mejor.

    **Auth:** X-Service-Key
    """
    return _serializar_preferencias(await uc.execute(student_id, courseId))


@internal_router.post(
    "/internal/lms-sync", status_code=202, response_model=LmsSyncResponse
)
async def lms_sync(
    body: LmsSyncRequest,
    uc: SincronizarLmsUseCase = Depends(get_sincronizar_lms_uc),
):
    """Recibe interacciones desde ms-integracion-lms y las persiste.

    Convierte los IDs numéricos de Moodle a UUIDs determinísticos (uuid5) y
    realiza deduplicación por ``moodle_event_id``.

    **Auth:** X-Service-Key | **Idempotente:** sí (omite eventos ya procesados)
    """
    resultado = await uc.execute(
        SincronizarLmsCommand(
            interacciones=[
                LmsInteraccionDTO(
                    moodle_user_id=item.moodle_user_id,
                    moodle_course_id=item.moodle_course_id,
                    moodle_activity_id=item.moodle_activity_id,
                    fecha_evento=item.fecha_evento,
                    nombre=item.nombre,
                    correo=item.correo,
                    concepto=item.concepto,
                    es_correcta=item.es_correcta,
                    nota=item.nota,
                    url_modulo=item.url_modulo,
                    nombre_actividad=item.nombre_actividad,
                    tipo_recurso=item.tipo_recurso,
                    es_vista=item.es_vista,
                    moodle_event_id=item.moodle_event_id,
                )
                for item in body.interacciones
            ]
        )
    )
    return {"procesadas": resultado.procesadas, "omitidas": resultado.omitidas}


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


@internal_router.get(
    "/internal/metrics/platform",
    status_code=status.HTTP_200_OK,
    response_model=MetricasPlataformaResponse,
)
async def get_platform_metrics(
    uc: ConsultarMetricasPlataformaUseCase = Depends(
        get_consultar_metricas_plataforma_uc
    ),
):
    """Métricas agregadas de toda la plataforma (s2s, auth service-key).

    Usado por ms-usuarios para el KPI "Dominio Plataforma" del panel admin.
    Promedia ``puntaje_promedio`` sobre todos los progresos académicos.
    """
    m = await uc.execute()
    return {
        "dominio_promedio": m.dominio_promedio,
        "estudiantes_con_progreso": m.estudiantes_con_progreso,
    }


@internal_router.get(
    "/dashboard/training-data",
    status_code=status.HTTP_200_OK,
    response_model=list[TrainingRowResponse],
)
async def get_training_data(
    uc: ExportarTrainingDataUseCase = Depends(get_exportar_training_data_uc),
):
    """Dataset de entrenamiento para el modelo SAKT (knowledge tracing, s2s).

    Devuelve TODAS las interacciones calificadas (``es_vista = False``) con
    ``concept_id`` no vacío, ordenadas por estudiante y por fecha, en el formato
    que consume el pipeline de entrenamiento offline de ms-recomendacion. Puede
    ser un payload grande; es de uso batch/offline.

    **Auth:** X-Service-Key
    """
    # `tipo_recurso` habilita el SAKT format-aware (skill concepto×formato) y el
    # análisis pedagógico por formato; los pipelines viejos ignoran el campo extra.
    muestras = await uc.execute()
    return [
        {
            "estudiante_id": s.estudiante_id,
            "concepto": s.concepto,
            "correcta": s.correcta,
            "orden": s.orden,
            "tipo_recurso": s.tipo_recurso,
        }
        for s in muestras
    ]


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
    uc: ConsultarTendenciaEtapasUseCase = Depends(get_consultar_tendencia_etapas_uc),
) -> list[dict]:
    """Tendencia del curso: dominio promedio acumulado y nº de estudiantes en
    riesgo, a lo largo de la secuencia de actividades (hasta 6 etapas).

    Igual que la evolución por estudiante, se usa la SECUENCIA (no semanas
    calendario) porque las notas de Moodle no traen fecha de envío fiable y el
    historial de snapshots solo crece con el tiempo. Así la curva refleja datos
    reales desde la primera sincronización. **Auth:** JWT
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
    courseName: str | None = Query(
        None, max_length=200, description="Nombre legible del curso para la cabecera"
    ),
    uc: GenerarReporteDocenteUseCase = Depends(get_generar_reporte_docente_uc),
) -> StreamingResponse:
    """Genera y descarga el reporte de progreso de la clase en PDF.

    El PDF incluye cabecera SWARD, un resumen agregado por nivel de riesgo y el
    detalle por estudiante (nombre, correo, riesgo, dominio, interacciones).

    **Auth:** JWT | **Content-Type:** application/pdf
    """
    pdf = await uc.execute(course_id, curso_nombre=courseName)
    filename = f"reporte_clase_{course_id}.pdf"
    return StreamingResponse(
        BytesIO(pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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
