"""Las rutas del panel de clase exigen rol de docente.

`/dashboard/teacher/...` solo pedía un JWT válido y nunca miraba el rol, aunque
su documentación prometiera un 403. Con la sesión de cualquiera de los
participantes se podía listar a toda la clase y descargar el reporte en PDF, que
lleva nombre, correo, nivel de riesgo y dominio de cada compañero — datos
personales de treinta estudiantes bajo la Ley 29733.

La función que exige un rol ya existía en sward-shared y no se usaba en ningún
router. Que además el docente dicte ese curso se prueba en
test_docente_solo_sus_cursos.py; aquí el docente pide el suyo.
"""

from uuid import UUID

import pytest
from fastapi import HTTPException

from src.application.ports.out_.cursos_client_port import CursosClientPort
from src.infrastructure.adapters.in_.trazabilidad_router import solo_quien_ensena

DOCENTE = {"rol": "docente", "sub": "11111111-1111-1111-1111-111111111111"}
ADMIN = {"rol": "administrador", "sub": "22222222-2222-2222-2222-222222222222"}
ESTUDIANTE = {"rol": "estudiante", "sub": "33333333-3333-3333-3333-333333333333"}

CURSO = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")


class _CursoDelDocente(CursosClientPort):
    async def docente_del_curso(self, curso_id, token):
        return UUID(DOCENTE["sub"])


async def _pasa(user: dict) -> dict:
    return await solo_quien_ensena(CURSO, user, "token", _CursoDelDocente())


async def test_el_docente_pasa():
    assert await _pasa(DOCENTE) == DOCENTE


async def test_el_administrador_pasa():
    assert await _pasa(ADMIN) == ADMIN


async def test_el_estudiante_no_pasa():
    with pytest.raises(HTTPException) as e:
        await _pasa(ESTUDIANTE)
    assert e.value.status_code == 403


async def test_un_token_sin_rol_no_pasa():
    # Sin el claim no se asume nada: el lado seguro del error es quedarse fuera.
    with pytest.raises(HTTPException) as e:
        await _pasa({"sub": ESTUDIANTE["sub"]})
    assert e.value.status_code == 403


async def test_un_rol_desconocido_tampoco():
    with pytest.raises(HTTPException) as e:
        await _pasa({"rol": "invitado", "sub": ESTUDIANTE["sub"]})
    assert e.value.status_code == 403
