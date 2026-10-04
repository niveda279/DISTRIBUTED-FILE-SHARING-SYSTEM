"""Pydantic schemas for files, locations, permissions."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class FileLocationResponse(BaseModel):
    node_id: str
    location_type: str
    status: str

    model_config = {"from_attributes": True}


class FilePermissionResponse(BaseModel):
    user_id: int
    user_email: str
    user_name: str
    permission: str
    created_at: datetime

    model_config = {"from_attributes": True}


class FileResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    size: int
    mime_type: Optional[str]
    owner_id: int
    owner_name: str
    owner_email: str
    checksum: str
    primary_node_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    locations: List[FileLocationResponse] = []
    user_permission: Optional[str] = None

    model_config = {"from_attributes": True}


class ShareRequest(BaseModel):
    email: str
    permission: str = "DOWNLOAD"  # VIEW | DOWNLOAD | MANAGE


class UpdatePermissionRequest(BaseModel):
    permission: str


class PermissionCreate(BaseModel):
    shared_with_email: str
    permission: str = "VIEW"  # VIEW | DOWNLOAD | MANAGE


class PermissionResponse(BaseModel):
    id: int
    file_id: int
    shared_with_id: int
    shared_with_email: str
    shared_with_name: str
    permission: str
    created_at: datetime

    model_config = {"from_attributes": True}


class SearchParams(BaseModel):
    q: Optional[str] = None
    file_type: Optional[str] = None
    owner: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
