"""Contratos HTTP del endpoint interno de sincronización LMS (Moodle → SWARD)."""

from datetime import datetime

from pydantic import BaseModel


class LmsInteraccionItem(BaseModel):
    moodle_user_id: str
    moodle_course_id: str
    moodle_activity_id: str
    nombre: str = ""
    correo: str = ""
    concepto: str = ""
    es_correcta: bool = False
    nota: float = 0.0
    url_modulo: str = ""
    nombre_actividad: str = ""
    tipo_recurso: str = ""
    es_vista: bool = False
    fecha_evento: datetime
    moodle_event_id: str = ""


class LmsSyncRequest(BaseModel):
    interacciones: list[LmsInteraccionItem]
