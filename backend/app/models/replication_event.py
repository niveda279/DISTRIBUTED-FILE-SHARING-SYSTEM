"""ReplicationEvent model."""
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class ReplicationEvent(Base):
    __tablename__ = "replication_events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    file_id: Mapped[int | None] = mapped_column(ForeignKey("files.id", ondelete="SET NULL"), nullable=True)
    source_node: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_node: Mapped[str | None] = mapped_column(String(100), nullable=True)
    trigger: Mapped[str] = mapped_column(String(100), nullable=False, default="AUTO_HEAL")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    file = relationship("File", foreign_keys=[file_id])
