"""Pydantic schemas for admin endpoints."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class AdminUserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SystemStats(BaseModel):
    total_users: int
    total_files: int
    total_size_bytes: int
    online_nodes: int
    offline_nodes: int
    total_nodes: int


class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int]
    user_email: Optional[str]
    action: str
    file_id: Optional[int]
    file_name: Optional[str]
    node_id: Optional[str]
    details: Optional[str]
    timestamp: datetime

    model_config = {"from_attributes": True}
