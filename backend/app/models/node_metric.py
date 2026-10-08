"""NodeMetric model."""
from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class NodeMetric(Base):
    __tablename__ = "node_metrics"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    node_id: Mapped[str] = mapped_column(
        ForeignKey("storage_nodes.node_id", ondelete="CASCADE"), nullable=False
    )
    sampled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    available_storage: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    used_storage: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    file_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    request_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_online: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    placement_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)

    node = relationship("StorageNode", foreign_keys=[node_id])
