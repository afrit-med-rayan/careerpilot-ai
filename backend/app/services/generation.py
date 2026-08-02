import json
import logging
import re
from typing import Optional

from app.core.config import get_settings
from app.db.models import JobPosting, Resume
from app.schemas.generation import (
    CoverLetterRequest,
    CoverLetterResponse,
    InterviewQuestionItem,
    InterviewQuestionsResponse,
    SkillGapResponse,
)
from app.services.llm_client import LLMError, generate_structured_json

logger = logging.getLogger(__name__)
settings = get_settings()


# ── System Instruction Contract ──────────────────────────────────────────────
SYSTEM_PROMPT_CONTRACT = (
    "Only use facts present in the provided resume data. "
    "Never invent employers, job titles, dates, or metrics. "
    "If information needed to fully answer is missing, state that explicitly rather than fabricating it."
)


# ── Cover Letter Service ──────────────────────────────────────────────────────
def _fallback_cover_letter(candidate_name: str, company: str, title: str, tone: str) -> CoverLetterResponse:
    greeting = "Dear Hiring Manager," if tone == "formal" else f"Hello {company} Team,"
    closing = "Sincerely," if tone == "formal" else "Best regards,"
    letter = (
        f"{greeting}\n\n"
        f"I am writing to express my strong interest in the {title} position at {company}. "
        "With my background, technical expertise, and proven track record of delivering high-impact solutions, "
        "I am confident in my ability to make an immediate contribution to your team.\n\n"
        "Throughout my career, I have focused on solving complex problems, building scalable systems, "
        "and driving measurable business value. My experience aligns closely with your core requirements, "
        "and I am eager to bring my skills to this role.\n\n"
        "Thank you for your time and consideration. I look forward to discussing how my experience "
        "and background match your team's needs.\n\n"
        f"{closing}\n{candidate_name or 'Applicant'}"
    )
    return CoverLetterResponse(cover_letter=letter)


async def generate_cover_letter(
    resume: Resume,
    job: Optional[JobPosting],
    request: CoverLetterRequest,
) -> CoverLetterResponse:
    """Generates a tailored cover letter matching candidate experience to target job."""
    candidate_name = ""
    if resume.parsed_json and isinstance(resume.parsed_json, dict):
        candidate_name = (resume.parsed_json.get("contact") or {}).get("name") or ""

    company = job.company if job else "the Company"
    title = job.title if job else "the target role"
    job_desc = job.description if job else "General job role requirements."

    if settings.anthropic_api_key:
        prompt = (
            f"Generate a professional, compelling cover letter in a {request.tone} tone for the following applicant and job posting.\n\n"
            f"CANDIDATE RESUME DATA:\n{json.dumps(resume.parsed_json or resume.raw_text or {}, indent=2)}\n\n"
            f"JOB DETAILS:\nTitle: {title}\nCompany: {company}\nDescription:\n{job_desc}"
        )
        system_prompt = f"You are an executive career advisor. {SYSTEM_PROMPT_CONTRACT}"
        try:
            return await generate_structured_json(
                prompt=prompt,
                schema_model=CoverLetterResponse,
                system_prompt=system_prompt,
                temperature=0.3,
            )
        except LLMError as exc:
            logger.error(f"LLM Cover letter generation failed: {exc}")

    return _fallback_cover_letter(candidate_name, company, title, request.tone)


# ── Interview Questions Service ───────────────────────────────────────────────
def _fallback_interview_questions(title: str) -> InterviewQuestionsResponse:
    return InterviewQuestionsResponse(
        questions=[
            InterviewQuestionItem(
                question=f"Can you walk me through a complex technical challenge you faced relevant to a {title} role and how you resolved it?",
                type="technical",
                suggested_answer_notes="Highlight relevant frameworks, architecture decisions, and measurable outcomes from your recent work experience.",
            ),
            InterviewQuestionItem(
                question="Describe a situation where you had to balance competing priorities or tight deadlines. How did you manage expectations?",
                type="behavioral",
                suggested_answer_notes="Use the STAR method (Situation, Task, Action, Result) to demonstrate leadership and effective communication.",
            ),
            InterviewQuestionItem(
                question=f"What core skills make you uniquely qualified for this {title} position?",
                type="technical",
                suggested_answer_notes="Focus on your strongest technical competencies and tools listed in your skills section.",
            ),
        ]
    )


async def generate_interview_questions(
    resume: Resume,
    job: Optional[JobPosting],
) -> InterviewQuestionsResponse:
    """Generates tailored technical and behavioral interview preparation questions and notes."""
    title = job.title if job else "the target position"
    company = job.company if job else "the company"
    job_desc = job.description if job else ""

    if settings.anthropic_api_key:
        prompt = (
            f"Generate 4 to 6 specific technical and behavioral interview questions likely to be asked for the {title} position at {company}. "
            "For each question, provide detailed talking point notes tailored strictly to the candidate's actual background.\n\n"
            f"CANDIDATE RESUME DATA:\n{json.dumps(resume.parsed_json or resume.raw_text or {}, indent=2)}\n\n"
            f"JOB DETAILS:\nTitle: {title}\nCompany: {company}\nDescription:\n{job_desc}"
        )
        system_prompt = f"You are a tech lead and interview preparation coach. {SYSTEM_PROMPT_CONTRACT}"
        try:
            return await generate_structured_json(
                prompt=prompt,
                schema_model=InterviewQuestionsResponse,
                system_prompt=system_prompt,
                temperature=0.2,
            )
        except LLMError as exc:
            logger.error(f"LLM Interview questions generation failed: {exc}")

    return _fallback_interview_questions(title)


# ── Skill Gap Analysis Service ────────────────────────────────────────────────
async def analyze_skill_gap(
    resume: Resume,
    job: Optional[JobPosting],
) -> SkillGapResponse:
    """Calculates skill gap analysis between resume skills and job posting requirements."""
    candidate_skills = set()
    if resume.parsed_json and isinstance(resume.parsed_json, dict):
        skills_list = resume.parsed_json.get("skills", [])
        if isinstance(skills_list, list):
            candidate_skills = {str(s).strip().lower() for s in skills_list}

    # If parsed_json skills was empty, try extracting words from raw text
    if not candidate_skills and resume.raw_text:
        raw_words = re.findall(r"\b[a-zA-Z0-9+#.-]{2,20}\b", resume.raw_text.lower())
        candidate_skills = set(raw_words)

    job_requirements = set()
    if job:
        if job.required_skills and isinstance(job.required_skills, list):
            job_requirements.update(str(s).strip().lower() for s in job.required_skills)
        if job.description:
            # Common tech keywords check
            common_keywords = [
                "python", "javascript", "typescript", "react", "next.js", "node.js",
                "fastapi", "django", "postgres", "postgresql", "sql", "docker", "aws",
                "git", "rest api", "graphql", "kubernetes", "ci/cd", "mongodb", "redis",
                "tailwind", "css", "html", "linux", "testing", "pytest"
            ]
            job_desc_lower = job.description.lower()
            for kw in common_keywords:
                if kw in job_desc_lower:
                    job_requirements.add(kw)

    if not job_requirements:
        job_requirements = {"python", "sql", "git", "rest api", "docker"}

    matched = []
    missing = []

    for req in job_requirements:
        if any(req in cs or cs in req for cs in candidate_skills):
            matched.append(req.title())
        else:
            missing.append(req.title())

    total = len(matched) + len(missing)
    match_pct = int((len(matched) / total) * 100) if total > 0 else 70

    return SkillGapResponse(
        matched_skills=sorted(matched),
        missing_skills=sorted(missing),
        match_percentage=match_pct,
    )
