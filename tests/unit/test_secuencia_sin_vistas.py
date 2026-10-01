"""Las vistas no deben entrar a la secuencia del knowledge-tracing.

Abrir un resumen, un video o la solución se guarda como interacción con
``es_vista=True`` y, por cómo las registra la sincronización, con
``is_correct=True``. El entrenamiento del SAKT las descarta —el export de
``/dashboard/training-data`` filtra ``es_vista=False``—, pero la ruta que arma
la secuencia para servir el modelo no las filtraba y, además, ni siquiera
devolvía el campo, así que quien consumía el historial no podía distinguir una
respuesta de una lectura. El modelo recibía aciertos que nadie respondió, y en
un tema de seis recursos y tres cuestionarios eso es más de la mitad de la
secuencia.
"""

from uuid import UUID, uuid4

from src.domain.entities.interaccion_academica import InteraccionAcademica
from src.domain.value_objects.nivel_riesgo import TipoInteraccion
from src.infrastructure.adapters.in_.trazabilidad_router import (
    _get_interactions_handler,
)

ESTUDIANTE = UUID("33333333-3333-3333-3333-333333333333")
CURSO = UUID("44444444-4444-4444-4444-444444444444")


def interaccion(es_vista: bool, concepto: str) -> InteraccionAcademica:
    return InteraccionAcademica(
        id=uuid4(),
        estudiante_id=ESTUDIANTE,
        curso_id=CURSO,
        tipo=TipoInteraccion.COMPLETADO if es_vista else TipoInteraccion.RESPUESTA,
        concept_id=concepto,
        is_correct=True,
        es_vista=es_vista,
    )


class RepoEspia:
    """Devuelve lo pedido y guarda con qué filtro se lo pidieron."""

    def __init__(self, items):
        self.items = items
        self.solo_calificadas = None

    async def find_interacciones(
        self, estudiante_id, curso_id=None, limit=50, solo_calificadas=False
    ):
        self.solo_calificadas = solo_calificadas
        if solo_calificadas:
            return [i for i in self.items if not i.es_vista]
        return self.items


async def test_el_historial_dice_si_cada_interaccion_fue_vista():
    repo = RepoEspia([interaccion(True, "Interés simple")])
    filas = await _get_interactions_handler(ESTUDIANTE, CURSO, 50, repo)
    assert filas[0]["es_vista"] is True


async def test_pedir_solo_calificadas_llega_al_repositorio():
    # El filtro tiene que viajar hasta la consulta: si se aplicara después, el
    # `limit` se gastaría en vistas y la secuencia calificada saldría recortada.
    repo = RepoEspia([interaccion(True, "Interés simple")])
    await _get_interactions_handler(ESTUDIANTE, CURSO, 50, repo, solo_calificadas=True)
    assert repo.solo_calificadas is True


async def test_solo_calificadas_deja_fuera_las_vistas():
    repo = RepoEspia(
        [
            interaccion(True, "Interés simple"),
            interaccion(False, "Interés simple"),
            interaccion(True, "Amortización"),
        ]
    )
    filas = await _get_interactions_handler(
        ESTUDIANTE, CURSO, 50, repo, solo_calificadas=True
    )
    assert len(filas) == 1
    assert filas[0]["es_vista"] is False


async def test_por_omision_el_historial_completo_sigue_saliendo():
    # La racha y el historial que ve el estudiante cuentan el material abierto:
    # el valor por omisión no cambia para no romperlos.
    repo = RepoEspia(
        [interaccion(True, "Interés simple"), interaccion(False, "VAN y TIR")]
    )
    filas = await _get_interactions_handler(ESTUDIANTE, CURSO, 50, repo)
    assert len(filas) == 2
    assert repo.solo_calificadas is False
