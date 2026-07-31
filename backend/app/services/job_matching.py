import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import JobPosting, Match, Resume
from app.schemas.job_match import JobMatchItem, MatchJobsRequest, MatchJobsResponse
from app.services.embeddings import compute_similarity
from app.services.job_connectors import fetch_all_jobs

logger = logging.getLogger(__name__)


def _construct_resume_text(resume: Resume) -> str:
    """Constructs a consolidated text string representing the candidate's background."""
    parts = []
    if resume.parsed_json and isinstance(resume.parsed_json, dict):
        parsed = resume.parsed_json
        if parsed.get("summary"):
            parts.append(str(parsed["summary"]))
        if parsed.get("skills"):
            skills = parsed["skills"]
            if isinstance(skills, list):
                parts.append("Skills: " + ", ".join(str(s) for s in skills))
        if parsed.get("experience"):
            exp_list = parsed["experience"]
            if isinstance(exp_list, list):
                for exp in exp_list:
                    if isinstance(exp, dict):
                        company = exp.get("company", "")
                        title = exp.get("title", "")
                        bullets = " ".join(exp.get("bullets", []))
                        parts.append(f"{title} at {company}. {bullets}")

    if not parts and resume.raw_text:
        parts.append(resume.raw_text)

    return "\n\n".join(parts)


async def match_resume_to_jobs(
    db: AsyncSession,
    resume: Resume,
    request: MatchJobsRequest,
    limit: int = 20,
) -> MatchJobsResponse:
    """
    Ingests job postings if cache is missing/stale, calculates semantic similarity,
    persists matches, and returns ranked job postings.
    """
    # 1. Fetch from database or query external sources
    query_str = request.query.strip()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

    # Check for existing cached jobs matching query
    stmt = select(JobPosting).where(
        JobPosting.title.ilike(f"%{query_str}%"),
        JobPosting.fetched_at >= cutoff
    ).limit(limit * 2)
    result = await db.execute(stmt)
    existing_jobs = list(result.scalars().all())

    if len(existing_jobs) < 5:
        logger.info(f"Fewer than 5 cached jobs for '{query_str}'. Fetching from connectors.")
        fetched = await fetch_all_jobs(query=query_str, location=request.location, limit=limit)
        
        for f_job in fetched:
            # Check if job already exists by (external_id, source)
            existing_stmt = select(JobPosting).where(
                JobPosting.external_id == f_job.external_id,
                JobPosting.source == f_job.source
            )
            ex_res = await db.execute(existing_stmt)
            jp = ex_res.scalar_one_or_none()

            if not jp:
                jp = JobPosting(
                    external_id=f_job.external_id,
                    source=f_job.source,
                    title=f_job.title,
                    company=f_job.company,
                    description=f_job.description,
                    url=f_job.url,
                    location=f_job.location,
                    required_skills=f_job.required_skills,
                    fetched_at=datetime.now(timezone.utc),
                )
                db.add(jp)
            else:
                jp.fetched_at = datetime.now(timezone.utc)

        await db.commit()

        # Re-query all matching jobs
        stmt = select(JobPosting).where(JobPosting.title.ilike(f"%{query_str}%")).limit(50)
        res_jobs = await db.execute(stmt)
        existing_jobs = list(res_jobs.scalars().all())

        if not existing_jobs:
            # Fallback: get any recent jobs in table if search term was very specific
            all_jobs_stmt = select(JobPosting).order_by(JobPosting.fetched_at.desc()).limit(30)
            existing_jobs = list((await db.execute(all_jobs_stmt)).scalars().all())

    # 2. Compute similarity for candidate resume vs each job posting
    resume_text = _construct_resume_text(resume)
    matches_list = []

    for job in existing_jobs:
        job_text = f"{job.title} at {job.company}\n\n{job.description}"
        score = compute_similarity(resume_text, job_text)

        # Upsert Match record
        match_stmt = select(Match).where(Match.resume_id == resume.id, Match.job_id == job.id)
        existing_match = (await db.execute(match_stmt)).scalar_one_or_none()

        if existing_match:
            existing_match.similarity_score = score
        else:
            new_match = Match(
                resume_id=resume.id,
                job_id=job.id,
                similarity_score=score,
            )
            db.add(new_match)

        matches_list.append(
            JobMatchItem(
                job_id=job.id,
                external_id=job.external_id,
                source=job.source,
                title=job.title,
                company=job.company,
                description=job.description[:300] + ("..." if len(job.description) > 300 else ""),
                location=job.location,
                url=job.url,
                similarity_score=round(score, 4),
            )
        )

    await db.commit()

    # Sort descending by similarity score
    matches_list.sort(key=lambda m: m.similarity_score, reverse=True)
    return MatchJobsResponse(matches=matches_list[:limit])
