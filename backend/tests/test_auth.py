"""Tests for auth endpoints."""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import get_db, Base
from app.core.config import get_settings

settings = get_settings()

TEST_DB_URL = "sqlite+aiosqlite:///./test.db"

engine_test = create_async_engine(TEST_DB_URL, echo=False)
TestingSessionLocal = sessionmaker(engine_test, class_=AsyncSession, expire_on_commit=False)


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
async def test_register_user(client):
    async with client as c:
        response = await c.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "Password1",
            "full_name": "Test User",
        })
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert "password" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    async with client as c:
        await c.post("/api/v1/auth/register", json={
            "email": "dup@example.com",
            "password": "Password1",
            "full_name": "User One",
        })
        response = await c.post("/api/v1/auth/register", json={
            "email": "dup@example.com",
            "password": "Password2",
            "full_name": "User Two",
        })
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_login_success(client):
    async with client as c:
        await c.post("/api/v1/auth/register", json={
            "email": "login@example.com",
            "password": "Password1",
            "full_name": "Login User",
        })
        response = await c.post(
            "/api/v1/auth/login",
            data={"username": "login@example.com", "password": "Password1"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    async with client as c:
        await c.post("/api/v1/auth/register", json={
            "email": "bad@example.com",
            "password": "Password1",
            "full_name": "Bad User",
        })
        response = await c.post(
            "/api/v1/auth/login",
            data={"username": "bad@example.com", "password": "WrongPass9"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_profile_authenticated(client):
    async with client as c:
        await c.post("/api/v1/auth/register", json={
            "email": "me@example.com",
            "password": "Password1",
            "full_name": "Me User",
        })
        login = await c.post(
            "/api/v1/auth/login",
            data={"username": "me@example.com", "password": "Password1"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        token = login.json()["access_token"]
        response = await c.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"
