"""
Analysis Routes - Text Analysis, Batch Processing, Explanations
"""
import uuid

import structlog
from fastapi import APIRouter, HTTPException, status, BackgroundTasks

from app.api.deps import DBSession
from app.schemas.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    BatchAnalysisRequest,
    BatchAnalysisJobResponse,
    ExplanationResponse,
)
from app.services.analysis_service import analysis_service
from app.services.ml_service import ml_service
from app.services.explain_service import explain_service

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post(
    "",
    response_model=AnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze single text",
)
async def analyze_text(
    request: AnalysisRequest,
    db: DBSession,
) -> AnalysisResponse:
    """
    Analyze a single text for sarcasm and misinformation.

    - Supports Hindi-English (Hinglish), Tamil-English, and pure English
    - Returns sarcasm and misinformation scores with confidence
    - Results are cached for 1 hour by text hash
    """
    if not ml_service.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ML model is not available. Please try again later.",
        )

    try:
        result = await analysis_service.analyze_text(
            db=db,
            text=request.text,
            user=None,
            model=request.model,
            language=request.language or "auto",
        )
        return result
    except Exception as exc:
        logger.error("Analysis failed", exc_info=exc, text=request.text[:100])
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Analysis failed. Please try again.",
        )


@router.post(
    "/batch",
    response_model=BatchAnalysisJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Batch analyze multiple texts",
)
async def analyze_batch(
    request: BatchAnalysisRequest,
    background_tasks: BackgroundTasks,
    db: DBSession,
) -> BatchAnalysisJobResponse:
    """
    Batch analyze multiple texts (runs inline; no Celery required).
    """
    job_id = str(uuid.uuid4())
    total = len(request.texts)

    async def _run_batch():
        for text in request.texts:
            try:
                await analysis_service.analyze_text(
                    db=db, text=text, user=None,
                    language=request.language or "auto"
                )
            except Exception:
                pass

    background_tasks.add_task(_run_batch)
    logger.info("Batch job queued inline", job_id=job_id, total_texts=total)
    return BatchAnalysisJobResponse(job_id=job_id, total_texts=total, status="queued")


@router.get(
    "/{analysis_id}",
    response_model=AnalysisResponse,
    summary="Get analysis result by ID",
)
async def get_analysis(
    analysis_id: uuid.UUID,
    db: DBSession,
) -> AnalysisResponse:
    """Retrieve a specific analysis result by its ID."""
    analysis = await analysis_service.get_by_id(db, analysis_id)
    if not analysis:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analysis not found",
        )

    from app.schemas.analysis import SarcasmResult, MisinformationResult
    return AnalysisResponse(
        id=analysis.id,
        text=analysis.text,
        sarcasm=SarcasmResult.from_score(analysis.sarcasm_score),
        misinformation=MisinformationResult.from_score(analysis.misinformation_score),
        model_version=analysis.model_version,
        language=analysis.language,
        processing_time_ms=analysis.processing_time_ms,
        created_at=analysis.created_at,
        is_cached=analysis.is_cached,
    )


@router.post(
    "/explain",
    response_model=ExplanationResponse,
    summary="Get SHAP/attention explanations",
)
async def explain_analysis(
    request: AnalysisRequest,
    db: DBSession,
) -> ExplanationResponse:
    """
    Generate explainability report for a text.

    - SHAP-based token importance using occlusion
    - Attention weight heatmap from last transformer layer
    - Returns top influential words/tokens
    """
    if not ml_service.is_loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ML model is not available",
        )

    try:
        explanation = await explain_service.get_full_explanation(
            text=request.text,
            analysis_id=uuid.uuid4(),
            ml_service_instance=ml_service,
        )
        return ExplanationResponse(**explanation)
    except Exception as exc:
        logger.error("Explanation failed", exc_info=exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Explanation generation failed",
        )
