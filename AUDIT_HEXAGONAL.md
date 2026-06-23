# Auditoría Hexagonal — sward-ms-trazabilidad

Fecha: 2026-06-22
Referencia de convenciones: `/Users/ryzeon/Development/@Tesis/HEXAGONAL.md`

Este microservicio usa la nomenclatura **`domain` / `application` / `infrastructure`**
con la separación `infrastructure/adapters/{in_,out_}` y `infrastructure/config`.
Es una variante válida de Ports & Adapters: `domain/ports/out_` son los contratos
del núcleo, `adapters/in_` son los adaptadores de entrada (FastAPI) y `adapters/out_`
los de salida (Postgres, EventBridge, REST, PDF). **No se renombraron carpetas ni se
hizo refactor estructural** (fuera del alcance).

---

## Resumen ejecutivo

La arquitectura es **sólida en el núcleo**: el dominio y la aplicación están limpios,
sin acoplamiento a frameworks, con puertos bien ubicados y eventos publicados desde la
capa de aplicación (no desde el dominio). El punto débil es **un único archivo**: el
router de entrada (`trazabilidad_router.py`, ~1450 líneas) concentra lógica de negocio
y acceso directo a la base de datos en varios endpoints, saltándose las capas
`application/` y `domain/`. Es deuda técnica localizada, no un problema de diseño global.

| Principio | Estado |
|---|---|
| Regla de dependencia (sin frameworks en `domain/`) | ✅ Cumple |
| Sin frameworks en `application/` | ✅ Cumple |
| Puertos en el núcleo (`domain/ports/out_`) | ✅ Cumple |
| 3 representaciones (schema ≠ dominio ≠ ORM) con mappers | ⚠️ Parcial |
| Errores dominio→HTTP centralizados | ⚠️ Parcial |
| Invariantes en el dominio | ⚠️ Parcial |
| Eventos de dominio publicados por la capa de aplicación | ✅ Cumple |
| Inyección por constructor / tipado contra puertos | ✅ Cumple |

---

## Hallazgos

### ✅ Lo que está bien

1. **Regla de dependencia respetada en el núcleo.** Verificado con grep: ningún
   `import fastapi / sqlalchemy / boto3 / httpx / pydantic` dentro de `src/domain/` ni
   `src/application/`. El dominio son dataclasses puras (`InteraccionAcademica`,
   `ProgresoAcademico`, value objects `NivelRiesgo`/`TipoInteraccion` con `StrEnum`).

2. **Puertos en el lugar correcto.** Los contratos viven en `domain/ports/out_/`
   (`EventPublisherPort`, `TrazabilidadRepositoryPort`, `LmsClientPort`,
   `UsuariosClientPort`, `ReporteRendererPort`) como `ABC`, y los adaptadores de
   `infrastructure/adapters/out_/` heredan de ellos. Esto es el corazón del patrón.

3. **Eventos publicados por la capa de aplicación, no por el dominio.** `RegistrarInteraccionUseCase`
   construye y publica `InteraccionRegistradaEvent`, `RiesgoActualizadoEvent` y
   `LogroDesbloqueadoEvent` a través de `EventPublisherPort`. El dominio NO conoce
   EventBridge. El adaptador (`EventBridgeAdapter`) traduce a `sward_shared`. Correcto.
   (Nota menor: las entidades no acumulan eventos con un `pull_events()` al estilo
   aggregate del doc; el caso de uso decide qué publicar. Es una simplificación
   aceptable dado que las invariantes aquí son simples.)

4. **Inyección por constructor y tipado contra puertos.** Los use cases reciben
   `TrazabilidadRepositoryPort` / `EventPublisherPort` por constructor; el cableado de
   implementaciones concretas está aislado en `infrastructure/dependencies.py`
   (composition root vía `Depends`). Cumple.

5. **Handler global de errores no controlados.** `main.py` registra un
   `@app.exception_handler(Exception)` que evita filtrar trazas al cliente (500 genérico).

### ⚠️ Hallazgos a corregir (recomendaciones — refactors NO triviales)

**H1 — Lógica de negocio + SQL crudo en el router (principal).**
`infrastructure/adapters/in_/trazabilidad_router.py` tiene ~1450 líneas. Varios
endpoints abren `AsyncSession` directamente (`Depends(get_session)`), arman queries
SQLAlchemy y ejecutan reglas de negocio dentro del handler, saltándose `application/` y
los puertos. Endpoints afectados:

- `get_concept_mastery` — agrega por `concept_id`, calcula tasa de acierto/dominio.
- `platform_activity` — serie temporal de actividad por día.
- `get_weekly_progress` — dominio acumulado por etapas de la secuencia.
- `tendencia_docente` — promedio acumulado + estudiantes en riesgo por etapa (¡y existe
  un `ConsultarTendenciaUseCase` que NO se usa! El router reimplementa la lógica con SQL
  en vez de delegar — duplicación + use case huérfano).
- `_calcular_preferencias` (helper) — reglas de preferencia de formato (rendimiento vs.
  engagement, `tipo_fuerte`/`tipo_debil`); reusado por la ruta JWT y la interna.
- `lms_sync` — el más grave: deduplicación, derivación de IDs Moodle→UUID, recálculo de
  `academic_progress`, **umbrales de nivel de riesgo embebidos** (`if puntaje < 40 …`)
  y `commit`, todo dentro del endpoint. Esos umbrales YA existen en el dominio
  (`ProgresoAcademico._recalcular_riesgo`), por lo que la regla de negocio está
  **duplicada y divergente** (el router usa cortes 40/55/70; el dominio 40/60/75).
- `get_training_data` — query del dataset SAKT con filtros de negocio (`es_vista=False`,
  `concept_id` no vacío) en el handler.

   **Impacto:** la regla "el router es delgado: HTTP→comando→servicio→HTTP" se viola; hay
   lógica no testeable sin levantar BD; y los umbrales de riesgo están duplicados con
   riesgo de divergencia (ya divergen). Anti-patrones del doc §11: "reglas de negocio en
   el router", "publicar/commit en el router".

   **Recomendación (refactor grande, fuera del alcance de esta auditoría):**
   - Mover cada bloque a un use case en `application/use_cases/` (p.ej.
     `ConsultarDominioPorConcepto`, `ConsultarActividadPlataforma`,
     `SincronizarLmsUseCase`, `ConsultarPreferenciasUseCase`, `ExportarTrainingDataUseCase`),
     consumiendo `TrazabilidadRepositoryPort` (añadiendo métodos de consulta al puerto).
   - **Hacer que `tendencia_docente` use el `ConsultarTendenciaUseCase` ya existente** (o
     borrar el use case si se decide no usarlo). Es el arreglo de mayor relación
     valor/esfuerzo y elimina duplicación.
   - **Unificar los umbrales de riesgo** en un único lugar del dominio (extraer
     `NivelRiesgo.desde_puntaje(p)` o reutilizar `ProgresoAcademico._recalcular_riesgo`)
     y consumirlo tanto en `lms_sync` como en el dominio. Elimina la divergencia 40/55/70
     vs 40/60/75.

**H2 — Tres representaciones: mappers implícitos / dicts sueltos.**
Hay separación schema (Pydantic) ≠ dominio (dataclass) ≠ ORM (SQLAlchemy en
`infrastructure/db/models/`), lo cual es correcto. Pero el mapeo dominio→respuesta se
hace con `dict` inline en cada endpoint (p.ej. `dashboard_docente`, `get_progress`) en
lugar de mappers explícitos, y algunos endpoints devuelven `list[dict]`/`dict` sin
`response_model`. No es un bug, pero diluye el contrato.
   **Recomendación:** centralizar el mapeo dominio→schema en un `mappers.py` del adaptador
   de entrada y declarar `response_model` en los endpoints que hoy devuelven `dict`.

**H3 — Errores dominio→HTTP no centralizados por tipo.**
Existe el handler global de `Exception` (500), pero NO hay un
`@app.exception_handler(DomainError)` que mapee errores de negocio a códigos HTTP
(404/409/422) como recomienda el doc §7. Hoy los endpoints evitan el problema con
fallbacks (p.ej. `get_progress` devuelve un progreso "vacío" en vez de 404) o validan en
Pydantic. Funciona, pero no sigue el patrón de "traducción de errores en un solo sitio".
   **Recomendación:** definir una jerarquía `DomainError` en `domain/` y registrar un
   exception handler único que la traduzca a HTTP. (Refactor moderado; depende de que el
   dominio empiece a lanzar errores de negocio en vez de devolver valores nulos.)

**H4 — Use case huérfano.** `ConsultarTendenciaUseCase` está implementado, inyectado en
`dependencies.py`, pero el endpoint `tendencia_docente` no lo invoca (reimplementa con
SQL). Ver H1. Decidir: cablearlo o eliminarlo.

### Arreglos triviales aplicados

Ninguno de código. La auditoría no encontró arreglos triviales seguros dentro del
alcance (todos los hallazgos son refactors que tocan varias capas y cambian
comportamiento/tests). Los cambios de Tarea 1 (limpieza de `.DS_Store` y
`docs/PROGRESS.md`) sí se aplicaron. `ruff check` pasa limpio y los 23 tests pasan,
antes y después de la limpieza.

---

## Plan recomendado (priorizado, para una iteración futura)

1. **(Alto valor / bajo riesgo)** Unificar umbrales de `NivelRiesgo` en el dominio y
   consumirlos desde `lms_sync`. Elimina la divergencia 40/55/70 vs 40/60/75 (bug latente).
2. **(Alto valor / bajo riesgo)** Cablear `tendencia_docente` al `ConsultarTendenciaUseCase`
   existente, o eliminar el use case. Quita duplicación y el huérfano.
3. **(Medio)** Extraer la lógica SQL de `get_concept_mastery`, `platform_activity`,
   `get_weekly_progress`, `_calcular_preferencias`, `get_training_data` y `lms_sync` a use
   cases con métodos nuevos en `TrazabilidadRepositoryPort`. Adelgaza el router y hace la
   lógica testeable con fakes.
4. **(Medio)** Introducir `DomainError` + exception handler centralizado dominio→HTTP.
5. **(Bajo)** Centralizar mappers dominio→schema y declarar `response_model` en los
   endpoints que devuelven `dict`.

> Regla de oro respetada: el núcleo (`domain/`, `application/`, `ports`) está limpio. La
> deuda es de la capa de adaptadores de entrada y es recuperable incrementalmente sin
> tocar el dominio.

---

## Verificación

- `pytest -q` → **23 passed** (sin cambios respecto al baseline).
- `ruff check` → **All checks passed!**
