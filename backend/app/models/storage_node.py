"""StorageNode model."""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class StorageNode(Base):
    __tablename__ = "storage_nodes"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    node_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="UNKNOWN")
    total_storage: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    available_storage: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    file_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    avg_latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    last_latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    request_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    file_locations = relationship("FileLocation", back_populates="node")
    metrics = relationship("NodeMetric", foreign_keys="NodeMetric.node_id", primaryjoin="StorageNode.node_id == NodeMetric.node_id")
