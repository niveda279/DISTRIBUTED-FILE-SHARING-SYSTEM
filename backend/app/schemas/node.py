"""Pydantic schemas for storage nodes."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class NodeResponse(BaseModel):
    id: int
    node_id: str
    name: str
    host: str
    port: int
    status: str
    total_storage: int
    available_storage: int
    file_count: int
    last_heartbeat: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class NodeHealthResponse(BaseModel):
    node_id: str
    status: str
    available_storage: int
    total_storage: int
    file_count: int
    timestamp: str
