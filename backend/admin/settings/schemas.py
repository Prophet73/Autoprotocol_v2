"""
Schemas for system settings endpoints.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class SettingResponse(BaseModel):
    """System setting response."""
    key: str
    value: str
    description: Optional[str]
    updated_at: datetime
    updated_by: Optional[str]

    class Config:
        from_attributes = True


class SettingListResponse(BaseModel):
    """List of settings response."""
    settings: List[SettingResponse]
    total: int


class CreateSettingRequest(BaseModel):
    """Request to create a new setting."""
    key: str
    value: str
    description: Optional[str] = None


class UpdateSettingRequest(BaseModel):
    """Request to update a setting value."""
    value: str
    description: Optional[str] = None


class SettingBulkUpdateRequest(BaseModel):
    """Request to update multiple settings at once."""
    settings: dict[str, str]  # key -> value mapping
