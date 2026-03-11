"""
Hub User Sync Service.

Synchronizes users from Hub to local AutoProtocol database.
Can be run manually via admin endpoint or scheduled.

Authentication methods (in order of preference):
1. HUB_SERVICE_TOKEN - Service account JWT token (best for automation)
2. Client credentials - Uses HUB_CLIENT_ID/SECRET to get token (requires Hub support)
3. Manual - Admin copies their JWT token temporarily
"""
import os
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.shared.models import User


# Hub Configuration
HUB_URL = os.getenv("HUB_URL", "https://ai-hub.svrd.ru")
HUB_SERVICE_TOKEN = os.getenv("HUB_SERVICE_TOKEN", "")  # Service account token for sync
HUB_CLIENT_ID = os.getenv("HUB_CLIENT_ID", "")
HUB_CLIENT_SECRET = os.getenv("HUB_CLIENT_SECRET", "")


class HubSyncService:
    """Service for syncing users from Hub."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.hub_url = HUB_URL
        self.service_token = HUB_SERVICE_TOKEN

    async def get_auth_token(self) -> str:
        """
        Get authentication token for Hub API.

        Tries in order:
        1. HUB_SERVICE_TOKEN env var
        2. Client credentials flow (if Hub supports it)
        """
        if self.service_token:
            return self.service_token

        # Try client credentials flow
        if HUB_CLIENT_ID and HUB_CLIENT_SECRET:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.hub_url}/oauth/token",
                    data={
                        "grant_type": "client_credentials",
                        "client_id": HUB_CLIENT_ID,
                        "client_secret": HUB_CLIENT_SECRET,
                        "scope": "users:read",
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                if response.status_code == 200:
                    tokens = response.json()
                    return tokens.get("access_token", "")

        raise ValueError(
            "Hub sync not configured. Set HUB_SERVICE_TOKEN or ensure Hub supports client_credentials grant."
        )

    async def fetch_hub_users(self) -> list[dict]:
        """
        Fetch all users from Hub API.

        Requires either HUB_SERVICE_TOKEN or client_credentials support in Hub.
        """
        token = await self.get_auth_token()

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.hub_url}/api/users",
                headers={"Authorization": f"Bearer {token}"},
                params={"limit": 1000}  # Adjust as needed
            )

            if response.status_code == 401:
                raise PermissionError("Hub token is invalid or expired")

            if response.status_code != 200:
                raise Exception(f"Failed to fetch users from Hub: {response.status_code} - {response.text}")

            data = response.json()
            # Handle both list and paginated response
            if isinstance(data, list):
                return data
            return data.get("items", data.get("users", []))

    def map_hub_user_to_local(self, hub_user: dict) -> dict:
        """
        Map Hub user fields to local User model.

        Hub User fields:
        - id, sso_id, email, display_name, first_name, last_name, middle_name
        - department, job_title, ad_groups, is_active, is_admin, is_super_admin

        Local User fields:
        - email, full_name, is_active, is_superuser, role, domain, sso_provider, sso_id
        """
        # Build full name from Hub fields
        full_name = hub_user.get("display_name")
        if not full_name:
            parts = []
            if hub_user.get("last_name"):
                parts.append(hub_user["last_name"])
            if hub_user.get("first_name"):
                parts.append(hub_user["first_name"])
            if hub_user.get("middle_name"):
                parts.append(hub_user["middle_name"])
            full_name = " ".join(parts) if parts else None

        # Determine role based on Hub admin flags
        is_super_admin = hub_user.get("is_super_admin", False)
        is_admin = hub_user.get("is_admin", False)

        if is_super_admin:
            role = "admin"
            is_superuser = True
        elif is_admin:
            role = "admin"
            is_superuser = False
        else:
            role = "user"
            is_superuser = False

        # Map department to domain (optional logic)
        department = hub_user.get("department", "").lower()
        domain = None
        if "строит" in department or "констр" in department or "construction" in department:
            domain = "construction"
        elif "it" in department or "ит" in department or "разработ" in department:
            domain = "it"

        return {
            "email": hub_user.get("email"),
            "full_name": full_name,
            "is_active": hub_user.get("is_active", True),
            "is_superuser": is_superuser,
            "role": role,
            "domain": domain,
            "sso_provider": "hub",
            "sso_id": str(hub_user.get("sso_id") or hub_user.get("id")),
        }

    async def sync_user(self, hub_user: dict) -> tuple[User, bool]:
        """
        Sync a single user from Hub to local database.

        Returns:
            Tuple of (User, created) where created is True if new user was created.
        """
        mapped = self.map_hub_user_to_local(hub_user)

        if not mapped["email"]:
            raise ValueError(f"Hub user has no email: {hub_user}")

        # Try to find existing user by email or sso_id
        result = await self.db.execute(
            select(User).where(
                (User.email == mapped["email"]) |
                ((User.sso_provider == "hub") & (User.sso_id == mapped["sso_id"]))
            )
        )
        user = result.scalar_one_or_none()

        created = False
        if user is None:
            # Create new user
            user = User(
                email=mapped["email"],
                full_name=mapped["full_name"],
                hashed_password="!SSO_ONLY_NO_PASSWORD_LOGIN",  # Sentinel — SSO users cannot log in with password
                is_active=mapped["is_active"],
                is_superuser=mapped["is_superuser"],
                role=mapped["role"],
                domain=mapped["domain"],
                sso_provider="hub",
                sso_id=mapped["sso_id"],
            )
            self.db.add(user)
            created = True
        else:
            # Update existing user
            user.full_name = mapped["full_name"] or user.full_name
            user.is_active = mapped["is_active"]
            # Don't downgrade admins that were promoted locally
            if mapped["is_superuser"] and not user.is_superuser:
                user.is_superuser = True
                user.role = "admin"
            user.sso_provider = "hub"
            user.sso_id = mapped["sso_id"]
            # Update domain only if not set locally
            if not user.domain and mapped["domain"]:
                user.domain = mapped["domain"]

        return user, created

    async def sync_all_users(self) -> dict:
        """
        Sync all users from Hub to local database.

        Returns:
            Dict with sync statistics.
        """
        hub_users = await self.fetch_hub_users()

        stats = {
            "total": len(hub_users),
            "created": 0,
            "updated": 0,
            "errors": [],
            "synced_at": datetime.now(timezone.utc).isoformat(),
        }

        for hub_user in hub_users:
            try:
                user, created = await self.sync_user(hub_user)
                if created:
                    stats["created"] += 1
                else:
                    stats["updated"] += 1
            except Exception as e:
                stats["errors"].append({
                    "email": hub_user.get("email", "unknown"),
                    "error": str(e)
                })

        await self.db.commit()
        return stats


async def sync_users_from_hub(db: AsyncSession) -> dict:
    """
    Convenience function to sync users from Hub.

    Usage:
        from backend.core.auth.hub_sync import sync_users_from_hub
        stats = await sync_users_from_hub(db)
    """
    service = HubSyncService(db)
    return await service.sync_all_users()
