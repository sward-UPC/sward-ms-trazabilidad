import httpx
from uuid import UUID

from src.domain.ports.out_.usuarios_client_port import UsuariosClientPort
from src.infrastructure.config.settings import settings


def _service_headers() -> dict[str, str]:
    return {"X-Service-Key": settings.service_key} if settings.service_key else {}


class UsuariosRestAdapter(UsuariosClientPort):
    """Cliente s2s hacia ms-usuarios para enriquecer respuestas con datos de perfil.

    En desarrollo no hace red (retorna mapa vacío), igual que LmsRestAdapter.
    """

    async def obtener_perfiles(self, ids: list[UUID]) -> dict[str, dict]:
        if settings.environment == "development" or not ids:
            return {}
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                f"{settings.usuarios_service_url}/internal/users/by-ids",
                json={"ids": [str(i) for i in ids]},
                headers=_service_headers(),
            )
            if r.status_code != 200:
                return {}
            return {u["id"]: u for u in r.json()}
