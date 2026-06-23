from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from src.domain.entities.progreso_academico import ProgresoAcademico
from src.application.ports.out_.trazabilidad_repository_port import (
    TrazabilidadRepositoryPort,
)
from src.application.ports.out_.usuarios_client_port import UsuariosClientPort
from src.domain.value_objects.nivel_riesgo import NivelRiesgo

# Ventana e intensidad del índice de engagement (interacciones recientes).
_ENGAGEMENT_DIAS = 30
_ENGAGEMENT_FACTOR = 5  # engagement = min(100, interacciones_30d * 5)


@dataclass
class EstudianteDashboard:
    """Progreso académico de un estudiante enriquecido con sus datos de perfil."""

    progreso: ProgresoAcademico
    nombre: str = ""
    apellido: str = ""
    correo: str = ""
    engagement: int = 0
    conceptos_en_riesgo: int = 0
    # True si el estudiante tiene cuenta en SWARD; False si solo existe en Moodle.
    registrado_en_sward: bool = False


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
        # Engagement = actividad reciente (interacciones de los últimos 30 días).
        desde = datetime.now(timezone.utc) - timedelta(days=_ENGAGEMENT_DIAS)
        recientes = await self._repo.contar_interacciones_recientes(curso_id, desde)
        # Conceptos (secciones) donde el estudiante tiene baja tasa de acierto.
        en_riesgo = await self._repo.contar_conceptos_en_riesgo(curso_id)

        def _datos(p):
            """Nombre/correo del perfil SWARD si está registrado; si no, los de
            Moodle guardados en el progreso. Devuelve (nombre, apellido, correo,
            registrado)."""
            perfil = perfiles.get(str(p.estudiante_id))
            if perfil:
                # `or ""` por si el perfil trae el campo en None (no solo ausente).
                return (
                    perfil.get("nombre") or "",
                    perfil.get("apellido") or "",
                    perfil.get("correo") or "",
                    True,
                )
            # Solo en Moodle: el nombre viene completo (fullname) en p.nombre.
            return (p.nombre or "", "", p.correo or "", False)

        resultado = []
        for p in progresos:
            nombre, apellido, correo, registrado = _datos(p)
            resultado.append(
                EstudianteDashboard(
                    progreso=p,
                    nombre=nombre,
                    apellido=apellido,
                    correo=correo,
                    engagement=min(
                        100, recientes.get(str(p.estudiante_id), 0) * _ENGAGEMENT_FACTOR
                    ),
                    conceptos_en_riesgo=en_riesgo.get(str(p.estudiante_id), 0),
                    registrado_en_sward=registrado,
                )
            )
        return resultado
