# sward-ms-trazabilidad

Microservicio de trazabilidad académica del sistema **SWARD**.  
Registra interacciones de aprendizaje, calcula el progreso académico y genera métricas de desempeño para estudiantes y docentes.

## Arquitectura

Arquitectura **Hexagonal (Ports & Adapters)**:

```
src/
  domain/           # InteraccionAcademica, RespuestaActividad, ProgresoAcademico, IndicadorTrazabilidad
  application/      # RegistrarInteraccionUseCase, ConsultarProgresoUseCase, CalcularIndicadoresUseCase
  infrastructure/   # FastAPI routers, TrazabilidadPostgresAdapter, IntegracionLmsRestAdapter
```

## Stack

- Python 3.11 · FastAPI · SQLAlchemy 2.0 · Alembic · PostgreSQL
- httpx · Pydantic v2 · boto3 (EventBridge)

## Desarrollo local

```bash
cp .env.example .env
docker compose up -d db
alembic upgrade head
uvicorn src.infrastructure.adapters.in_.main:app --reload --port 8003
```

## Tests

```bash
pytest tests/ -v --cov=src
```

## Endpoints principales

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/interactions` | Registrar interacción académica |
| GET | `/students/{id}/progress` | Progreso por curso |
| GET | `/students/{id}/indicators` | Indicadores de trazabilidad |
| GET | `/students/{id}/interactions` | Historial de interacciones |
| GET | `/dashboard/teacher/{cursoId}/students-progress` | Dashboard docente |

## Proyecto

**TP202610051** — Universidad Peruana de Ciencias Aplicadas (UPC)  
Taller de Proyecto 1 / 2026
