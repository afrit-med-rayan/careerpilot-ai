#!/usr/bin/env python3
"""
seed_demo.py — Populate the database with demo data.

Usage:
    cd backend
    python scripts/seed_demo.py

This script creates:
  - 1 demo user   (demo@careerpilot.ai / demo1234)
  - 2 sample resumes with parsed JSON, ATS scores, and analysis reports
  - 3 cached job postings
  - 3 match records linking resumes to jobs

Safe to run multiple times — existing demo data is detected and skipped.
"""

import asyncio
import sys
import uuid
from pathlib import Path

# Ensure the backend package is on sys.path when run directly
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.models import (
    ArtifactType,
    GeneratedArtifact,
    JobPosting,
    Match,
    Resume,
    User,
)

# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

DEMO_EMAIL = "demo@careerpilot.ai"
DEMO_PASSWORD = "demo1234"

SAMPLE_RESUMES = [
    {
        "original_filename": "jane_doe_software_engineer.pdf",
        "file_url": "uploads/demo_jane_doe.pdf",
        "raw_text": (
            "Jane Doe\njane.doe@email.com | github.com/janedoe | linkedin.com/in/janedoe\n\n"
            "SUMMARY\nSoftware engineer with 5 years of experience building scalable Python web APIs "
            "and React frontends. Passionate about clean code and developer tooling.\n\n"
            "EXPERIENCE\nSenior Software Engineer — Acme Corp (2021–Present)\n"
            "• Redesigned the authentication service, reducing login latency by 40%\n"
            "• Led migration from monolith to microservices, cutting deploy time by 60%\n"
            "• Mentored 3 junior engineers through weekly code reviews\n\n"
            "Software Engineer — StartupXYZ (2019–2021)\n"
            "• Built REST APIs consumed by 200k+ monthly active users\n"
            "• Introduced automated testing, raising code coverage from 12% to 78%\n\n"
            "EDUCATION\nB.Sc. Computer Science — State University (2015–2019)\n\n"
            "SKILLS\nPython, FastAPI, Django, React, TypeScript, PostgreSQL, Docker, Kubernetes, AWS"
        ),
        "parsed_json": {
            "name": "Jane Doe",
            "email": "jane.doe@email.com",
            "summary": "Software engineer with 5 years of experience building scalable Python web APIs and React frontends.",
            "experience": [
                {
                    "title": "Senior Software Engineer",
                    "company": "Acme Corp",
                    "period": "2021–Present",
                    "bullets": [
                        "Redesigned the authentication service, reducing login latency by 40%",
                        "Led migration from monolith to microservices, cutting deploy time by 60%",
                        "Mentored 3 junior engineers through weekly code reviews",
                    ],
                },
                {
                    "title": "Software Engineer",
                    "company": "StartupXYZ",
                    "period": "2019–2021",
                    "bullets": [
                        "Built REST APIs consumed by 200k+ monthly active users",
                        "Introduced automated testing, raising code coverage from 12% to 78%",
                    ],
                },
            ],
            "education": [{"degree": "B.Sc. Computer Science", "school": "State University", "year": "2019"}],
            "skills": ["Python", "FastAPI", "Django", "React", "TypeScript", "PostgreSQL", "Docker", "Kubernetes", "AWS"],
        },
        "ats_score": 82,
        "analysis_report": {
            "ats_score": 82,
            "missing_sections": [],
            "strengths": [
                "Strong quantified achievements (latency -40%, coverage 78%)",
                "Progressive career growth visible",
                "Broad modern tech stack",
            ],
            "improvements": [
                "Add a dedicated 'Projects' section to showcase personal work",
                "Include certifications (AWS, Kubernetes) if held",
            ],
            "passive_voice_count": 1,
            "metrics_detected": 5,
            "llm_summary": "Solid senior-level resume with clear impact metrics. Minor gaps: no certifications or personal projects listed.",
        },
    },
    {
        "original_filename": "alex_chen_data_scientist.pdf",
        "file_url": "uploads/demo_alex_chen.pdf",
        "raw_text": (
            "Alex Chen\nalex.chen@email.com | kaggle.com/alexchen\n\n"
            "OBJECTIVE\nData Scientist with 3 years of experience in ML model development and data pipelines. "
            "Looking to join an AI-first team.\n\n"
            "EXPERIENCE\nData Scientist — DataDriven Inc (2022–Present)\n"
            "• Developed churn prediction model with 91% accuracy, saving $2M annually\n"
            "• Built ETL pipelines processing 10TB of clickstream data daily\n"
            "• Collaborated with product team to define KPIs and build dashboards\n\n"
            "Junior Data Analyst — RetailCo (2021–2022)\n"
            "• Conducted A/B tests that improved conversion rate by 18%\n"
            "• Created automated reporting reducing manual work by 6 hours/week\n\n"
            "EDUCATION\nM.Sc. Data Science — Tech University (2019–2021)\n\n"
            "SKILLS\nPython, scikit-learn, TensorFlow, PyTorch, SQL, Spark, Airflow, Tableau, dbt"
        ),
        "parsed_json": {
            "name": "Alex Chen",
            "email": "alex.chen@email.com",
            "summary": "Data Scientist with 3 years of experience in ML model development and data pipelines.",
            "experience": [
                {
                    "title": "Data Scientist",
                    "company": "DataDriven Inc",
                    "period": "2022–Present",
                    "bullets": [
                        "Developed churn prediction model with 91% accuracy, saving $2M annually",
                        "Built ETL pipelines processing 10TB of clickstream data daily",
                        "Collaborated with product team to define KPIs and build dashboards",
                    ],
                },
                {
                    "title": "Junior Data Analyst",
                    "company": "RetailCo",
                    "period": "2021–2022",
                    "bullets": [
                        "Conducted A/B tests that improved conversion rate by 18%",
                        "Created automated reporting reducing manual work by 6 hours/week",
                    ],
                },
            ],
            "education": [{"degree": "M.Sc. Data Science", "school": "Tech University", "year": "2021"}],
            "skills": ["Python", "scikit-learn", "TensorFlow", "PyTorch", "SQL", "Spark", "Airflow", "Tableau", "dbt"],
        },
        "ats_score": 76,
        "analysis_report": {
            "ats_score": 76,
            "missing_sections": ["certifications"],
            "strengths": [
                "Excellent quantified business impact ($2M saving, 91% accuracy)",
                "Mix of engineering (pipelines) and analytical (A/B tests) skills",
            ],
            "improvements": [
                "Replace generic 'Objective' with a targeted 'Summary' statement",
                "Add GitHub/portfolio links to showcase projects",
                "List publications or Kaggle competition rankings if available",
            ],
            "passive_voice_count": 2,
            "metrics_detected": 4,
            "llm_summary": "Good mid-level DS resume. Objective section feels dated; replacing with a strong summary would improve ATS performance.",
        },
    },
]

SAMPLE_JOBS = [
    {
        "external_id": "demo-job-001",
        "source": "remotive",
        "title": "Senior Python Backend Engineer",
        "company": "CloudScale",
        "description": (
            "We are looking for a Senior Python Backend Engineer to join our platform team. "
            "You will design and build scalable REST APIs, work with FastAPI and PostgreSQL, "
            "containerize services with Docker and Kubernetes, and own CI/CD pipelines. "
            "Required: Python 5+ years, FastAPI or Django, PostgreSQL, Docker, AWS. "
            "Nice to have: Kafka, Redis, gRPC."
        ),
        "url": "https://remotive.com/remote-jobs/software-dev/senior-python-backend-engineer-demo",
        "location": "Remote",
        "required_skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes", "AWS"],
    },
    {
        "external_id": "demo-job-002",
        "source": "adzuna",
        "title": "Machine Learning Engineer",
        "company": "AI Ventures",
        "description": (
            "Join our ML team to productionise models and build robust data pipelines. "
            "You will work closely with data scientists and backend engineers. "
            "Required: Python, PyTorch or TensorFlow, MLflow or Kubeflow, SQL, Docker. "
            "Experience with Spark or Airflow is a plus."
        ),
        "url": "https://www.adzuna.com/details/demo-job-002",
        "location": "New York, NY",
        "required_skills": ["Python", "PyTorch", "TensorFlow", "MLflow", "SQL", "Docker", "Spark"],
    },
    {
        "external_id": "demo-job-003",
        "source": "remotive",
        "title": "Full-Stack Engineer (React + Python)",
        "company": "ProductLab",
        "description": (
            "Build consumer-facing features end-to-end. Our stack is React/TypeScript on the frontend "
            "and FastAPI/Python on the backend with PostgreSQL. "
            "Required: React, TypeScript, Python, REST API design, SQL. "
            "Nice to have: Next.js, GraphQL, Tailwind CSS."
        ),
        "url": "https://remotive.com/remote-jobs/software-dev/full-stack-engineer-demo",
        "location": "Remote",
        "required_skills": ["React", "TypeScript", "Python", "FastAPI", "PostgreSQL", "Next.js"],
    },
]

SAMPLE_COVER_LETTER = """Dear Hiring Manager,

I am writing to express my enthusiasm for the Senior Python Backend Engineer position at CloudScale. 
With five years of hands-on experience designing and scaling Python APIs — including a recent 
microservices migration that reduced deployment time by 60% — I am confident I can make an 
immediate impact on your platform team.

At Acme Corp, I led the redesign of our authentication service (FastAPI + PostgreSQL), cutting 
login latency by 40% while serving 200k+ monthly active users. I have deep familiarity with 
Docker and Kubernetes orchestration and have owned end-to-end CI/CD pipelines in AWS environments.

I am drawn to CloudScale's mission of making infrastructure invisible so that product teams can 
ship faster. I would love to bring my experience in distributed systems and developer tooling to 
help accelerate that vision.

Thank you for your time and consideration. I look forward to the opportunity to discuss how my 
background aligns with your needs.

Warm regards,
Jane Doe"""

# ---------------------------------------------------------------------------
# Seeding logic
# ---------------------------------------------------------------------------


async def seed(session: AsyncSession) -> None:
    # ── 1. Demo user ────────────────────────────────────────────────────────
    result = await session.execute(select(User).where(User.email == DEMO_EMAIL))
    user = result.scalars().first()

    if user is None:
        user = User(
            id=uuid.uuid4(),
            email=DEMO_EMAIL,
            hashed_password=hash_password(DEMO_PASSWORD),
        )
        session.add(user)
        await session.flush()
        print(f"✅  Created demo user: {DEMO_EMAIL} / {DEMO_PASSWORD}")
    else:
        print(f"ℹ️   Demo user already exists: {DEMO_EMAIL}")

    # ── 2. Job postings ─────────────────────────────────────────────────────
    job_objects: list[JobPosting] = []
    for job_data in SAMPLE_JOBS:
        result = await session.execute(
            select(JobPosting).where(
                JobPosting.external_id == job_data["external_id"],
                JobPosting.source == job_data["source"],
            )
        )
        job = result.scalars().first()
        if job is None:
            job = JobPosting(id=uuid.uuid4(), **job_data)
            session.add(job)
            print(f"✅  Created job: {job_data['title']} @ {job_data['company']}")
        else:
            print(f"ℹ️   Job already exists: {job_data['title']}")
        job_objects.append(job)
    await session.flush()

    # ── 3. Resumes ──────────────────────────────────────────────────────────
    resume_objects: list[Resume] = []
    for resume_data in SAMPLE_RESUMES:
        result = await session.execute(
            select(Resume).where(
                Resume.user_id == user.id,
                Resume.original_filename == resume_data["original_filename"],
            )
        )
        resume = result.scalars().first()
        if resume is None:
            resume = Resume(id=uuid.uuid4(), user_id=user.id, **resume_data)
            session.add(resume)
            print(f"✅  Created resume: {resume_data['original_filename']}")
        else:
            print(f"ℹ️   Resume already exists: {resume_data['original_filename']}")
        resume_objects.append(resume)
    await session.flush()

    # ── 4. Matches ──────────────────────────────────────────────────────────
    match_configs = [
        # Jane Doe ↔ Python Backend job (high match)
        (resume_objects[0], job_objects[0], 0.91),
        # Jane Doe ↔ Full-Stack job (moderate match)
        (resume_objects[0], job_objects[2], 0.74),
        # Alex Chen ↔ ML Engineer job (high match)
        (resume_objects[1], job_objects[1], 0.88),
    ]
    for resume, job, score in match_configs:
        result = await session.execute(
            select(Match).where(
                Match.resume_id == resume.id,
                Match.job_id == job.id,
            )
        )
        existing = result.scalars().first()
        if existing is None:
            match = Match(
                id=uuid.uuid4(),
                resume_id=resume.id,
                job_id=job.id,
                similarity_score=score,
            )
            session.add(match)
            print(f"✅  Created match: {resume.original_filename} ↔ {job.title} ({score:.0%})")
        else:
            print(f"ℹ️   Match already exists: {resume.original_filename} ↔ {job.title}")

    await session.flush()

    # ── 5. Sample generated artifact (cover letter) ─────────────────────────
    jane_resume = resume_objects[0]
    python_job = job_objects[0]
    result = await session.execute(
        select(GeneratedArtifact).where(
            GeneratedArtifact.resume_id == jane_resume.id,
            GeneratedArtifact.type == ArtifactType.cover_letter,
        )
    )
    if result.scalars().first() is None:
        artifact = GeneratedArtifact(
            id=uuid.uuid4(),
            resume_id=jane_resume.id,
            job_id=python_job.id,
            type=ArtifactType.cover_letter,
            content={
                "cover_letter": SAMPLE_COVER_LETTER,
                "tone": "formal",
                "word_count": len(SAMPLE_COVER_LETTER.split()),
            },
        )
        session.add(artifact)
        print("✅  Created sample cover letter artifact for Jane Doe")
    else:
        print("ℹ️   Cover letter artifact already exists")

    await session.commit()
    print("\n🎉  Seed complete! Log in with:")
    print(f"     Email:    {DEMO_EMAIL}")
    print(f"     Password: {DEMO_PASSWORD}")
    print("     API docs: http://localhost:8000/docs")


async def main() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        await seed(session)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
