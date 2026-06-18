"""Tests de integración de los endpoints de trazabilidad (in-process)."""

from uuid import uuid4

import pytest

HEALTH = "/health"
INTERACTIONS = "/interactions"

ESTUDIANTE = str(uuid4())
CURSO = str(uuid4())


@pytest.mark.asyncio
async def test_health_ok(client):
    resp = await client.get(HEALTH)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_endpoint_protegido_sin_token_retorna_401(anon_client):
    resp = await anon_client.post(
        INTERACTIONS,
        json={"estudiante_id": ESTUDIANTE, "curso_id": CURSO, "tipo": "vista"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_registrar_interaccion_devuelve_201(client):
    resp = await client.post(
        INTERACTIONS,
        json={"estudiante_id": ESTUDIANTE, "curso_id": CURSO, "tipo": "vista"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert "id" in body
    assert body["tipo"] == "vista"


@pytest.mark.asyncio
async def test_progress_sin_actividad(client):
    resp = await client.get(
        f"/students/{ESTUDIANTE}/progress", params={"courseId": CURSO}
    )
    assert resp.status_code == 200
    assert resp.json()["total_interacciones"] == 0


@pytest.mark.asyncio
async def test_flujo_interaccion_se_refleja_en_progreso(client):
    est = str(uuid4())
    curso = str(uuid4())

    reg = await client.post(
        INTERACTIONS,
        json={
            "estudiante_id": est,
            "curso_id": curso,
            "tipo": "respuesta",
            "puntaje": 90.0,
        },
    )
    assert reg.status_code == 201

    resp = await client.get(f"/students/{est}/progress", params={"courseId": curso})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_interacciones"] == 1
    assert body["puntaje_promedio"] == 90.0
    # 90 -> riesgo bajo según _recalcular_riesgo.
    assert body["nivel_riesgo"] == "bajo"


@pytest.mark.asyncio
async def test_dashboard_docente_lista_progreso_del_curso(client):
    curso = str(uuid4())
    est_a = str(uuid4())
    est_b = str(uuid4())

    await client.post(
        INTERACTIONS,
        json={
            "estudiante_id": est_a,
            "curso_id": curso,
            "tipo": "respuesta",
            "puntaje": 30.0,
        },
    )
    await client.post(
        INTERACTIONS,
        json={
            "estudiante_id": est_b,
            "curso_id": curso,
            "tipo": "respuesta",
            "puntaje": 85.0,
        },
    )

    resp = await client.get(f"/dashboard/teacher/{curso}/students-progress")
    assert resp.status_code == 200
    progresos = resp.json()
    assert len(progresos) == 2
    # Ordenado por riesgo descendente: el de puntaje 30 (crítico) va primero.
    assert progresos[0]["nivel_riesgo"] == "critico"
    estudiantes = {p["estudiante_id"] for p in progresos}
    assert estudiantes == {est_a, est_b}
    # El dashboard se enriquece con nombre/correo vía s2s a ms-usuarios.
    assert all(p["nombre"] for p in progresos)
    assert all("@upc.edu.pe" in p["correo"] for p in progresos)


@pytest.mark.asyncio
async def test_reporte_docente_genera_pdf(client):
    curso = str(uuid4())
    await client.post(
        INTERACTIONS,
        json={
            "estudiante_id": str(uuid4()),
            "curso_id": curso,
            "tipo": "respuesta",
            "puntaje": 65.0,
        },
    )

    resp = await client.get(f"/dashboard/teacher/{curso}/report")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert "attachment" in resp.headers["content-disposition"]
    # Un PDF válido empieza con la firma %PDF.
    assert resp.content[:4] == b"%PDF"
    assert len(resp.content) > 1000  # contenido real, no vacío


@pytest.mark.asyncio
async def test_registrar_feedback_docente(client):
    resp = await client.post(
        "/dashboard/teacher/feedback",
        json={
            "estudiante_id": str(uuid4()),
            "curso_id": str(uuid4()),
            "mensaje": "Buen avance, sigue reforzando fracciones.",
            "tipo": "encouragement",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["tipo"] == "encouragement"
    assert body["id"]


@pytest.mark.asyncio
async def test_registrar_feedback_tipo_invalido_es_422(client):
    resp = await client.post(
        "/dashboard/teacher/feedback",
        json={
            "estudiante_id": str(uuid4()),
            "curso_id": str(uuid4()),
            "mensaje": "x",
            "tipo": "no-existe",
        },
    )
    assert resp.status_code == 422
