"""FileLocation model – tracks which node holds which copy."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class FileLocation(Base):
    __tablename__ = "file_locations"
    __table_args__ = (UniqueConstraint("file_id", "node_id", name="uq_file_node"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id", ondelete="CASCADE"), nullable=False)
    node_id: Mapped[str] = mapped_column(
        ForeignKey("storage_nodes.node_id", ondelete="CASCADE"), nullable=False
    )
    location_type: Mapped[str] = mapped_column(String(50), nullable=False)   # PRIMARY | REPLICA
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="ACTIVE")  # ACTIVE | FAILED
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    file = relationship("File", back_populates="locations")
    node = relationship("StorageNode", back_populates="file_locations")
