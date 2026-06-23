from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sward_shared.identidad import moodle_uuid as _moodle_id

from src.application.ports.out_.trazabilidad_repository_port import (
    InteraccionLms,
    ProgresoRecomputado,
    TrazabilidadRepositoryPort,
)
from src.domain.value_objects.nivel_riesgo import NivelRiesgo


@dataclass
class LmsInteraccionDTO:
    """Una interacción cruda recibida desde ms-integracion-lms."""

    moodle_user_id: str
    moodle_course_id: str
    moodle_activity_id: str
    fecha_evento: datetime
    nombre: str = ""
    correo: str = ""
    concepto: str = ""
    es_correcta: bool = False
    nota: float = 0.0
    url_modulo: str = ""
    nombre_actividad: str = ""
    tipo_recurso: str = ""
    es_vista: bool = False
    moodle_event_id: str = ""


@dataclass
class SincronizarLmsCommand:
    interacciones: list[LmsInteraccionDTO]


@dataclass
class SincronizarLmsResult:
    procesadas: int
    omitidas: int


class SincronizarLmsUseCase:
    """Persiste interacciones provenientes del LMS y recomputa el progreso.

    Orquestación pura: convierte los IDs numéricos de Moodle a UUIDs
    determinísticos, delega la persistencia/deduplicación al repositorio y
    recalcula el nivel de riesgo usando la regla única del dominio
    (``NivelRiesgo.por_puntaje``). No ejecuta SQL.
    """

    def __init__(self, repo: TrazabilidadRepositoryPort):
        self._repo = repo

    async def execute(self, cmd: SincronizarLmsCommand) -> SincronizarLmsResult:
        procesadas = 0
        omitidas = 0
        # (estudiante_id, curso_id) afectados -> para recomputar su progreso.
        afectados: set[tuple[UUID, UUID]] = set()
        # estudiante_id -> (nombre, correo) más reciente visto en este lote.
        perfiles: dict[UUID, tuple[str, str]] = {}

        for item in cmd.interacciones:
            est_id = _moodle_id("user", item.moodle_user_id)
            cur_id = _moodle_id("course", item.moodle_course_id)
            act_id = _moodle_id("activity", item.moodle_activity_id)
            afectados.add((est_id, cur_id))
            if item.nombre or item.correo:
                perfiles[est_id] = (item.nombre, item.correo)

            es_nueva = await self._repo.upsert_interaccion_lms(
                InteraccionLms(
                    estudiante_id=est_id,
                    curso_id=cur_id,
                    actividad_id=act_id,
                    concepto=item.concepto,
                    es_correcta=item.es_correcta,
                    nota=item.nota,
                    url_modulo=item.url_modulo,
                    nombre_actividad=item.nombre_actividad,
                    tipo_recurso=item.tipo_recurso,
                    es_vista=item.es_vista,
                    fecha_evento=item.fecha_evento,
                    moodle_event_id=item.moodle_event_id,
                )
            )
            if es_nueva:
                procesadas += 1
            else:
                omitidas += 1

        # Persiste las interacciones para poder agregarlas (mismo commit).
        await self._repo.flush_interacciones_lms()

        for est_id, cur_id in afectados:
            agg = await self._repo.agregar_metricas_estudiante(est_id, cur_id)
            if agg is None or agg.total == 0:
                continue
            # Dominio = promedio de la nota real (continuo). Si no hay notas, cae al
            # % de aciertos para no romper datos antiguos.
            puntaje = (
                round(agg.promedio_nota, 1)
                if agg.promedio_nota is not None
                else round(agg.correctas / agg.total * 100, 1)
            )
            riesgo = NivelRiesgo.por_puntaje(puntaje, agg.total)
            nombre, correo = perfiles.get(est_id, ("", ""))
            await self._repo.recomputar_progreso_lms(
                ProgresoRecomputado(
                    estudiante_id=est_id,
                    curso_id=cur_id,
                    total_interacciones=agg.total,
                    recursos_completados=agg.correctas,
                    puntaje=puntaje,
                    nivel_riesgo=riesgo,
                    ultima_actividad=agg.ultima_actividad,
                    nombre=nombre,
                    correo=correo,
                )
            )

        await self._repo.commit_lms_sync()
        return SincronizarLmsResult(procesadas=procesadas, omitidas=omitidas)
