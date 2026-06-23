from dataclasses import dataclass

from src.domain.ports.out_.trazabilidad_repository_port import (
    TrazabilidadRepositoryPort,
)


@dataclass
class TrainingSample:
    estudiante_id: str
    concepto: str
    correcta: bool
    orden: str
    tipo_recurso: str


class ExportarTrainingDataUseCase:
    """Dataset de entrenamiento para el modelo SAKT (knowledge tracing).

    Devuelve las interacciones calificadas con concepto, ordenadas por estudiante
    y fecha, en el formato que consume el pipeline de entrenamiento offline.
    """

    def __init__(self, repo: TrazabilidadRepositoryPort):
        self._repo = repo

    async def execute(self) -> list[TrainingSample]:
        filas = await self._repo.training_data()
        return [
            TrainingSample(
                estudiante_id=str(f.estudiante_id),
                concepto=f.concepto,
                correcta=f.correcta,
                orden=f.fecha.isoformat(),
                tipo_recurso=f.tipo_recurso,
            )
            for f in filas
        ]
