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
    assert resp.json()["sin_actividad"] is True


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
