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

# Umbral de aprobación (mismo criterio binario que el resto del dominio).
UMBRAL_APROBACION = 60.0


@dataclass
class RegistrarQuizResultCommand:
    """Resultado de un quiz/práctica generado por el motor de recomendación.

    El ``estudiante_id`` proviene del JWT (claim ``sub``), nunca del body.
    """

    estudiante_id: UUID
    curso_id: UUID
    concepto: str
    total_preguntas: int
    correctas: int
    tipo_recurso: str = "quiz_generado"


class RegistrarQuizResultUseCase:
    """Registra el resultado de un quiz generado como interacción CALIFICADA.

    Cierra el loop de feedback del SAKT: la interacción se persiste con
    ``es_vista=False`` y ``concept_id`` poblado, por lo que entra al dataset de
    entrenamiento (``/dashboard/training-data`` filtra ``es_vista=False``).
    """

    def __init__(
        self, repo: TrazabilidadRepositoryPort, event_publisher: EventPublisherPort
    ):
        self._repo = repo
        self._event_publisher = event_publisher

    async def execute(self, cmd: RegistrarQuizResultCommand) -> InteraccionAcademica:
        nota = cmd.correctas / cmd.total_preguntas * 100
        is_correct = nota >= UMBRAL_APROBACION

        interaccion = InteraccionAcademica(
            estudiante_id=cmd.estudiante_id,
            curso_id=cmd.curso_id,
            tipo=TipoInteraccion.RESPUESTA,
            concept_id=cmd.concepto,
            is_correct=is_correct,
            nota=nota,
            es_vista=False,
            nombre_actividad=f"Quiz generado — {cmd.concepto}",
            tipo_recurso=cmd.tipo_recurso or "quiz_generado",
        )
        guardada = await self._repo.save_interaccion(interaccion)

        # Actualiza/crea el progreso del estudiante con esta nota (mismo patrón
        # que RegistrarInteraccionUseCase).
        progreso = await self._repo.find_progreso(cmd.estudiante_id, cmd.curso_id)
        if not progreso:
            progreso = ProgresoAcademico(
                estudiante_id=cmd.estudiante_id, curso_id=cmd.curso_id
            )
        progreso.actualizar(guardada)
        n = progreso.total_interacciones
        progreso.puntaje_promedio = ((progreso.puntaje_promedio * (n - 1)) + nota) / n
        progreso._recalcular_riesgo()
        await self._repo.save_progreso(progreso)

        self._event_publisher.publish(
            InteraccionRegistradaEvent(
                interaccion_id=guardada.id,
                estudiante_id=cmd.estudiante_id,
                curso_id=cmd.curso_id,
            )
        )
        if progreso.nivel_riesgo in (NivelRiesgo.ALTO, NivelRiesgo.CRITICO):
            self._event_publisher.publish(
                RiesgoActualizadoEvent(
                    estudiante_id=cmd.estudiante_id,
                    curso_id=cmd.curso_id,
                    nivel_riesgo=progreso.nivel_riesgo.value,
                )
            )
        return guardada
