from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class InteraccionModel(Base):
    __tablename__ = "interactions"
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    estudiante_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    curso_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    actividad_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    recurso_id: Mapped[UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    fecha: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
    moodle_event_id: Mapped[str] = mapped_column(String(100), default="")


class ProgresoModel(Base):
    __tablename__ = "academic_progress"
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    estudiante_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    curso_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    porcentaje_avance: Mapped[float] = mapped_column(Float, default=0.0)
    nivel_riesgo: Mapped[str] = mapped_column(String(20), default="bajo", index=True)
    total_interacciones: Mapped[int] = mapped_column(Integer, default=0)
    recursos_completados: Mapped[int] = mapped_column(Integer, default=0)
    puntaje_promedio: Mapped[float] = mapped_column(Float, default=0.0)
    ultima_actividad: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class IndicadorModel(Base):
    __tablename__ = "indicators"
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    progreso_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    valor: Mapped[float] = mapped_column(Float, default=0.0)
    unidad: Mapped[str] = mapped_column(String(50), default="")


class FeedbackModel(Base):
    __tablename__ = "teacher_feedback"
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    docente_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    estudiante_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    curso_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    mensaje: Mapped[str] = mapped_column(String(1000), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), default="general")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
