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
