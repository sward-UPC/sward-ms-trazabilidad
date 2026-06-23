from uuid import uuid4
from src.domain.entities.progreso_academico import ProgresoAcademico
from src.domain.value_objects.nivel_riesgo import NivelRiesgo


def test_riesgo_critico_por_puntaje_bajo():
    p = ProgresoAcademico(
        estudiante_id=uuid4(), curso_id=uuid4(), puntaje_promedio=35.0
    )
    p._recalcular_riesgo()
    assert p.nivel_riesgo == NivelRiesgo.CRITICO


def test_riesgo_bajo_puntaje_alto():
    p = ProgresoAcademico(
        estudiante_id=uuid4(),
        curso_id=uuid4(),
        puntaje_promedio=85.0,
        total_interacciones=5,
    )
    p._recalcular_riesgo()
    assert p.nivel_riesgo == NivelRiesgo.BAJO


def test_por_puntaje_es_la_regla_unica_de_umbrales():
    # Fuente de verdad del dominio: usada por el progreso y por la sync del LMS.
    assert NivelRiesgo.por_puntaje(0.0, 0) == NivelRiesgo.CRITICO
    assert NivelRiesgo.por_puntaje(39.9) == NivelRiesgo.CRITICO
    assert NivelRiesgo.por_puntaje(40.0) == NivelRiesgo.ALTO
    assert NivelRiesgo.por_puntaje(59.9) == NivelRiesgo.ALTO
    assert NivelRiesgo.por_puntaje(60.0) == NivelRiesgo.MEDIO
    assert NivelRiesgo.por_puntaje(74.9) == NivelRiesgo.MEDIO
    assert NivelRiesgo.por_puntaje(75.0) == NivelRiesgo.BAJO
