# PROGRESS — sward-ms-trazabilidad

## Sprint 3 — 2026-05-29

### Implementado
- [x] Entidades: InteraccionAcademica, RespuestaActividad, ProgresoAcademico, IndicadorTrazabilidad
- [x] Value objects: NivelRiesgo, TipoInteraccion
- [x] Evento: InteraccionRegistradaEvent
- [x] Use Cases: RegistrarInteraccion, ConsultarProgreso, CalcularIndicadores, ConsultarDashboardDocente
- [x] TrazabilidadPostgresAdapter
- [x] LmsRestAdapter (mock en dev)
- [x] EventBridgeAdapter
- [x] Endpoints: POST /interactions, GET /students/{id}/progress|indicators|interactions, GET /dashboard/teacher/{id}/students-progress
- [x] SQLAlchemy models: interactions, academic_progress, indicators
- [x] Docker Compose: PostgreSQL 15
- [x] Tests unitarios: 7 tests
- [x] GitHub Actions CI
