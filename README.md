# sward-ms-trazabilidad

Microservicio de **trazabilidad académica** del sistema **SWARD**. Construido con
FastAPI siguiendo arquitectura **Hexagonal (Ports & Adapters)**.

## Qué hace

Es la fuente de verdad del comportamiento de aprendizaje de cada estudiante. Sus
responsabilidades:

- **Registrar interacciones académicas** (vistas, prácticas, quizzes, recursos
  completados), tanto desde el frontend como sincronizadas desde Moodle vía
  `ms-integracion-lms`.
- **Calcular progreso y nivel de riesgo** por estudiante/curso (dominio continuo a
  partir de las notas reales) y mantener indicadores de desempeño.
- **Servir el dashboard docente**: progreso por estudiante, engagement, conceptos en
  riesgo, tendencia histórica de la clase, reporte PDF y retroalimentación docente→alumno.
- **Exponer el training-data del SAKT** (knowledge tracing) y las **preferencias de
  formato** del estudiante para el motor de recomendación (`ms-recomendacion`).
- **Publicar eventos de dominio** (interacción registrada, riesgo actualizado, logro
  desbloqueado, feedback) a EventBridge, que alimentan alertas y notificaciones.

## Stack

- **Python 3.11** · **FastAPI** · **Pydantic v2** / pydantic-settings
- **SQLAlchemy 2.0** (async) · **asyncpg** · **PostgreSQL 15**
- **boto3** (Amazon EventBridge) · **httpx** (clientes REST s2s)
- **reportlab** (reporte PDF docente) · **scalar-fastapi** (docs interactivas)
- **sward-shared** (auth JWT/service-key, publisher EventBridge, identidad Moodle→UUID)
- Tests: **pytest** + pytest-asyncio · Lint: **ruff**

## Estructura hexagonal

```
src/
├── domain/                              # Núcleo. Sin dependencias de frameworks.
│   ├── entities/
│   │   ├── interaccion_academica.py     # InteraccionAcademica, RespuestaActividad
│   │   ├── progreso_academico.py        # ProgresoAcademico, IndicadorTrazabilidad, ProgresoHistorial
│   │   └── feedback_docente.py          # FeedbackDocente
│   ├── value_objects/
│   │   └── nivel_riesgo.py              # NivelRiesgo, TipoInteraccion (StrEnum)
│   ├── events/                          # Eventos de dominio
│   │   ├── interaccion_registrada_event.py
│   │   ├── riesgo_actualizado_event.py
│   │   ├── logro_desbloqueado_event.py
│   │   └── feedback_registrado_event.py
│   └── ports/out_/                      # Contratos (ABC) que el núcleo necesita
│       ├── trazabilidad_repository_port.py
│       ├── event_publisher_port.py
│       ├── lms_client_port.py
│       ├── usuarios_client_port.py
│       └── reporte_renderer_port.py
│
├── application/use_cases/               # Casos de uso (orquestación)
│   ├── registrar_interaccion.py
│   ├── registrar_quiz_result.py
│   ├── registrar_material_completado.py
│   ├── consultar_progreso.py
│   ├── calcular_indicadores.py
│   ├── consultar_racha.py
│   ├── consultar_tendencia.py
│   ├── consultar_dashboard_docente.py
│   ├── generar_reporte_docente.py
│   └── registrar_feedback.py
│
└── infrastructure/
    ├── adapters/
    │   ├── in_/                         # Adaptadores de ENTRADA (FastAPI)
    │   │   ├── main.py                  # App, lifespan, CORS, security headers, /health
    │   │   └── trazabilidad_router.py   # Endpoints públicos (JWT) e internos (service-key)
    │   └── out_/                        # Adaptadores de SALIDA (implementan los ports)
    │       ├── trazabilidad_postgres_adapter.py
    │       ├── eventbridge_adapter.py
    │       ├── lms_rest_adapter.py
    │       ├── usuarios_rest_adapter.py
    │       └── pdf_reporte_renderer.py
    ├── config/
    │   └── settings.py                  # Pydantic Settings (env / Secrets Manager)
    ├── db/
    │   ├── database.py                  # Engine async + get_session
    │   └── models/trazabilidad_models.py # Modelos ORM SQLAlchemy
    └── dependencies.py                  # Composition root (Depends → use cases/adaptadores)
```

**Regla de dependencia:** `domain/` y `application/` no importan FastAPI, SQLAlchemy ni
boto3. Esos imports viven solo en `infrastructure/`. Las implementaciones concretas se
cablean únicamente en `infrastructure/dependencies.py`.

## Endpoints principales

Todas las rutas públicas exigen **JWT** (emitido por `ms-usuarios`, HS256). Las rutas
`/internal/*` y `/dashboard/training-data` usan **service-key** (`X-Service-Key`, s2s).

### Registro de interacciones
| Método | Ruta | Descripción |
|---|---|---|
| POST | `/interactions` | Registrar interacción académica |
| POST | `/interactions/quiz-result` | Resultado de quiz generado → calificada (alimenta SAKT) |
| POST | `/interactions/material-completed` | Recurso completado (práctica/lectura/video) |

### Consulta de estudiante
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/students/{id}/progress?courseId=` | Progreso y nivel de riesgo por curso |
| GET | `/students/{id}/indicators?courseId=` | Indicadores de desempeño |
| GET | `/students/{id}/interactions` | Historial de interacciones |
| GET | `/students/{id}/streak` | Racha global de días consecutivos activos |
| GET | `/students/{id}/concept-mastery?courseId=` | Dominio por concepto/sección |
| GET | `/students/{id}/weekly-progress?courseId=` | Evolución del dominio por etapas |
| GET | `/students/{id}/preferences?courseId=` | Preferencia de formato (en qué rinde mejor) |

### Dashboard docente
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/dashboard/teacher/{courseId}/students-progress` | Progreso de todos los alumnos (riesgo, engagement, conceptos en riesgo) |
| GET | `/dashboard/teacher/{courseId}/trend` | Tendencia histórica de la clase |
| GET | `/dashboard/teacher/{courseId}/report?courseName=` | Reporte PDF de la clase |
| POST | `/dashboard/teacher/feedback` | Retroalimentación docente → estudiante |
| GET | `/dashboard/platform-activity?days=&courseId=` | Actividad de la plataforma por día |

### Internos (service-key, s2s)
| Método | Ruta | Consumidor | Descripción |
|---|---|---|---|
| POST | `/internal/lms-sync` | ms-integracion-lms | Ingesta idempotente de interacciones de Moodle |
| GET | `/internal/students/{id}/interactions` | ms-recomendacion | Secuencia para el SAKT |
| GET | `/internal/students/{id}/preferences?courseId=` | ms-recomendacion | Preferencia de formato (s2s) |
| GET | `/internal/metrics/platform` | ms-usuarios | KPI "Dominio Plataforma" (panel admin) |
| GET | `/dashboard/training-data` | ms-recomendacion | Dataset de entrenamiento offline del SAKT |

### Operación
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Liveness/readiness |
| GET | `/scalar` | Referencia de API interactiva (Scalar) |
| GET | `/interactions/openapi.json` | Esquema OpenAPI |

## Eventos que publica (EventBridge)

Publicados por la **capa de aplicación** vía `EventPublisherPort` (el dominio no conoce
EventBridge). En `ENVIRONMENT=development` solo se loguean.

| Evento | `event_type` | Disparador |
|---|---|---|
| `InteraccionRegistradaEvent` | `sward.trazabilidad.InteraccionRegistrada` | Al registrar cualquier interacción |
| `RiesgoActualizadoEvent` | `sward.trazabilidad.RiesgoActualizado` | Progreso en riesgo alto/crítico (→ lambda-alertas) |
| `LogroDesbloqueadoEvent` | `sward.trazabilidad.LogroDesbloqueado` | Hito de racha (3/7/14/30) o recursos (5/10/20/50); idempotente |
| `FeedbackRegistradoEvent` | `sward.trazabilidad.FeedbackRegistrado` | Retroalimentación docente (→ notificación al alumno) |

## Variables de entorno

Ver `.env.example`. Principales:

| Variable | Default | Descripción |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://sward:sward@localhost:5432/trazabilidad_db` | Conexión Postgres async |
| `DB_USERNAME` / `DB_PASSWORD` / `DATABASE_HOST` / `DATABASE_PORT` / `DATABASE_NAME` | — | Componentes inyectados por ECS/Secrets Manager; si están, recomponen `DATABASE_URL` |
| `LMS_SERVICE_URL` | `http://localhost:8002` | URL de ms-integracion-lms |
| `USUARIOS_SERVICE_URL` | `http://usuarios.sward.local:8000` | URL de ms-usuarios |
| `AWS_REGION` | `us-east-1` | Región AWS |
| `EVENTBRIDGE_BUS_NAME` | `sward-event-bus` | Event bus destino |
| `ENVIRONMENT` | `development` | `development` no publica a EventBridge ni exige secretos |
| `CORS_ALLOWED_ORIGINS` | `["http://localhost:5173"]` | Orígenes permitidos |
| `SECRET_KEY` | `dev-secret-change-in-production` | Firma JWT (HS256); obligatorio cambiar fuera de dev |
| `JWT_ALGORITHM` | `HS256` | Algoritmo del JWT |
| `SERVICE_KEY` | — | Clave que este servicio envía en llamadas salientes |
| `AUTHORIZED_RECOMENDACION_KEY` / `AUTHORIZED_INTEGRACION_LMS_KEY` / `AUTHORIZED_USUARIOS_KEY` | — | Service-keys entrantes autorizadas (Secrets Manager) |

## Correr en local

```bash
cp .env.example .env

# Opción A: solo la BD en Docker, app con reload
docker compose up -d db
uvicorn src.infrastructure.adapters.in_.main:app --reload --port 8003

# Opción B: todo en Docker
docker compose up --build
```

El esquema de BD se crea automáticamente al arrancar (lifespan: `create_all` +
migraciones `ADD COLUMN IF NOT EXISTS` idempotentes), con reintentos hasta que la BD
esté lista. Docs interactivas en `http://localhost:8003/scalar`.

## Tests y lint

```bash
pip install -r requirements-dev.txt
pytest -q                 # 23 tests (unit + integration)
pytest --cov=src          # con cobertura
ruff check                # lint
```

- `tests/unit/` — dominio y use cases con fakes en memoria (sin BD, sin red).
- `tests/integration/` — endpoints y docs OpenAPI vía `httpx.AsyncClient`.

## Flujo de deploy

CI/CD vía GitHub Actions con workflows reutilizables de la org `sward-UPC`:

- **`.github/workflows/ci.yml`** — en `push`/`pull_request` a `main`: corre tests y lint
  (`ci-microservice.yml@main`, con `needs_shared: true` para resolver `sward-shared`).
- **`.github/workflows/build-push.yml`** — en `push` a la rama **`deploy`**: construye la
  imagen Docker, la publica en **GHCR** y actualiza el servicio ECS
  (`build-push-ghcr.yml@main`; `aws_service_name: trazabilidad`, `aws_cluster_name:
  sward-cluster`).

Runtime: contenedor Docker (uvicorn, puerto 8000, usuario no-root) en **AWS ECS/Fargate**
detrás del ALB. Config de BD y claves inyectadas por la task definition (CDK) vía
**Secrets Manager**.

> Nota de dependencia: `sward-shared` se referencia como `@main` en `requirements.txt`.
> La capa Docker que instala dependencias se cachea por contenido del archivo; si un cambio
> en `sward-shared` no se refleja en el deploy, fijar el SHA en lugar de `@main`.

## Proyecto

**TP202610051** — Universidad Peruana de Ciencias Aplicadas (UPC) · Taller de Proyecto / 2026
