"""
API Dependencies - Database session
"""
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

# =============================================================================
# Type Aliases
# =============================================================================
DBSession = Annotated[AsyncSession, Depends(get_db)]
