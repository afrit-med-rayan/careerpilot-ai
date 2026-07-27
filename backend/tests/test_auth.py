"""
Integration tests for auth endpoints (register + login).

These tests use an in-memory SQLite database so they run without a real
Postgres instance in CI. SQLite is sync-only — we use StaticPool + a
sync-compatible engine for simplicity in tests.
"""
import pytest
from httpx import AsyncClient


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
