"""
Integration tests for auth endpoints (register + login).

These tests use an in-memory SQLite database so they run without a real
Postgres instance in CI. SQLite is sync-only — we use StaticPool + a
sync-compatible engine for simplicity in tests.
"""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Base
from app.db.session import get_db
from app.main import app

# Use an in-memory async SQLite DB for tests (no Postgres needed)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False
)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create all tables before each test, drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestRegister:
    async def test_register_success(self, client):
        resp = await client.post(
            "/api/auth/register",
            json={"email": "alice@example.com", "password": "secret123"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "alice@example.com"
        assert "id" in data
        assert "hashed_password" not in data  # never exposed

    async def test_register_duplicate_email(self, client):
        payload = {"email": "bob@example.com", "password": "pass"}
        await client.post("/api/auth/register", json=payload)
        resp = await client.post("/api/auth/register", json=payload)
        assert resp.status_code == 409
        assert "already registered" in resp.json()["detail"].lower()

    async def test_register_invalid_email(self, client):
        resp = await client.post(
            "/api/auth/register",
            json={"email": "not-an-email", "password": "pass"},
        )
        assert resp.status_code == 422


class TestLogin:
    async def test_login_success(self, client):
        # Register first
        await client.post(
            "/api/auth/register",
            json={"email": "carol@example.com", "password": "mypassword"},
        )
        resp = await client.post(
            "/api/auth/login",
            json={"email": "carol@example.com", "password": "mypassword"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client):
        await client.post(
            "/api/auth/register",
            json={"email": "dave@example.com", "password": "correct"},
        )
        resp = await client.post(
            "/api/auth/login",
            json={"email": "dave@example.com", "password": "wrong"},
        )
        assert resp.status_code == 401

    async def test_login_nonexistent_user(self, client):
        resp = await client.post(
            "/api/auth/login",
            json={"email": "nobody@example.com", "password": "pass"},
        )
        assert resp.status_code == 401
