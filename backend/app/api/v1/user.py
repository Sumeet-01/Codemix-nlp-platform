"""
User Routes - Profile, History, API Keys
"""
import structlog
from fastapi import APIRouter, HTTPException, Query, status
from typing import Optional
from datetime import datetime

from app.api.deps import DBSession, CurrentUser
from app.schemas.user import UserResponse, UserUpdate
from app.schemas.analysis import AnalysisResponse, SarcasmResult, MisinformationResult
from app.services.user_service import user_service
from app.services.analysis_service import analysis_service

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/me", response_model=UserResponse, summary="Get current user profile")
async def get_profile(current_user: CurrentUser) -> UserResponse:
    """Get the authenticated user's profile."""
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse, summary="Update profile")
async def update_profile(
    update_data: UserUpdate,
    db: DBSession,
    current_user: CurrentUser,
) -> UserResponse:
    """Update the authenticated user's profile."""
    try:
        user = await user_service.update_user(db, current_user, update_data)
        return UserResponse.model_validate(user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/history", summary="Get analysis history")
async def get_history(
    db: DBSession,
    current_user: CurrentUser,
    search: Optional[str] = Query(None, max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sarcasm_label: Optional[str] = Query(None),
    misinfo_label: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
) -> dict:
    """
    Get user's analysis history with search and filters.
    
    - Filter by sarcasm/misinformation labels
    - Search by text content
    - Date range filtering
    - Paginated results
    """
    analyses, total = await analysis_service.get_user_history(
        db=db,
        user=current_user,
        page=page,
        page_size=page_size,
        search=search,
        sarcasm_filter=sarcasm_label,
        misinfo_filter=misinfo_label,
        date_from=start_date,
        date_to=end_date,
    )

    items = [
        AnalysisResponse(
            id=a.id,
            text=a.text,
            sarcasm=SarcasmResult.from_score(a.sarcasm_score),
            misinformation=MisinformationResult.from_score(a.misinformation_score),
            model_version=a.model_version,
            language=a.language,
            processing_time_ms=a.processing_time_ms,
            created_at=a.created_at,
            is_cached=a.is_cached,
        )
        for a in analyses
    ]

    total_pages = max(1, -(-total // page_size))  # ceiling division
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.post("/api-key", summary="Generate API key")
async def generate_api_key(
    db: DBSession,
    current_user: CurrentUser,
) -> dict:
    """Generate a new API key for the authenticated user."""
    api_key = await user_service.generate_api_key_for_user(db, current_user)
    return {"api_key": api_key, "message": "Store this key securely. It won't be shown again."}


@router.delete("/api-key", status_code=status.HTTP_204_NO_CONTENT, summary="Revoke API key")
async def revoke_api_key(
    db: DBSession,
    current_user: CurrentUser,
) -> None:
    """Revoke the user's API key."""
    await user_service.revoke_api_key(db, current_user)
