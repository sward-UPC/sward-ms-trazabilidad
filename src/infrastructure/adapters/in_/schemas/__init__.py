"""Contratos Pydantic (Request/Response) del adaptador de entrada HTTP.

Organizados por concern (interacciones, progreso, lms, feedback) en vez de un
único archivo, según buenas prácticas de organización. Se re-exportan aquí para
que las rutas importen desde `...adapters.in_.schemas` sin conocer el submódulo.
"""

from .feedback import FeedbackRequest, FeedbackResponse
from .interacciones import (
    InteraccionRequest,
    InteraccionResponse,
    MaterialCompletadoRequest,
    MaterialCompletadoResponse,
    QuizResultRequest,
    QuizResultResponse,
)
from .lms import (
    LmsInteraccionItem,
    LmsSyncRequest,
    LmsSyncResponse,
    TrainingRowResponse,
)
from .plataforma import ActividadDiariaResponse, MetricasPlataformaResponse
from .progreso import (
    ConceptoMasteryResponse,
    EstudianteProgressResponse,
    EvolucionEtapaResponse,
    IndicadorResponse,
    ProgresoResponse,
    RachaResponse,
    TendenciaResponse,
)

__all__ = [
    "InteraccionRequest",
    "InteraccionResponse",
    "QuizResultRequest",
    "QuizResultResponse",
    "MaterialCompletadoRequest",
    "MaterialCompletadoResponse",
    "ProgresoResponse",
    "IndicadorResponse",
    "EstudianteProgressResponse",
    "TendenciaResponse",
    "RachaResponse",
    "ConceptoMasteryResponse",
    "EvolucionEtapaResponse",
    "ActividadDiariaResponse",
    "MetricasPlataformaResponse",
    "LmsInteraccionItem",
    "LmsSyncRequest",
    "LmsSyncResponse",
    "TrainingRowResponse",
    "FeedbackRequest",
    "FeedbackResponse",
]
