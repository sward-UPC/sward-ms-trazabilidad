import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from src.application.use_cases.registrar_interaccion import (
    RegistrarInteraccionCommand,
    RegistrarInteraccionUseCase,
)
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
    use_case._event_publisher.publish.assert_called_once()
