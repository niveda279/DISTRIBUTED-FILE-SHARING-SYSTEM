"""File model."""
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class File(Base):
    __tablename__ = "files"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)           # stored/physical ID
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)  # user-supplied name
    size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    mime_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    primary_node_id: Mapped[str | None] = mapped_column(
        ForeignKey("storage_nodes.node_id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    # Versioning
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    parent_file_id: Mapped[int | None] = mapped_column(
        ForeignKey("files.id", ondelete="SET NULL"), nullable=True
    )
    is_current_version: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Deduplication
    is_deduplicated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    dedup_source_file_id: Mapped[int | None] = mapped_column(
        ForeignKey("files.id", ondelete="SET NULL"), nullable=True
    )
    # Access tracking
    access_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    owner = relationship("User", back_populates="files")
    locations = relationship("FileLocation", back_populates="file", cascade="all, delete-orphan")
    permissions = relationship("FilePermission", back_populates="file", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="file")
    primary_node = relationship("StorageNode", foreign_keys=[primary_node_id])
    versions = relationship("FileVersion", back_populates="file", foreign_keys="FileVersion.file_id", cascade="all, delete-orphan")
