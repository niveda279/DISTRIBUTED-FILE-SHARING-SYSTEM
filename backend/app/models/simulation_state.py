"""SimulationState model."""
from datetime import datetime
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class SimulationState(Base):
    __tablename__ = "simulation_state"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    node_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    is_simulated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    simulated_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    simulated_latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    simulated_load_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    simulated_storage_warning: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
