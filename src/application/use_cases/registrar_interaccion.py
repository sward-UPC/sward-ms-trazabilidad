from dataclasses import dataclass
from uuid import UUID
from src.domain.entities.interaccion_academica import InteraccionAcademica
from src.domain.entities.progreso_academico import ProgresoAcademico
from src.domain.events.interaccion_registrada_event import InteraccionRegistradaEvent
from src.domain.events.riesgo_actualizado_event import RiesgoActualizadoEvent
from src.domain.ports.out_.event_publisher_port import EventPublisherPort
from src.domain.ports.out_.trazabilidad_repository_port import (
    TrazabilidadRepositoryPort,
)
from src.domain.value_objects.nivel_riesgo import NivelRiesgo, TipoInteraccion


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
