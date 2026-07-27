import pytest
from httpx import AsyncClient

from app.schemas.rewrite import RewriteRequest
from app.services.rewriting import rewrite_bullets_rule_based, rewrite_resume


class TestRewritingService:
    def test_rule_based_rewriter_identifies_weak_verbs(self):
        sample_parsed = {
            "experience": [
                {
                    "title": "Software Engineer",
                    "company": "Acme Inc",
                    "bullets": [
                        "Responsible for maintaining legacy codebase.",
                        "Worked on building new REST endpoints.",
                    ],
                }
            ]
        }
        result = rewrite_bullets_rule_based(sample_parsed)
        assert len(result.rewrites) == 2
        assert "Spearheaded" in result.rewrites[0].rewritten
        assert "Spearheaded" in result.rewrites[1].rewritten

    @pytest.mark.asyncio
    async def test_rewrite_resume_service_fallback(self):
        sample_parsed = {
            "experience": [
                {
                    "title": "Developer",
                    "company": "Tech Corp",
                    "bullets": ["Helped with database migration."],
                }
            ]
        }
        result = await rewrite_resume(sample_parsed, RewriteRequest(job_description="Python FastApi Developer"))
        assert len(result.rewrites) >= 1
        assert result.rewrites[0].original == "Helped with database migration."


class TestRewriteEndpoint:
    @pytest.mark.asyncio
    async def test_rewrite_unauthenticated(self, client: AsyncClient):
        res = await client.post("/api/resumes/00000000-0000-0000-0000-000000000000/rewrite")
        assert res.status_code == 401

    @pytest.mark.asyncio
    async def test_rewrite_resume_not_found(self, client: AsyncClient):
        # Register user & login to get token
        await client.post("/api/auth/register", json={"email": "rewriteuser@example.com", "password": "password123"})
        login_res = await client.post("/api/auth/login", json={"email": "rewriteuser@example.com", "password": "password123"})
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        res = await client.post(
            "/api/resumes/00000000-0000-0000-0000-000000000000/rewrite",
            headers=headers,
            json={"job_description": "Senior Engineer"},
        )
        assert res.status_code == 404
