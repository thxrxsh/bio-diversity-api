from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class RecordingChunk(Base):
    __tablename__ = "recording_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    recording_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("recordings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_sec: Mapped[float] = mapped_column(Float, nullable=False)
    end_sec: Mapped[float] = mapped_column(Float, nullable=False)

    label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_leopard: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    leopard_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    non_leopard_probability: Mapped[float | None] = mapped_column(Float, nullable=True)

    distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    distance_min_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    distance_max_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    distance_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    recording: Mapped["Recording"] = relationship(
        "Recording",
        back_populates="chunks",
        foreign_keys=[recording_id],
    )
