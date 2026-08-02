import pytest
from httpx import AsyncClient

from app.schemas.generation import CoverLetterRequest
from app.services.generation import (
    analyze_skill_gap,
    generate_cover_letter,
    generate_interview_questions,
)


class TestGenerationServices:
    @pytest.mark.asyncio
    async def test_cover_letter_service_fallback(self):
        class DummyResume:
            parsed_json = {"contact": {"name": "Jane Doe"}}
            raw_text = "Experienced Engineer"
        res = await generate_cover_letter(DummyResume(), None, CoverLetterRequest(tone="formal"))
        assert "Jane Doe" in res.cover_letter or "Sincerely" in res.cover_letter
        assert len(res.cover_letter) > 50

    @pytest.mark.asyncio
    async def test_interview_questions_service(self):
        class DummyResume:
            parsed_json = {"skills": ["Python", "FastAPI"]}
            raw_text = ""
        res = await generate_interview_questions(DummyResume(), None)
        assert len(res.questions) >= 3
        assert res.questions[0].type in ["technical", "behavioral"]

    @pytest.mark.asyncio
    async def test_skill_gap_service(self):
        class DummyResume:
            parsed_json = {"skills": ["Python", "FastAPI", "SQL"]}
            raw_text = ""
        class DummyJob:
            required_skills = ["Python", "Docker", "AWS"]
            description = "Python software engineer with Docker experience"
        res = await analyze_skill_gap(DummyResume(), DummyJob())
        assert isinstance(res.matched_skills, list)
        assert isinstance(res.missing_skills, list)
        assert 0 <= res.match_percentage <= 100


class TestGenerationEndpoints:
    @pytest.mark.asyncio
    async def test_generation_unauthenticated(self, client: AsyncClient):
        res1 = await client.post("/api/resumes/00000000-0000-0000-0000-000000000000/cover-letter")
        assert res1.status_code == 401

        res2 = await client.post("/api/resumes/00000000-0000-0000-0000-000000000000/interview-questions")
        assert res2.status_code == 401

        res3 = await client.get("/api/resumes/00000000-0000-0000-0000-000000000000/skill-gap")
        assert res3.status_code == 401

    @pytest.mark.asyncio
    async def test_generation_endpoints_not_found(self, client: AsyncClient):
        # Register user & login
        await client.post("/api/auth/register", json={"email": "genuser@example.com", "password": "password123"})
        login_res = await client.post("/api/auth/login", json={"email": "genuser@example.com", "password": "password123"})
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        res = await client.post(
            "/api/resumes/00000000-0000-0000-0000-000000000000/cover-letter",
            headers=headers,
            json={"tone": "conversational"},
        )
        assert res.status_code == 404
