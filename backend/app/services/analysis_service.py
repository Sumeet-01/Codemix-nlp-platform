"""
Analysis Service - Core Business Logic for NLP Analysis
"""
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

import structlog
from sqlalchemy import select, func, desc

try:
    from redis.asyncio import Redis as _Redis
except ImportError:  # redis not installed in dev
    _Redis = None
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.analysis import Analysis
from app.models.user import User
from app.schemas.analysis import AnalysisResponse, SarcasmResult, MisinformationResult
from app.services.ml_service import ml_service

logger = structlog.get_logger(__name__)


class AnalysisService:
    """Service for managing text analysis operations."""

    def __init__(self) -> None:
        self._redis: Optional[object] = None

    async def get_redis(self) -> Optional[object]:
        """Get Redis client (lazy initialization). Returns None when Redis is not configured."""
        if not settings.REDIS_URL or _Redis is None:
            return None
        if self._redis is None:
            self._redis = _Redis.from_url(settings.REDIS_URL, decode_responses=True)
        return self._redis

    async def analyze_text(
        self,
        db: AsyncSession,
        text: str,
        user: Optional[User] = None,
        model: Optional[str] = None,
        language: str = "auto",
    ) -> AnalysisResponse:
        """
        Analyze a single text for sarcasm and misinformation.
        Checks Redis cache first, then runs ML inference.
        """
        text_hash = ml_service.hash_text(text)
        redis = await self.get_redis()

        # Check cache (skip if Redis not available)
        cache_key = f"analysis:{text_hash}"
        cached = await redis.get(cache_key) if redis else None
        if cached:
            cached_data = json.loads(cached)
            logger.info("Cache hit", text_hash=text_hash)

            # Still store in DB for user history
            if user:
                await self._save_to_db(
                    db,
                    text=text,
                    text_hash=text_hash,
                    user=user,
                    result=cached_data,
                    is_cached=True,
                    language=language,
                )

            return AnalysisResponse(
                id=uuid.uuid4(),
                text=text,
                sarcasm=SarcasmResult.from_score(cached_data["sarcasm_score"]),
                misinformation=MisinformationResult.from_score(cached_data["misinformation_score"]),
                model_version=cached_data["model_version"],
                language=language,
                processing_time_ms=cached_data["processing_time_ms"],
                created_at=datetime.now(timezone.utc),
                is_cached=True,
            )

        # Run ML inference
        result = await ml_service.predict(text)

        # Cache result
        cache_data = {
            "sarcasm_score": result["sarcasm_score"],
            "sarcasm_label": result["sarcasm_label"],
            "misinformation_score": result["misinformation_score"],
            "misinformation_label": result["misinformation_label"],
            "model_version": result["model_version"],
            "processing_time_ms": result["processing_time_ms"],
        }
        if redis:
            await redis.setex(cache_key, settings.CACHE_TTL, json.dumps(cache_data))
            logger.info("Result cached", text_hash=text_hash)

        # Save to DB
        analysis = await self._save_to_db(
            db,
            text=text,
            text_hash=text_hash,
            user=user,
            result=result,
            is_cached=False,
            language=language,
        )

        return AnalysisResponse(
            id=analysis.id,
            text=text,
            sarcasm=SarcasmResult.from_score(result["sarcasm_score"]),
            misinformation=MisinformationResult.from_score(result["misinformation_score"]),
            model_version=result["model_version"],
            language=language,
            processing_time_ms=result["processing_time_ms"],
            created_at=analysis.created_at,
            is_cached=False,
        )

    async def _save_to_db(
        self,
        db: AsyncSession,
        text: str,
        text_hash: str,
        user: Optional[User],
        result: dict,
        is_cached: bool,
        language: str,
    ) -> Analysis:
        """Persist analysis result to database."""
        analysis = Analysis(
            id=uuid.uuid4(),
            user_id=user.id if user else None,
            text=text,
            text_hash=text_hash,
            sarcasm_score=result["sarcasm_score"],
            sarcasm_label=result["sarcasm_label"],
            misinformation_score=result["misinformation_score"],
            misinformation_label=result["misinformation_label"],
            model_version=result["model_version"],
            language=language,
            processing_time_ms=result["processing_time_ms"],
            is_cached=is_cached,
        )
        db.add(analysis)
        await db.flush()
        await db.refresh(analysis)
        return analysis

    async def get_by_id(
        self, db: AsyncSession, analysis_id: uuid.UUID
    ) -> Optional[Analysis]:
        """Get analysis by ID."""
        result = await db.execute(
            select(Analysis).where(Analysis.id == analysis_id)
        )
        return result.scalar_one_or_none()

    async def get_user_history(
        self,
        db: AsyncSession,
        user: User,
        page: int = 1,
        page_size: int = 20,
        limit: int = 0,   # legacy, ignored when page used
        offset: int = 0,  # legacy
        search: Optional[str] = None,
        sarcasm_filter: Optional[str] = None,
        misinfo_filter: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> tuple[list[Analysis], int]:
        """Get user's analysis history with filters."""
        query = select(Analysis)
        if user:
            query = query.where(Analysis.user_id == user.id)

        if search:
            query = query.where(Analysis.text.ilike(f"%{search}%"))
        # Accept both bool filter and string label filter
        if sarcasm_filter is not None:
            if isinstance(sarcasm_filter, str):
                query = query.where(Analysis.sarcasm_label == (sarcasm_filter == "SARCASTIC"))
            else:
                query = query.where(Analysis.sarcasm_label == sarcasm_filter)
        if misinfo_filter is not None:
            if isinstance(misinfo_filter, str):
                query = query.where(Analysis.misinformation_label == (misinfo_filter == "MISINFORMATION"))
            else:
                query = query.where(Analysis.misinformation_label == misinfo_filter)
        if date_from:
            query = query.where(Analysis.created_at >= date_from)
        if date_to:
            query = query.where(Analysis.created_at <= date_to)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        # Paginate using page/page_size
        real_limit = page_size or 20
        real_offset = (max(page, 1) - 1) * real_limit
        query = query.order_by(desc(Analysis.created_at)).offset(real_offset).limit(real_limit)
        result = await db.execute(query)
        analyses = result.scalars().all()

        return list(analyses), total

    async def get_dashboard_stats(
        self, db: AsyncSession, user: Optional[User] = None
    ) -> dict:
        """Get analytics stats for dashboard."""
        base_query = select(Analysis)
        if user:
            base_query = base_query.where(Analysis.user_id == user.id)

        # Last 30 days
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        recent_query = base_query.where(Analysis.created_at >= thirty_days_ago)

        # Total analyses
        total = await db.scalar(
            select(func.count()).select_from(base_query.subquery())
        )
        # Recent analyses
        recent = await db.scalar(
            select(func.count()).select_from(recent_query.subquery())
        )
        # Sarcasm detected
        sarcasm_query = recent_query.where(Analysis.sarcasm_label.is_(True))
        sarcasm_count = await db.scalar(
            select(func.count()).select_from(sarcasm_query.subquery())
        )
        # Misinformation detected
        misinfo_query = recent_query.where(Analysis.misinformation_label.is_(True))
        misinfo_count = await db.scalar(
            select(func.count()).select_from(misinfo_query.subquery())
        )
        # Avg processing time
        avg_time = await db.scalar(
            select(func.avg(Analysis.processing_time_ms)).select_from(
                recent_query.subquery()
            )
        )

        # Daily stats for chart — last 14 days
        from sqlalchemy import cast, Date as SADate, text
        daily_rows = await db.execute(
            recent_query.order_by(desc(Analysis.created_at))
        )
        all_recent = daily_rows.scalars().all()

        # Group by date in Python (SQLite-safe)
        daily_map: dict = {}
        for a in all_recent:
            try:
                d = a.created_at.date().isoformat() if hasattr(a.created_at, "date") else str(a.created_at)[:10]
            except Exception:
                d = str(a.created_at)[:10]
            if d not in daily_map:
                daily_map[d] = {"date": d, "count": 0, "sarcasm_count": 0, "misinfo_count": 0}
            daily_map[d]["count"] += 1
            if a.sarcasm_label:
                daily_map[d]["sarcasm_count"] += 1
            if a.misinformation_label:
                daily_map[d]["misinfo_count"] += 1
        daily_stats = sorted(daily_map.values(), key=lambda x: x["date"])[-14:]

        n_recent = recent or 1
        return {
            "total_analyses": total or 0,
            "sarcasm_detected": sarcasm_count or 0,
            "misinformation_detected": misinfo_count or 0,
            "avg_processing_time_ms": round(avg_time or 0, 2),
            "cache_hit_rate": 0.0,
            "daily_stats": daily_stats,
            # keep legacy names too for other consumers
            "recent_analyses_30d": recent or 0,
            "sarcasm_rate": round((sarcasm_count or 0) / n_recent * 100, 1),
            "misinfo_rate": round((misinfo_count or 0) / n_recent * 100, 1),
        }


analysis_service = AnalysisService()
