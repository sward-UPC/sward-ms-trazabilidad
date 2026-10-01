"""Las rutas del panel de clase exigen rol de docente.

`/dashboard/teacher/...` solo pedía un JWT válido y nunca miraba el rol, aunque
su documentación prometiera un 403. Con la sesión de cualquiera de los
participantes se podía listar a toda la clase y descargar el reporte en PDF, que
lleva nombre, correo, nivel de riesgo y dominio de cada compañero — datos
personales de treinta estudiantes bajo la Ley 29733.

La función que exige un rol ya existía en sward-shared y no se usaba en ningún
router.
"""

import pytest
from fastapi import HTTPException

from src.infrastructure.adapters.in_.trazabilidad_router import solo_quien_ensena

DOCENTE = {"rol": "docente", "sub": "11111111-1111-1111-1111-111111111111"}
ADMIN = {"rol": "administrador", "sub": "22222222-2222-2222-2222-222222222222"}
ESTUDIANTE = {"rol": "estudiante", "sub": "33333333-3333-3333-3333-333333333333"}


async def test_el_docente_pasa():
    assert await solo_quien_ensena(DOCENTE) == DOCENTE


async def test_el_administrador_pasa():
    assert await solo_quien_ensena(ADMIN) == ADMIN


async def test_el_estudiante_no_pasa():
    with pytest.raises(HTTPException) as e:
        await solo_quien_ensena(ESTUDIANTE)
    assert e.value.status_code == 403


async def test_un_token_sin_rol_no_pasa():
    # Sin el claim no se asume nada: el lado seguro del error es quedarse fuera.
    with pytest.raises(HTTPException) as e:
        await solo_quien_ensena({"sub": ESTUDIANTE["sub"]})
    assert e.value.status_code == 403


async def test_un_rol_desconocido_tampoco():
    with pytest.raises(HTTPException) as e:
        await solo_quien_ensena({"rol": "invitado", "sub": ESTUDIANTE["sub"]})
    assert e.value.status_code == 403
