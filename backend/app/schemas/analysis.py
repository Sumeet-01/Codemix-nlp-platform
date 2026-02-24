"""
Analysis Pydantic Schemas
"""
import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class AnalysisRequest(BaseModel):
    """Schema for single text analysis request."""
    text: str = Field(..., min_length=1, max_length=500, description="Text to analyze")
    model: Optional[str] = Field(None, description="Model to use (xlm-roberta, mbert, indicbert)")
    language: Optional[str] = Field("auto", description="Language hint: hi-en, ta-en, auto")

    @field_validator("text")
    @classmethod
    def sanitize_text(cls, v: str) -> str:
        # Strip leading/trailing whitespace
        v = v.strip()
        if not v:
            raise ValueError("Text cannot be empty")
        return v


class BatchAnalysisRequest(BaseModel):
    """Schema for batch analysis request."""
    texts: List[str] = Field(..., min_length=1, max_length=100, description="List of texts to analyze")
    model: Optional[str] = None
    language: Optional[str] = Field("auto", description="Language hint")

    @field_validator("texts")
    @classmethod
    def validate_texts(cls, v: List[str]) -> List[str]:
        if len(v) > 100:
            raise ValueError("Maximum 100 texts per batch")
        cleaned = []
        for text in v:
            t = text.strip()
            if t:
                cleaned.append(t[:500])  # Truncate to max length
        return cleaned


def _confidence_band(score: float) -> str:
    """Convert 0-1 float to HIGH/MEDIUM/LOW string."""
    if score >= 0.75:
        return "HIGH"
    elif score >= 0.45:
        return "MEDIUM"
    return "LOW"


class SarcasmResult(BaseModel):
    """Sarcasm detection result."""
    score: float = Field(..., ge=0.0, le=1.0)
    label: str  # "SARCASTIC" | "NOT_SARCASTIC"
    confidence: str  # "HIGH" | "MEDIUM" | "LOW"

    @classmethod
    def from_score(cls, score: float) -> "SarcasmResult":
        return cls(
            score=round(score, 4),
            label="SARCASTIC" if score >= 0.5 else "NOT_SARCASTIC",
            confidence=_confidence_band(score if score >= 0.5 else 1 - score),
        )


class MisinformationResult(BaseModel):
    """Misinformation detection result."""
    score: float = Field(..., ge=0.0, le=1.0)
    label: str  # "MISINFORMATION" | "CREDIBLE"
    confidence: str  # "HIGH" | "MEDIUM" | "LOW"

    @classmethod
    def from_score(cls, score: float) -> "MisinformationResult":
        return cls(
            score=round(score, 4),
            label="MISINFORMATION" if score >= 0.5 else "CREDIBLE",
            confidence=_confidence_band(score if score >= 0.5 else 1 - score),
        )


class AnalysisResponse(BaseModel):
    """Schema for single analysis response."""
    id: uuid.UUID
    text: str
    sarcasm: SarcasmResult
    misinformation: MisinformationResult
    model_version: str
    language: str
    processing_time_ms: int
    created_at: datetime
    is_cached: bool = False

    model_config = {"from_attributes": True}


class BatchAnalysisJobResponse(BaseModel):
    """Schema for batch analysis job response."""
    job_id: str
    total_texts: int
    status: str = "queued"
    message: str = "Batch job submitted successfully. Use job_id to check status."


class BatchJobStatusResponse(BaseModel):
    """Schema for batch job status response."""
    job_id: str
    status: str  # queued, processing, completed, failed
    total: int
    completed: int
    failed: int
    results: Optional[List[AnalysisResponse]] = None


class ShapValue(BaseModel):
    """SHAP token importance value — matches frontend ShapValue interface."""
    token: str
    sarcasm_score: float
    misinfo_score: float


class ExplanationResponse(BaseModel):
    """Schema for explanation response."""
    analysis_id: str
    tokens: List[str]
    shap_values: List[ShapValue]
    attention_weights: Optional[List[List[float]]] = None
    top_sarcasm_tokens: List[ShapValue] = []
    top_misinfo_tokens: List[ShapValue] = []
    confidence: dict
    method: str = "shap+attention"


class HistoryFilters(BaseModel):
    """Schema for history filters."""
    search: Optional[str] = None
    sarcasm_filter: Optional[bool] = None
    misinfo_filter: Optional[bool] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
