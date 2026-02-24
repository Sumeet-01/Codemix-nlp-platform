"""
User Service - Business Logic for User Management
"""
import uuid
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password, generate_api_key
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate

logger = structlog.get_logger(__name__)


class UserService:
    """Service for user management operations."""

    async def create_user(self, db: AsyncSession, user_data: UserCreate) -> User:
        """Create a new user."""
        # Check if email already exists
        existing = await self.get_by_email(db, user_data.email)
        if existing:
            raise ValueError(f"User with email {user_data.email} already exists")

        user = User(
            id=uuid.uuid4(),
            email=user_data.email.lower(),
            password_hash=hash_password(user_data.password),
            full_name=user_data.full_name,
            is_active=True,
            is_verified=False,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        logger.info("User created", user_id=str(user.id), email=user.email)
        return user

    async def get_by_id(self, db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
        """Get user by ID."""
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """Get user by email address."""
        result = await db.execute(
            select(User).where(User.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def get_by_api_key(self, db: AsyncSession, api_key: str) -> Optional[User]:
        """Get user by API key."""
        result = await db.execute(
            select(User).where(User.api_key == api_key)
        )
        return result.scalar_one_or_none()

    async def authenticate(
        self, db: AsyncSession, email: str, password: str
    ) -> Optional[User]:
        """Authenticate user with email/password."""
        user = await self.get_by_email(db, email)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        if not user.is_active:
            return None
        logger.info("User authenticated", user_id=str(user.id))
        return user

    async def update_user(
        self, db: AsyncSession, user: User, update_data: UserUpdate
    ) -> User:
        """Update user profile."""
        if update_data.full_name is not None:
            user.full_name = update_data.full_name
        if update_data.email is not None:
            # Check if email is taken
            existing = await self.get_by_email(db, update_data.email)
            if existing and existing.id != user.id:
                raise ValueError("Email already in use")
            user.email = update_data.email.lower()
        await db.flush()
        await db.refresh(user)
        return user

    async def generate_api_key_for_user(
        self, db: AsyncSession, user: User
    ) -> str:
        """Generate and assign a new API key to the user."""
        api_key = generate_api_key()
        user.api_key = api_key
        await db.flush()
        return api_key

    async def revoke_api_key(self, db: AsyncSession, user: User) -> None:
        """Revoke user's API key."""
        user.api_key = None
        await db.flush()


user_service = UserService()
