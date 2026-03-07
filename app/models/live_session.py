from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class LiveSession(Base):
    __tablename__ = "live_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    device_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")

    overall_is_leopard: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    best_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    last_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)

    started_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_detected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    best_chunk_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("live_chunks.id", ondelete="SET NULL"),
        nullable=True,
    )

    chunks: Mapped[list["LiveChunk"]] = relationship(
        "LiveChunk",
        back_populates="live_session",
        cascade="all, delete-orphan",
        foreign_keys="LiveChunk.live_session_id",
    )

    best_chunk: Mapped["LiveChunk | None"] = relationship(
        "LiveChunk",
        foreign_keys=[best_chunk_id],
        post_update=True,
    )
