from dataclasses import dataclass
from uuid import UUID

from src.domain.entities.progreso_academico import ProgresoAcademico
from src.domain.ports.out_.trazabilidad_repository_port import (
    TrazabilidadRepositoryPort,
)
from src.domain.ports.out_.usuarios_client_port import UsuariosClientPort
from src.domain.value_objects.nivel_riesgo import NivelRiesgo


@dataclass
class EstudianteDashboard:
    """Progreso académico de un estudiante enriquecido con sus datos de perfil."""

    progreso: ProgresoAcademico
    nombre: str = ""
    apellido: str = ""
    correo: str = ""


class ConsultarDashboardDocenteUseCase:
    def __init__(
        self,
        repo: TrazabilidadRepositoryPort,
        usuarios_client: UsuariosClientPort,
    ):
        self._repo = repo
        self._usuarios = usuarios_client

    async def execute(self, curso_id: UUID) -> list[EstudianteDashboard]:
        progresos = await self._repo.find_all_progreso_curso(curso_id)
        # Ordenar por nivel de riesgo descendente (crítico primero)
        orden = {
            NivelRiesgo.CRITICO: 0,
            NivelRiesgo.ALTO: 1,
            NivelRiesgo.MEDIO: 2,
            NivelRiesgo.BAJO: 3,
        }
        progresos = sorted(progresos, key=lambda p: orden.get(p.nivel_riesgo, 4))

        # Enriquecer con nombre/correo vía s2s a ms-usuarios (una sola llamada).
        perfiles = await self._usuarios.obtener_perfiles(
            [p.estudiante_id for p in progresos]
        )
        return [
            EstudianteDashboard(
                progreso=p,
                nombre=perfiles.get(str(p.estudiante_id), {}).get("nombre", ""),
                apellido=perfiles.get(str(p.estudiante_id), {}).get("apellido", ""),
                correo=perfiles.get(str(p.estudiante_id), {}).get("correo", ""),
            )
            for p in progresos
        ]
