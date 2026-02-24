"""
Models Routes - Available Models Information
"""
import structlog
from fastapi import APIRouter

from app.services.ml_service import ml_service

logger = structlog.get_logger(__name__)
router = APIRouter()

AVAILABLE_MODELS = [
    {
        "id": "xlm-roberta",
        "name": "XLM-RoBERTa Large",
        "description": "Best multilingual performance. Fine-tuned on code-mixed Indian text.",
        "base_model": "xlm-roberta-large",
        "languages": ["hi-en", "ta-en", "en", "hi", "ta"],
        "is_default": True,
        "max_length": 128,
    },
    {
        "id": "mbert",
        "name": "mBERT",
        "description": "Multilingual BERT. Faster inference, good for batch processing.",
        "base_model": "bert-base-multilingual-cased",
        "languages": ["hi-en", "ta-en", "en"],
        "is_default": False,
        "max_length": 128,
    },
    {
        "id": "indicbert",
        "name": "IndicBERT",
        "description": "Specialized for Indic languages. Best for pure Hindi/Tamil.",
        "base_model": "ai4bharat/indic-bert",
        "languages": ["hi", "ta", "hi-en", "ta-en"],
        "is_default": False,
        "max_length": 128,
    },
]


@router.get("", summary="List available models")
async def list_models() -> dict:
    """List all available models for analysis."""
    return {
        "models": AVAILABLE_MODELS,
        "active_model": ml_service.model_version,
        "model_loaded": ml_service.is_loaded,
        "device": getattr(ml_service, "device", "cpu"),
    }


@router.get("/{model_id}", summary="Get model details")
async def get_model(model_id: str) -> dict:
    """Get detailed information about a specific model."""
    model = next((m for m in AVAILABLE_MODELS if m["id"] == model_id), None)
    if not model:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model '{model_id}' not found",
        )
    return model
