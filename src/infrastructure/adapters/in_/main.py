import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from scalar_fastapi import get_scalar_api_reference
from sqlalchemy import text

from src.infrastructure.adapters.in_.trazabilidad_router import internal_router, router
from src.infrastructure.config.settings import settings
from src.infrastructure.db.database import engine
from src.infrastructure.db.models.trazabilidad_models import Base

logger = logging.getLogger(__name__)

# Columnas nuevas en tablas existentes (create_all no las agrega). Idempotente.
_MIGRACIONES = [
    "ALTER TABLE interactions ADD COLUMN IF NOT EXISTS concept_id VARCHAR(255)",
    "ALTER TABLE interactions ADD COLUMN IF NOT EXISTS is_correct BOOLEAN",
    "ALTER TABLE interactions ADD COLUMN IF NOT EXISTS nota DOUBLE PRECISION",
    "ALTER TABLE academic_progress ADD COLUMN IF NOT EXISTS nombre VARCHAR(255) NOT NULL DEFAULT ''",
    "ALTER TABLE academic_progress ADD COLUMN IF NOT EXISTS correo VARCHAR(255) NOT NULL DEFAULT ''",
]


async def _init_db() -> None:
    for intento in range(10):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                for stmt in _MIGRACIONES:
                    await conn.execute(text(stmt))
            logger.info("Base de datos lista.")
            return
        except Exception as exc:
            logger.warning("BD no disponible (intento %d/10): %s", intento + 1, exc)
            await asyncio.sleep(5)
    logger.error("No se pudo conectar a la BD tras 10 intentos.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(_init_db())
    yield
    await engine.dispose()


app = FastAPI(
    title="SWARD — Microservicio de Trazabilidad",
    version="0.1.0",
    openapi_url="/interactions/openapi.json",
    description=(
        "Registra y consulta la trazabilidad de eventos de aprendizaje de los "
        "estudiantes para auditoría y análisis dentro de SWARD."
    ),
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "Trazabilidad",
            "description": "Registro y consulta de eventos de trazabilidad de aprendizaje.",
        },
        {"name": "Health", "description": "Sonda de estado del servicio."},
    ],
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Service-Key"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    if not settings.is_development:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception(
        "Error interno no controlado en %s %s", request.method, request.url.path
    )
    return JSONResponse(
        status_code=500, content={"detail": "Error interno del servidor."}
    )


app.include_router(router)
app.include_router(internal_router)


@app.get("/scalar", include_in_schema=False)
async def scalar_docs():
    """Renderiza la referencia de API interactiva (Scalar) del servicio."""
    return get_scalar_api_reference(openapi_url=app.openapi_url, title=app.title)


@app.get("/health", tags=["Health"], summary="Estado del servicio")
async def health():
    """Devuelve el estado de salud del microservicio para sondas de liveness/readiness."""
    return {"status": "ok", "service": settings.service_name}
