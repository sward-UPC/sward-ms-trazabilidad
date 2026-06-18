from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.application.use_cases.generar_reporte_docente import ReporteClase


class ReporteRendererPort(ABC):
    @abstractmethod
    def render(self, reporte: "ReporteClase") -> bytes:
        """Renderiza el reporte de clase a bytes (p.ej. un PDF)."""
        ...
