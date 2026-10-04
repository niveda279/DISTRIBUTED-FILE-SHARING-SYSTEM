"""FilePermission model."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class FilePermission(Base):
    __tablename__ = "file_permissions"
    __table_args__ = (UniqueConstraint("file_id", "user_id", name="uq_file_user"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    file_id: Mapped[int] = mapped_column(ForeignKey("files.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    permission: Mapped[str] = mapped_column(String(50), nullable=False, default="VIEW")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    file = relationship("File", back_populates="permissions")
    user = relationship("User", back_populates="permissions")
