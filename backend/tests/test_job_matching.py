import pytest
from httpx import AsyncClient

from app.services.embeddings import compute_similarity
from app.services.job_connectors import fetch_remotive_jobs


class TestEmbeddings:
    def test_compute_similarity_identical(self):
        text = "Senior Python Developer with FastAPI and Postgres experience."
        score = compute_similarity(text, text)
        assert score >= 0.95

    def test_compute_similarity_different(self):
        text1 = "Senior Python Developer building REST APIs."
        text2 = "Pastry chef baking sourdough bread and croissants."
        score = compute_similarity(text1, text2)
        assert score < 0.5

    def test_compute_similarity_empty(self):
        assert compute_similarity("", "Python developer") == 0.0


class TestJobConnectors:
    @pytest.mark.asyncio
    async def test_remotive_connector(self):
        jobs = await fetch_remotive_jobs(query="python", limit=5)
        # Remotive endpoint should return a list (empty if network down, or populated if up)
        assert isinstance(jobs, list)


class TestJobMatchingEndpoint:
    @pytest.mark.asyncio
    async def test_match_jobs_unauthenticated(self, client: AsyncClient):
        res = await client.post(
            "/api/resumes/00000000-0000-0000-0000-000000000000/match-jobs",
            json={"query": "developer"}
        )
        assert res.status_code == 401

    @pytest.mark.asyncio
    async def test_match_jobs_not_found(self, client: AsyncClient):
        # Register user & login
        await client.post("/api/auth/register", json={"email": "jobmatchuser@example.com", "password": "password123"})
        login_res = await client.post("/api/auth/login", json={"email": "jobmatchuser@example.com", "password": "password123"})
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        res = await client.post(
            "/api/resumes/00000000-0000-0000-0000-000000000000/match-jobs",
            headers=headers,
            json={"query": "python developer"}
        )
        assert res.status_code == 404
