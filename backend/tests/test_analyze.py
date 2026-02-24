"""Tests for analysis endpoints (uses mock ML service)."""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import get_db, Base

TEST_DB_URL = "sqlite+aiosqlite:///./test_analyze.db"
engine_test = create_async_engine(TEST_DB_URL, echo=False)
TestingSessionLocal = sessionmaker(engine_test, class_=AsyncSession, expire_on_commit=False)

MOCK_PREDICTION = {
    "sarcasm_score": 0.82,
    "sarcasm_label": "SARCASTIC",
    "misinformation_score": 0.21,
    "misinformation_label": "CREDIBLE",
    "processing_time_ms": 120.5,
    "model_version": "xlm-roberta-large-codemix-v1",
    "language": "hinglish",
    "tokens": ["haan", "yaar", "bahut", "accha"],
    "attention_weights": None,
}


async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    app.dependency_overrides[get_db] = override_get_db
    yield
    app.dependency_overrides.clear()
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_analyze_unauthenticated(client):
    """Public analyze endpoint should work without auth."""
    with patch("app.services.ml_service.ml_service.predict", new_callable=AsyncMock) as mock_predict, \
         patch("app.services.analysis_service.AnalysisService._get_from_cache", new_callable=AsyncMock) as mock_cache:
        mock_predict.return_value = MOCK_PREDICTION
        mock_cache.return_value = None
        async with client as c:
            response = await c.post("/api/v1/analyze", json={"text": "Haan bilkul, bahut accha"})
    assert response.status_code == 200
    data = response.json()
    assert "sarcasm" in data
    assert "misinformation" in data
    assert data["sarcasm"]["label"] == "SARCASTIC"


@pytest.mark.asyncio
async def test_analyze_text_too_long(client):
    async with client as c:
        response = await c.post("/api/v1/analyze", json={"text": "a" * 501})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_analyze_empty_text(client):
    async with client as c:
        response = await c.post("/api/v1/analyze", json={"text": "   "})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_batch_analyze_requires_auth(client):
    async with client as c:
        response = await c.post("/api/v1/analyze/batch", json={"texts": ["test 1", "test 2"]})
    assert response.status_code == 401
