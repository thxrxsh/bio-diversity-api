from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Recording(Base):
    __tablename__ = "recordings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    saved_path: Mapped[str] = mapped_column(String(500), nullable=False)
    device_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="uploaded")

    overall_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    overall_is_leopard: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    best_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    best_chunk_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("recording_chunks.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    chunks: Mapped[list["RecordingChunk"]] = relationship(
        "RecordingChunk",
        back_populates="recording",
        cascade="all, delete-orphan",
        foreign_keys="RecordingChunk.recording_id",
    )

    best_chunk: Mapped["RecordingChunk | None"] = relationship(
        "RecordingChunk",
        foreign_keys=[best_chunk_id],
        post_update=True,
    )
