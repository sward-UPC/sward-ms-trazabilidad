"""El recurso que el estudiante marca como completado tiene que recordarse.

Defecto 16 (HU-034, escenario 3; CP080, observado por el grupo 10 en el ciclo 1):
al marcar un recurso de «Recomendado para ti» con «Ya lo revisé» o «Marcar como
completado», se guardaba la sección y el tipo, pero no qué recurso era. Al recargar
la página nada decía que ese recurso ya estaba hecho y volvía a ofrecerse igual.
Ahora el registro guarda la dirección del recurso y las preferencias del
estudiante devuelven la lista de los que completó.
"""

from uuid import UUID

import pytest

from src.application.use_cases.registrar_material_completado import (
    RegistrarMaterialCompletadoCommand,
    RegistrarMaterialCompletadoUseCase,
)
from src.infrastructure.adapters.in_.mappers import _serializar_preferencias
from src.infrastructure.adapters.in_.schemas import MaterialCompletadoRequest
from src.infrastructure.adapters.in_.trazabilidad_router import (
    registrar_material_completado,
)
from src.infrastructure.adapters.out_.trazabilidad_postgres_adapter import (
    resumir_preferencias,
)

ESTUDIANTE = UUID("33333333-3333-3333-3333-333333333333")
CURSO = UUID("44444444-4444-4444-4444-444444444444")
URL = "https://aula.example.com/mod/page/view.php?id=101"


class RepoEnMemoria:
    def __init__(self):
        self.guardadas = []

    async def save_interaccion(self, interaccion):
        self.guardadas.append(interaccion)
        return interaccion

    async def find_progreso(self, estudiante_id, curso_id):
        return None

    async def save_progreso(self, progreso):
        return progreso


class PublicadorMudo:
    def publish(self, evento):
        pass


@pytest.mark.parametrize("tipo", ["lectura", "video", "practica"])
async def test_el_registro_guarda_que_recurso_se_completo(tipo):
    repo = RepoEnMemoria()
    uc = RegistrarMaterialCompletadoUseCase(repo, PublicadorMudo())
    await uc.execute(
        RegistrarMaterialCompletadoCommand(
            estudiante_id=ESTUDIANTE,
            curso_id=CURSO,
            concepto="Interés simple",
            tipo=tipo,
            url_modulo=URL,
        )
    )
    assert repo.guardadas[0].url_modulo == URL


async def test_la_ruta_pasa_la_direccion_del_recurso_al_caso_de_uso():
    recibido = {}

    class CasoDeUsoEspia:
        async def execute(self, cmd):
            recibido["cmd"] = cmd

            class Guardada:
                es_vista = True

            return Guardada()

    body = MaterialCompletadoRequest(
        curso_id=CURSO, concepto="Interés simple", tipo="lectura", url_modulo=URL
    )
    await registrar_material_completado(
        body, {"sub": str(ESTUDIANTE)}, CasoDeUsoEspia()
    )
    assert recibido["cmd"].url_modulo == URL


def test_la_direccion_es_opcional_para_no_romper_la_version_publicada():
    body = MaterialCompletadoRequest(curso_id=CURSO, concepto="X", tipo="video")
    assert body.url_modulo == ""


def test_las_preferencias_devuelven_los_recursos_completados():
    # (tipo_recurso, nota, is_correct, es_vista, url_modulo), como la consulta
    filas = [
        ("lectura_generada", None, True, True, URL),
        ("practica_generada", 100.0, True, False, URL + "2"),
        ("practica_generada", 0.0, False, False, URL + "2"),  # se repite: una vez
        ("lectura_generada", None, True, True, ""),  # registro viejo, sin dirección
        ("quiz", 80.0, True, False, URL + "3"),  # intento en Moodle: no es «completado»
        ("page", None, True, True, URL + "4"),  # vista sincronizada desde Moodle
    ]
    pref = resumir_preferencias(filas)
    assert pref.recursos_completados == [URL, URL + "2"]
    # lo que ya existía no cambia
    assert pref.recursos_vistos == [URL, URL + "4"]
    assert _serializar_preferencias(pref)["recursos_completados"] == [URL, URL + "2"]
