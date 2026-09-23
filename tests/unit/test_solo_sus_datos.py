"""El estudiante solo lee sus propios datos.

Las rutas /students/{id}/... tomaban el id de la URL sin mirar quién preguntaba:
con un JWT de estudiante se podían leer los datos de otro cambiando el UUID, que
además se deriva del id de Moodle con uuid5 y por tanto se puede calcular.
"""

from uuid import UUID

from src.infrastructure.adapters.in_.trazabilidad_router import de_quien

OTRO = UUID("11111111-1111-1111-1111-111111111111")
YO = "22222222-2222-2222-2222-222222222222"


def test_estudiante_solo_lee_lo_suyo():
    assert de_quien(OTRO, {"rol": "estudiante", "sub": YO}) == UUID(YO)


def test_docente_lee_el_de_cualquiera():
    assert de_quien(OTRO, {"rol": "docente", "sub": YO}) == OTRO


def test_administrador_lee_el_de_cualquiera():
    assert de_quien(OTRO, {"rol": "administrador", "sub": YO}) == OTRO


def test_sin_rol_no_se_asume_docente():
    # Un token sin el claim no abre la puerta: se queda con lo suyo.
    assert de_quien(OTRO, {"sub": YO}) == UUID(YO)


def test_rol_desconocido_tampoco():
    assert de_quien(OTRO, {"rol": "invitado", "sub": YO}) == UUID(YO)
