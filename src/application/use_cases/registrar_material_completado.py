from dataclasses import dataclass
from uuid import UUID

from src.domain.entities.interaccion_academica import InteraccionAcademica
from src.domain.entities.progreso_academico import ProgresoAcademico
from src.domain.events.interaccion_registrada_event import InteraccionRegistradaEvent
from src.application.ports.out_.event_publisher_port import EventPublisherPort
from src.application.ports.out_.trazabilidad_repository_port import (
    TrazabilidadRepositoryPort,
)
from src.domain.value_objects.nivel_riesgo import TipoInteraccion

# Tipos de recurso generado que son "vistas" (señal de preferencia de formato, NO
# entran al knowledge-tracing); el resto (práctica) son calificados y SÍ entran.
TIPOS_VISTA = {"lectura", "video"}

_ETIQUETA = {
    "practica": "Práctica generada",
    "lectura": "Lectura generada",
    "video": "Video generado",
}
_TIPO_RECURSO = {
    "practica": "practica_generada",
    "lectura": "lectura_generada",
    "video": "video_generado",
}


@dataclass
class RegistrarMaterialCompletadoCommand:
    """Un recurso generado (práctica/lectura/video) que el estudiante completó.

    El ``estudiante_id`` proviene del JWT (claim ``sub``), nunca del body.
    """

    estudiante_id: UUID
    curso_id: UUID
    concepto: str
    tipo: str  # "practica" | "lectura" | "video"
    aprobado: bool = True  # solo aplica a práctica


class RegistrarMaterialCompletadoUseCase:
    """Registra como interacción cualquier recurso generado completado.

    - **práctica** → interacción CALIFICADA (``es_vista=False``, ``is_correct`` según
      la IA) → entra al dataset de entrenamiento del SAKT, igual que el quiz.
    - **lectura / video** → VISTA (``es_vista=True``) → no entra al knowledge-tracing,
      pero alimenta la señal de preferencia de formato del estudiante.
    """

    def __init__(
        self, repo: TrazabilidadRepositoryPort, event_publisher: EventPublisherPort
    ):
        self._repo = repo
        self._event_publisher = event_publisher

    async def execute(
        self, cmd: RegistrarMaterialCompletadoCommand
    ) -> InteraccionAcademica:
        es_vista = cmd.tipo in TIPOS_VISTA
        etiqueta = _ETIQUETA.get(cmd.tipo, "Recurso generado")
        tipo_recurso = _TIPO_RECURSO.get(cmd.tipo, f"{cmd.tipo}_generado")

        if es_vista:
            interaccion = InteraccionAcademica(
                estudiante_id=cmd.estudiante_id,
                curso_id=cmd.curso_id,
                tipo=TipoInteraccion.VISTA,
                concept_id=cmd.concepto,
                is_correct=True,
                es_vista=True,
                nombre_actividad=f"{etiqueta} — {cmd.concepto}",
                tipo_recurso=tipo_recurso,
            )
            guardada = await self._repo.save_interaccion(interaccion)
        else:
            # Práctica: calificada (aprobó la IA = dominó el ejercicio).
            nota = 100.0 if cmd.aprobado else 0.0
            interaccion = InteraccionAcademica(
                estudiante_id=cmd.estudiante_id,
                curso_id=cmd.curso_id,
                tipo=TipoInteraccion.RESPUESTA,
                concept_id=cmd.concepto,
                is_correct=cmd.aprobado,
                nota=nota,
                es_vista=False,
                nombre_actividad=f"{etiqueta} — {cmd.concepto}",
                tipo_recurso=tipo_recurso,
            )
            guardada = await self._repo.save_interaccion(interaccion)

            # Actualiza el progreso con la nota (mismo patrón que el quiz).
            progreso = await self._repo.find_progreso(cmd.estudiante_id, cmd.curso_id)
            if not progreso:
                progreso = ProgresoAcademico(
                    estudiante_id=cmd.estudiante_id, curso_id=cmd.curso_id
                )
            progreso.actualizar(guardada)
            n = progreso.total_interacciones
            progreso.puntaje_promedio = (
                (progreso.puntaje_promedio * (n - 1)) + nota
            ) / n
            progreso._recalcular_riesgo()
            await self._repo.save_progreso(progreso)

        self._event_publisher.publish(
            InteraccionRegistradaEvent(
                interaccion_id=guardada.id,
                estudiante_id=cmd.estudiante_id,
                curso_id=cmd.curso_id,
            )
        )
        return guardada
