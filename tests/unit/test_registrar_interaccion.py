import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from src.application.use_cases.registrar_interaccion import (
    RegistrarInteraccionCommand,
    RegistrarInteraccionUseCase,
)
from src.domain.events.interaccion_registrada_event import InteraccionRegistradaEvent
from src.domain.value_objects.nivel_riesgo import TipoInteraccion


@pytest.fixture
def use_case():
    repo = AsyncMock()
    repo.save_interaccion.side_effect = lambda i: i
    repo.find_progreso.return_value = None
    repo.save_progreso.side_effect = lambda p: p
    return RegistrarInteraccionUseCase(repo, MagicMock())


@pytest.mark.asyncio
async def test_registrar_interaccion_vista(use_case):
    cmd = RegistrarInteraccionCommand(
        estudiante_id=uuid4(), curso_id=uuid4(), tipo=TipoInteraccion.VISTA
    )
    i = await use_case.execute(cmd)
    assert i.tipo == TipoInteraccion.VISTA


@pytest.mark.asyncio
async def test_registrar_crea_progreso_si_no_existe(use_case):
    cmd = RegistrarInteraccionCommand(estudiante_id=uuid4(), curso_id=uuid4())
    await use_case.execute(cmd)
    use_case._repo.save_progreso.assert_called_once()


@pytest.mark.asyncio
async def test_registrar_publica_evento(use_case):
    cmd = RegistrarInteraccionCommand(estudiante_id=uuid4(), curso_id=uuid4())
    await use_case.execute(cmd)
    publish = use_case._event_publisher.publish
    publish.assert_called()
    # El primer evento publicado siempre es InteraccionRegistrada.
    primero = publish.call_args_list[0].args[0]
    assert isinstance(primero, InteraccionRegistradaEvent)


@pytest.mark.asyncio
async def test_registrar_publica_riesgo_cuando_critico(use_case):
    # Estudiante nuevo sin puntaje → riesgo crítico → además emite RiesgoActualizado.
    cmd = RegistrarInteraccionCommand(estudiante_id=uuid4(), curso_id=uuid4())
    await use_case.execute(cmd)
    tipos = [
        c.args[0].event_type for c in use_case._event_publisher.publish.call_args_list
    ]
    assert any("RiesgoActualizado" in t for t in tipos)
