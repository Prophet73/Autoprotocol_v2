"""
Schemas for admin user management endpoints.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr

from backend.shared.models import UserRole, Domain


class UserResponse(BaseModel):
    """User information response."""
    id: int
    email: str
    full_name: Optional[str]
    is_active: bool
    is_superuser: bool
    role: str
    domain: Optional[str]  # Legacy single domain
    domains: List[str] = []  # Multiple domains
    active_domain: Optional[str] = None  # Currently selected domain
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """List of users response."""
    users: List[UserResponse]
    total: int


class AssignRoleRequest(BaseModel):
    """Request to assign role and domain to user."""
    user_id: int
    role: UserRole
    domain: Optional[Domain] = None


class AssignRoleResponse(BaseModel):
    """Response after role assignment."""
    message: str
    user: UserResponse


class CreateUserRequest(BaseModel):
    """Request to create a new user (admin only)."""
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: UserRole = UserRole.USER
    domain: Optional[Domain] = None
    is_superuser: bool = False


class UpdateUserRequest(BaseModel):
    """Request to update user details."""
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    role: Optional[UserRole] = None
    domain: Optional[Domain] = None
    domains: Optional[List[str]] = None  # Set multiple domains
    active_domain: Optional[str] = None  # Set active domain


# Domain management schemas
class AssignDomainsRequest(BaseModel):
    """Request to assign multiple domains to user."""
    user_id: int
    domains: List[str]  # ["construction", "hr", "it"]


class SetActiveDomainRequest(BaseModel):
    """Request to set user's active domain."""
    domain: str


# Project access schemas
class GrantProjectAccessRequest(BaseModel):
    """Request to grant user access to a project."""
    user_id: int
    project_id: int


class RevokeProjectAccessRequest(BaseModel):
    """Request to revoke user access from a project."""
    user_id: int
    project_id: int


class ProjectAccessResponse(BaseModel):
    """Response for project access operations."""
    user_id: int
    project_id: int
    granted: bool
    message: str


class UserProjectAccessList(BaseModel):
    """List of projects user has access to."""
    user_id: int
    project_ids: List[int]


class ProjectUserAccessList(BaseModel):
    """List of users who have access to a project."""
    project_id: int
    user_ids: List[int]
    users: List[UserResponse] = []  # Optional: full user info
