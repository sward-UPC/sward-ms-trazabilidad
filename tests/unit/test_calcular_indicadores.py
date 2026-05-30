import pytest
from unittest.mock import AsyncMock
from uuid import uuid4
from src.application.use_cases.calcular_indicadores import (
    CalcularIndicadoresCommand,
    CalcularIndicadoresUseCase,
)
from src.domain.entities.progreso_academico import ProgresoAcademico


@pytest.mark.asyncio
async def test_calcula_4_indicadores():
    repo = AsyncMock()
    repo.find_progreso.return_value = ProgresoAcademico(
        estudiante_id=uuid4(),
        curso_id=uuid4(),
        total_interacciones=10,
        puntaje_promedio=75.0,
        recursos_completados=3,
        porcentaje_avance=60.0,
    )
    repo.save_indicador.return_value = None
    uc = CalcularIndicadoresUseCase(repo)
    indicadores = await uc.execute(
        CalcularIndicadoresCommand(estudiante_id=uuid4(), curso_id=uuid4())
    )
    assert len(indicadores) == 4
    nombres = {i.nombre for i in indicadores}
    assert "total_interacciones" in nombres
    assert "puntaje_promedio" in nombres


@pytest.mark.asyncio
async def test_sin_progreso_retorna_vacio():
    repo = AsyncMock()
    repo.find_progreso.return_value = None
    uc = CalcularIndicadoresUseCase(repo)
    result = await uc.execute(
        CalcularIndicadoresCommand(estudiante_id=uuid4(), curso_id=uuid4())
    )
    assert result == []
