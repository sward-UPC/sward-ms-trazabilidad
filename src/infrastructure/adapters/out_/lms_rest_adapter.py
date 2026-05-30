import httpx
from src.domain.ports.out_.lms_client_port import LmsClientPort
from src.infrastructure.config.settings import settings


def _service_headers() -> dict[str, str]:
    return {"X-Service-Key": settings.service_key} if settings.service_key else {}


class LmsRestAdapter(LmsClientPort):
    async def obtener_interacciones(self, curso_id=None, user_id=None) -> list[dict]:
        if settings.environment == "development":
            return []
        params = {}
        if curso_id:
            params["courseId"] = curso_id
        if user_id:
            params["userId"] = user_id
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"{settings.lms_service_url}/lms/interactions",
                params=params,
                headers=_service_headers(),
            )
            return r.json() if r.status_code == 200 else []

    async def obtener_calificaciones(self, curso_id=None, user_id=None) -> list[dict]:
        if settings.environment == "development":
            return []
        params = {}
        if curso_id:
            params["courseId"] = curso_id
        if user_id:
            params["userId"] = user_id
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(
                f"{settings.lms_service_url}/lms/grades",
                params=params,
                headers=_service_headers(),
            )
            return r.json() if r.status_code == 200 else []
