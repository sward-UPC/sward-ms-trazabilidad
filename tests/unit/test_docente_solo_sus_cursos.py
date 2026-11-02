"""El docente solo ve los cursos que dicta.

`solo_quien_ensena` le cerraba el paso al estudiante, pero a cualquier docente
lo dejaba entrar a cualquier curso: con su sesión se podía listar la clase de
otro —nombre, correo, nivel de riesgo y promedio—, descargar su reporte en PDF
o leer el detalle de un estudiante ajeno con solo cambiar el UUID del curso en
la URL. La asignación ya existía (``docente_id`` de cada curso en
ms-cursos-recursos, la pone el administrador) y el frontend ya filtraba el
panel con ella; el servidor no la miraba.

Ahora el docente tiene que ser el asignado al curso que pide, el administrador
sigue viendo todos y, si la asignación no se puede consultar, no se entrega
nada.
"""

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.application.ports.out_.cursos_client_port import (
    AsignacionNoDisponibleError,
    CursosClientPort,
)
from src.infrastructure.adapters.in_.main import app
from src.infrastructure.dependencies import (
    get_calcular_indicadores_uc,
    get_consultar_concepto_mastery_uc,
    get_consultar_evolucion_estudiante_uc,
    get_consultar_preferencias_uc,
    get_consultar_progreso_uc,
    get_consultar_racha_uc,
    get_consultar_tendencia_etapas_uc,
    get_cursos_client,
    get_dashboard_docente_uc,
    get_generar_reporte_docente_uc,
    get_registrar_feedback_uc,
    get_trazabilidad_repo,
    require_jwt,
    token_del_usuario,
)

DOCENTE = "11111111-1111-1111-1111-111111111111"
OTRO_DOCENTE = "44444444-4444-4444-4444-444444444444"
ADMIN = "22222222-2222-2222-2222-222222222222"
ESTUDIANTE = "33333333-3333-3333-3333-333333333333"

CURSO_PROPIO = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
CURSO_AJENO = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
CURSO_SIN_DOCENTE = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")

TOKEN = "token-de-la-sesion"
CORREO = "ana.prueba@upc.edu.pe"


def _usuario(rol: str, sub: str) -> dict:
    return {"sub": sub, "rol": rol, "type": "access"}


class _CursosFake(CursosClientPort):
    """ms-cursos-recursos con la asignación que puso el administrador."""

    def __init__(self):
        self.asignaciones = {
            CURSO_PROPIO: UUID(DOCENTE),
            CURSO_AJENO: UUID(OTRO_DOCENTE),
            CURSO_SIN_DOCENTE: None,
        }
        self.consultas: list[tuple[UUID, str]] = []

    async def docente_del_curso(self, curso_id: UUID, token: str) -> UUID | None:
        self.consultas.append((curso_id, token))
        return self.asignaciones.get(curso_id)


class _CursosCaido(CursosClientPort):
    """ms-cursos-recursos sin responder: tiempo agotado."""

    def __init__(self):
        self.consultas: list[tuple[UUID, str]] = []

    async def docente_del_curso(self, curso_id: UUID, token: str) -> UUID | None:
        self.consultas.append((curso_id, token))
        raise AsignacionNoDisponibleError("tiempo agotado")


class _Uc:
    """Caso de uso de mentira: devuelve datos fijos y anota si se ejecutó."""

    def __init__(self, resultado):
        self.resultado = resultado
        self.llamadas: list = []

    async def execute(self, *args, **kwargs):
        self.llamadas.append((args, kwargs))
        return self.resultado


class _Repo:
    def __init__(self, interaccion):
        self.interaccion = interaccion
        self.llamadas: list = []

    async def find_interacciones(self, *args, **kwargs):
        self.llamadas.append((args, kwargs))
        return [self.interaccion]


class _Feedback(_Uc):
    async def execute(self, cmd):
        self.llamadas.append(cmd)
        return SimpleNamespace(
            id=uuid4(),
            estudiante_id=cmd.estudiante_id,
            tipo=cmd.tipo,
            created_at=datetime.now(timezone.utc),
        )


def _alumna_de_la_clase():
    return SimpleNamespace(
        progreso=SimpleNamespace(
            estudiante_id=UUID(ESTUDIANTE),
            nivel_riesgo="alto",
            puntaje_promedio=41.0,
            total_interacciones=12,
            recursos_completados=3,
            ultima_actividad=None,
        ),
        nombre="Ana",
        apellido="Prueba",
        correo=CORREO,
        engagement=20,
        conceptos_en_riesgo=2,
        registrado_en_sward=True,
    )


class _Entorno:
    def __init__(self):
        self.usuario = _usuario("docente", DOCENTE)
        self.cursos: CursosClientPort = _CursosFake()
        self.repo = _Repo(
            SimpleNamespace(
                id=uuid4(),
                actividad_id=None,
                concept_id="Interés simple",
                is_correct=False,
                es_vista=False,
                tipo=SimpleNamespace(value="quiz"),
                fecha=datetime(2026, 10, 1, tzinfo=timezone.utc),
                curso_id=CURSO_AJENO,
                url_modulo=None,
                nombre_actividad="Cuestionario 1",
                tipo_recurso="quiz",
            )
        )
        self.ucs = {
            get_dashboard_docente_uc: _Uc([_alumna_de_la_clase()]),
            get_consultar_tendencia_etapas_uc: _Uc(
                [SimpleNamespace(week="Etapa 1", promedio=41.0, riesgo_alto=1)]
            ),
            get_generar_reporte_docente_uc: _Uc(b"%PDF-1.4 " + CORREO.encode()),
            get_registrar_feedback_uc: _Feedback(None),
            get_consultar_progreso_uc: _Uc(
                SimpleNamespace(
                    id=uuid4(),
                    porcentaje_avance=50.0,
                    nivel_riesgo="alto",
                    total_interacciones=12,
                    puntaje_promedio=41.0,
                )
            ),
            get_calcular_indicadores_uc: _Uc(
                [SimpleNamespace(nombre="Participación", valor=80.0, unidad="%")]
            ),
            get_consultar_racha_uc: _Uc(5),
            get_consultar_concepto_mastery_uc: _Uc(
                [
                    SimpleNamespace(
                        concepto="Interés simple", dominio=0.4, total=5, correctas=2
                    )
                ]
            ),
            get_consultar_evolucion_estudiante_uc: _Uc(
                [SimpleNamespace(etapa="Etapa 1", dominio=0.4)]
            ),
            get_consultar_preferencias_uc: _Uc(
                SimpleNamespace(
                    por_tipo={"quiz": 0.4},
                    tipo_fuerte="quiz",
                    tipo_debil=None,
                    engagement_por_tipo={},
                    formato_mas_consumido="quiz",
                    recursos_vistos=3,
                )
            ),
        }
        self.client: AsyncClient | None = None

    def como(self, rol: str, sub: str) -> None:
        self.usuario = _usuario(rol, sub)

    def se_entregaron_datos(self) -> bool:
        return bool(self.repo.llamadas) or any(uc.llamadas for uc in self.ucs.values())


def _siempre(objeto):
    # Sin parámetros a propósito: FastAPI tomaría un `lambda uc=uc: uc` como
    # parámetro de consulta y entregaría una copia, no el objeto que se vigila.
    return lambda: objeto


@pytest_asyncio.fixture
async def entorno():
    e = _Entorno()
    app.dependency_overrides[require_jwt] = lambda: e.usuario
    app.dependency_overrides[token_del_usuario] = lambda: TOKEN
    app.dependency_overrides[get_cursos_client] = lambda: e.cursos
    app.dependency_overrides[get_trazabilidad_repo] = lambda: e.repo
    for dependencia, uc in e.ucs.items():
        app.dependency_overrides[dependencia] = _siempre(uc)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        e.client = client
        yield e
    app.dependency_overrides.clear()


# Rutas en las que el docente indica un curso. El estudiante consultado es
# siempre el mismo; lo que cambia es el curso.
RUTAS_CON_CURSO = [
    ("GET", "/dashboard/teacher/{curso}/students-progress"),
    ("GET", "/dashboard/teacher/{curso}/trend"),
    ("GET", "/dashboard/teacher/{curso}/report"),
    ("POST", "/dashboard/teacher/feedback"),
    ("GET", "/students/{estudiante}/progress?courseId={curso}"),
    ("GET", "/students/{estudiante}/indicators?courseId={curso}"),
    ("GET", "/students/{estudiante}/interactions?courseId={curso}"),
    ("GET", "/students/{estudiante}/concept-mastery?courseId={curso}"),
    ("GET", "/students/{estudiante}/weekly-progress?courseId={curso}"),
    ("GET", "/students/{estudiante}/preferences?courseId={curso}"),
]


async def _pedir(e: _Entorno, metodo: str, ruta: str, curso: UUID):
    url = ruta.format(curso=curso, estudiante=ESTUDIANTE)
    if metodo == "POST":
        return await e.client.post(
            url,
            json={
                "estudiante_id": ESTUDIANTE,
                "curso_id": str(curso),
                "mensaje": "Revisa el tema 2, vas bien.",
            },
        )
    return await e.client.get(url)


@pytest.mark.parametrize("metodo,ruta", RUTAS_CON_CURSO)
async def test_docente_no_entra_a_un_curso_que_no_dicta(entorno, metodo, ruta):
    resp = await _pedir(entorno, metodo, ruta, CURSO_AJENO)

    assert resp.status_code == 403, resp.text
    assert CORREO not in resp.text
    assert not entorno.se_entregaron_datos()


@pytest.mark.parametrize("metodo,ruta", RUTAS_CON_CURSO)
async def test_docente_entra_al_curso_que_dicta(entorno, metodo, ruta):
    resp = await _pedir(entorno, metodo, ruta, CURSO_PROPIO)

    assert resp.status_code in (200, 201), resp.text
    assert entorno.se_entregaron_datos()


@pytest.mark.parametrize("metodo,ruta", RUTAS_CON_CURSO)
async def test_administrador_entra_a_cualquier_curso(entorno, metodo, ruta):
    # Con ms-cursos-recursos caído a propósito: el administrador no depende de
    # la asignación, así que tampoco de que se pueda consultar.
    entorno.como("administrador", ADMIN)
    entorno.cursos = _CursosCaido()

    resp = await _pedir(entorno, metodo, ruta, CURSO_AJENO)

    assert resp.status_code in (200, 201), resp.text
    assert entorno.cursos.consultas == []


@pytest.mark.parametrize("metodo,ruta", RUTAS_CON_CURSO)
async def test_sin_poder_consultar_la_asignacion_no_se_entregan_datos(
    entorno, metodo, ruta
):
    entorno.cursos = _CursosCaido()

    resp = await _pedir(entorno, metodo, ruta, CURSO_PROPIO)

    assert resp.status_code == 503, resp.text
    assert "curso" in resp.json()["detail"]
    assert CORREO not in resp.text
    assert not entorno.se_entregaron_datos()


async def test_un_curso_sin_docente_asignado_no_es_de_ningun_docente(entorno):
    resp = await entorno.client.get(
        f"/dashboard/teacher/{CURSO_SIN_DOCENTE}/students-progress"
    )

    assert resp.status_code == 403
    assert not entorno.se_entregaron_datos()


async def test_se_consulta_la_asignacion_con_el_token_de_quien_pregunta(entorno):
    await entorno.client.get(f"/dashboard/teacher/{CURSO_PROPIO}/students-progress")

    assert entorno.cursos.consultas == [(CURSO_PROPIO, TOKEN)]


async def test_docente_no_lee_todas_las_interacciones_de_otro_sin_indicar_curso(
    entorno,
):
    # Sin curso la respuesta mezcla todos los del estudiante, también los que
    # el docente no dicta.
    resp = await entorno.client.get(f"/students/{ESTUDIANTE}/interactions")

    assert resp.status_code == 403
    assert not entorno.se_entregaron_datos()


async def test_docente_no_lee_la_racha_de_otro(entorno):
    # La racha es global, de todos los cursos: no hay un curso que comprobar.
    resp = await entorno.client.get(f"/students/{ESTUDIANTE}/streak")

    assert resp.status_code == 403
    assert not entorno.se_entregaron_datos()


async def test_docente_lee_su_propia_racha(entorno):
    resp = await entorno.client.get(f"/students/{DOCENTE}/streak")

    assert resp.status_code == 200
    assert resp.json() == {"dias_racha": 5}


async def test_el_estudiante_sigue_leyendo_solo_lo_suyo(entorno):
    # La regla del docente no toca al estudiante: pida el curso que pida, se
    # queda con sus propios datos y no se consulta a ms-cursos-recursos.
    entorno.como("estudiante", ESTUDIANTE)

    resp = await entorno.client.get(
        f"/students/{OTRO_DOCENTE}/progress?courseId={CURSO_AJENO}"
    )

    assert resp.status_code == 200
    (cmd,), _ = entorno.ucs[get_consultar_progreso_uc].llamadas[0]
    assert cmd.estudiante_id == UUID(ESTUDIANTE)
    assert entorno.cursos.consultas == []


async def test_el_estudiante_sigue_sin_entrar_al_panel_de_clase(entorno):
    entorno.como("estudiante", ESTUDIANTE)

    resp = await entorno.client.get(
        f"/dashboard/teacher/{CURSO_PROPIO}/students-progress"
    )

    assert resp.status_code == 403
    assert not entorno.se_entregaron_datos()


async def test_el_estudiante_recibe_403_en_la_retroalimentacion_aunque_el_body_falle(
    entorno,
):
    # El rol se mira antes de validar el body: un estudiante no aprende nada
    # del contrato probando bodies.
    entorno.como("estudiante", ESTUDIANTE)

    resp = await entorno.client.post(
        "/dashboard/teacher/feedback", json={"curso_id": "no-es-un-uuid"}
    )

    assert resp.status_code == 403
    assert entorno.cursos.consultas == []


async def test_un_docente_con_un_sub_que_no_es_uuid_no_pasa(entorno):
    entorno.como("docente", "no-es-un-uuid")

    resp = await entorno.client.get(
        f"/dashboard/teacher/{CURSO_PROPIO}/students-progress"
    )

    assert resp.status_code == 403
    assert not entorno.se_entregaron_datos()
