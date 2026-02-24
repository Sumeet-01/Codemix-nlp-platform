"""
Analysis SQLAlchemy Model
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.database import Base


class Analysis(Base):
    """Analysis database model."""
    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True, native_uuid=False),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True, native_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    text_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Sarcasm detection results
    sarcasm_score: Mapped[float] = mapped_column(Float, nullable=False)
    sarcasm_label: Mapped[bool] = mapped_column(Boolean, nullable=False)

    # Misinformation detection results
    misinformation_score: Mapped[float] = mapped_column(Float, nullable=False)
    misinformation_label: Mapped[bool] = mapped_column(Boolean, nullable=False)

    # Metadata
    model_version: Mapped[str] = mapped_column(String(100), nullable=False, default="xlm-roberta-v1")
    language: Mapped[str] = mapped_column(String(20), nullable=False, default="auto")
    processing_time_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_cached: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="analyses")  # noqa: F821

    def __repr__(self) -> str:
        return f"<Analysis id={self.id} sarcasm={self.sarcasm_label} misinfo={self.misinformation_label}>"
