from uuid import UUID

import httpx

from src.application.ports.out_.cursos_client_port import (
    AsignacionNoDisponibleError,
    CursosClientPort,
)
from src.infrastructure.config.settings import settings


class CursosRestAdapter(CursosClientPort):
    """Pregunta a ms-cursos-recursos quién dicta un curso.

    La asignación es la columna ``docente_id`` del curso, que pone el
    administrador. ``GET /courses/{id}`` solo acepta el JWT de un usuario —no hay
    ruta interna con service-key para leer cursos—, así que se reenvía el token
    de quien hizo la petición, que ya se validó aquí.

    A diferencia de los otros adaptadores, en desarrollo no devuelve nada
    simulado: inventar una asignación abriría o cerraría la puerta a ciegas, y
    ``ENVIRONMENT`` vale «development» por defecto. Sin ms-cursos-recursos el
    docente recibe un 503; el administrador no depende de esta consulta.
    """

    async def docente_del_curso(self, curso_id: UUID, token: str) -> UUID | None:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(
                    f"{settings.cursos_service_url}/courses/{curso_id}",
                    headers={"Authorization": f"Bearer {token}"},
                )
        except httpx.HTTPError as exc:
            raise AsignacionNoDisponibleError(
                f"ms-cursos-recursos no respondió: {type(exc).__name__}"
            ) from exc
        if r.status_code == 404:
            return None
        if r.status_code != 200:
            raise AsignacionNoDisponibleError(
                f"ms-cursos-recursos respondió HTTP {r.status_code}"
            )
        try:
            docente_id = r.json().get("docente_id")
            return UUID(str(docente_id)) if docente_id else None
        except (ValueError, TypeError, AttributeError) as exc:
            raise AsignacionNoDisponibleError(
                "ms-cursos-recursos devolvió un curso que no se entiende"
            ) from exc
