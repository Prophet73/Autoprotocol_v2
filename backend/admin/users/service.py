"""
Admin user management service.

Provides business logic for:
- Listing users with roles
- Assigning roles and domains
- Creating and updating users
"""
from typing import Optional, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.shared.models import User, UserRole, Domain
from backend.core.auth.dependencies import get_password_hash
from .schemas import (
    UserResponse,
    UserListResponse,
    AssignRoleRequest,
    CreateUserRequest,
    UpdateUserRequest,
)


class UserService:
    """Service for admin user management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_users(
        self,
        skip: int = 0,
        limit: int = 100,
        role_filter: Optional[UserRole] = None,
        domain_filter: Optional[Domain] = None,
    ) -> UserListResponse:
        """
        List all users with optional filtering.

        Args:
            skip: Number of records to skip (pagination)
            limit: Maximum records to return
            role_filter: Filter by role
            domain_filter: Filter by domain

        Returns:
            UserListResponse with users list and total count
        """
        query = select(User)

        if role_filter:
            query = query.where(User.role == role_filter.value)
        if domain_filter:
            query = query.where(User.domain == domain_filter.value)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Get paginated results
        query = query.offset(skip).limit(limit).order_by(User.created_at.desc())
        result = await self.db.execute(query)
        users = result.scalars().all()

        return UserListResponse(
            users=[UserResponse.model_validate(u) for u in users],
            total=total
        )

    async def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def assign_role(self, request: AssignRoleRequest) -> User:
        """
        Assign role and domain to a user.

        Args:
            request: Role assignment request

        Returns:
            Updated user

        Raises:
            ValueError: If user not found
        """
        user = await self.get_user(request.user_id)
        if not user:
            raise ValueError(f"User with id {request.user_id} not found")

        user.role = request.role.value
        if request.domain:
            user.domain = request.domain.value
        else:
            user.domain = None

        # Auto-update superuser flag based on role
        if request.role == UserRole.SUPERUSER:
            user.is_superuser = True

        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def create_user(self, request: CreateUserRequest) -> User:
        """
        Create a new user.

        Args:
            request: User creation request

        Returns:
            Created user

        Raises:
            ValueError: If email already exists
        """
        existing = await self.get_user_by_email(request.email)
        if existing:
            raise ValueError(f"User with email {request.email} already exists")

        user = User(
            email=request.email,
            hashed_password=get_password_hash(request.password),
            full_name=request.full_name,
            role=request.role.value,
            domain=request.domain.value if request.domain else None,
            is_superuser=request.is_superuser or request.role == UserRole.SUPERUSER,
            is_active=True,
        )

        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def update_user(self, user_id: int, request: UpdateUserRequest) -> User:
        """
        Update user details.

        Args:
            user_id: User ID to update
            request: Update request

        Returns:
            Updated user

        Raises:
            ValueError: If user not found
        """
        user = await self.get_user(user_id)
        if not user:
            raise ValueError(f"User with id {user_id} not found")

        if request.full_name is not None:
            user.full_name = request.full_name
        if request.is_active is not None:
            user.is_active = request.is_active
        if request.is_superuser is not None:
            user.is_superuser = request.is_superuser
        if request.role is not None:
            user.role = request.role.value
            if request.role == UserRole.SUPERUSER:
                user.is_superuser = True
        if request.domain is not None:
            user.domain = request.domain.value

        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def delete_user(self, user_id: int) -> bool:
        """
        Delete a user.

        Args:
            user_id: User ID to delete

        Returns:
            True if deleted, False if not found
        """
        user = await self.get_user(user_id)
        if not user:
            return False

        await self.db.delete(user)
        await self.db.flush()
        return True
