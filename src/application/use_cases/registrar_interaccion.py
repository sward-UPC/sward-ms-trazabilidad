import uuid
from dataclasses import dataclass
from uuid import UUID
from src.application.use_cases.consultar_racha import ConsultarRachaUseCase
from src.domain.entities.interaccion_academica import InteraccionAcademica
from src.domain.entities.progreso_academico import ProgresoAcademico
from src.domain.events.interaccion_registrada_event import InteraccionRegistradaEvent
from src.domain.events.logro_desbloqueado_event import LogroDesbloqueadoEvent
from src.domain.events.riesgo_actualizado_event import RiesgoActualizadoEvent
from src.domain.ports.out_.event_publisher_port import EventPublisherPort
from src.domain.ports.out_.trazabilidad_repository_port import (
    TrazabilidadRepositoryPort,
)
from src.domain.value_objects.nivel_riesgo import NivelRiesgo, TipoInteraccion

# Hitos que disparan una notificación de logro al alumno.
HITOS_RACHA = {3, 7, 14, 30}
HITOS_RECURSOS = {5, 10, 20, 50}


@dataclass
class RegistrarInteraccionCommand:
    estudiante_id: UUID
    curso_id: UUID
    tipo: TipoInteraccion = TipoInteraccion.VISTA
    actividad_id: UUID | None = None
    recurso_id: UUID | None = None
    puntaje: float | None = None
    moodle_event_id: str = ""


class RegistrarInteraccionUseCase:
    def __init__(
        self, repo: TrazabilidadRepositoryPort, event_publisher: EventPublisherPort
    ):
        self._repo = repo
        self._event_publisher = event_publisher

    async def execute(self, cmd: RegistrarInteraccionCommand) -> InteraccionAcademica:
        interaccion = InteraccionAcademica(
            estudiante_id=cmd.estudiante_id,
            curso_id=cmd.curso_id,
            tipo=cmd.tipo,
            actividad_id=cmd.actividad_id,
            recurso_id=cmd.recurso_id,
            moodle_event_id=cmd.moodle_event_id,
        )
        guardada = await self._repo.save_interaccion(interaccion)

        # Actualizar o crear progreso
        progreso = await self._repo.find_progreso(cmd.estudiante_id, cmd.curso_id)
        if not progreso:
            progreso = ProgresoAcademico(
                estudiante_id=cmd.estudiante_id, curso_id=cmd.curso_id
            )
        progreso.actualizar(guardada)
        if cmd.puntaje is not None:
            n = progreso.total_interacciones
            progreso.puntaje_promedio = (
                (progreso.puntaje_promedio * (n - 1)) + cmd.puntaje
            ) / n
            progreso._recalcular_riesgo()
        if cmd.tipo == TipoInteraccion.COMPLETADO:
            progreso.recursos_completados += 1
        await self._repo.save_progreso(progreso)

        self._event_publisher.publish(
            InteraccionRegistradaEvent(
                interaccion_id=guardada.id,
                estudiante_id=cmd.estudiante_id,
                curso_id=cmd.curso_id,
            )
        )

        # Logros del alumno (solo al completar un recurso, para no recalcular en
        # cada vista). Idempotente vía event_id determinístico (1 noti por hito).
        if cmd.tipo == TipoInteraccion.COMPLETADO:
            await self._publicar_logros(
                cmd.estudiante_id, progreso.recursos_completados
            )

        # Dispara la generación de alerta docente (vía lambda-alertas) sin depender
        # del motor de recomendación, cuando el riesgo es alto o crítico.
        if progreso.nivel_riesgo in (NivelRiesgo.ALTO, NivelRiesgo.CRITICO):
            self._event_publisher.publish(
                RiesgoActualizadoEvent(
                    estudiante_id=cmd.estudiante_id,
                    curso_id=cmd.curso_id,
                    nivel_riesgo=progreso.nivel_riesgo.value,
                )
            )
        return guardada

    async def _publicar_logros(
        self, estudiante_id: UUID, recursos_completados: int
    ) -> None:
        """Publica LogroDesbloqueado si se alcanzó un hito de racha o de recursos."""
        # Recursos completados (por curso) — exacto cuando cruza el hito.
        if recursos_completados in HITOS_RECURSOS:
            self._publicar_logro(estudiante_id, "recursos", recursos_completados)

        # Racha global de días consecutivos.
        racha = await ConsultarRachaUseCase(self._repo).execute(estudiante_id)
        if racha in HITOS_RACHA:
            self._publicar_logro(estudiante_id, "racha", racha)

    def _publicar_logro(self, estudiante_id: UUID, tipo: str, valor: int) -> None:
        # event_id determinístico → el mismo hito notifica una sola vez.
        event_id = uuid.uuid5(
            uuid.NAMESPACE_URL, f"logro-{estudiante_id}-{tipo}-{valor}"
        )
        self._event_publisher.publish(
            LogroDesbloqueadoEvent(
                event_id=event_id,
                estudiante_id=estudiante_id,
                tipo=tipo,
                valor=valor,
            )
        )
