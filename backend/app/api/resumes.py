import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_current_user
from app.db.models import ArtifactType, GeneratedArtifact, JobPosting, Resume, User
from app.db.session import AsyncSessionLocal, get_db
from app.schemas import ResumeResponse, ResumeUploadResponse
from app.schemas.analysis import ResumeAnalysis
from app.schemas.generation import (
    CoverLetterRequest,
    CoverLetterResponse,
    InterviewQuestionsResponse,
    SkillGapResponse,
)
from app.schemas.job_match import MatchJobsRequest, MatchJobsResponse
from app.schemas.rewrite import RewriteRequest, RewriteResponse
from app.services.analysis import analyze_resume
from app.services.generation import (
    analyze_skill_gap,
    generate_cover_letter,
    generate_interview_questions,
)
from app.services.job_matching import match_resume_to_jobs
from app.services.parsing import parse_document, segment_resume
from app.services.rewriting import rewrite_resume
from app.services.storage import LocalStorage, get_storage_backend

router = APIRouter(prefix="/api/resumes", tags=["resumes"])

ALLOWED_EXTENSIONS = {"pdf", "docx", "doc"}
MAX_FILE_SIZE_MB = 10


async def process_resume_background(resume_id: uuid.UUID, raw_text: str):
    """Background task to segment the resume via LLM."""
    parsed = await segment_resume(raw_text)
    if parsed:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Resume).where(Resume.id == resume_id))
            resume = result.scalar_one_or_none()
            if resume:
                resume.parsed_json = parsed.model_dump()
                await db.commit()


@router.post("/upload", response_model=ResumeUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    storage: LocalStorage = Depends(get_storage_backend),
):
    """
    Upload a resume PDF or DOCX.
    - Stores the file via the storage backend.
    - Extracts raw text (no LLM segmentation yet — that's Phase 2).
    - Returns a preview of the raw text.
    """
    # Validate extension
    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported file type '.{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Read content + size guard
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large ({size_mb:.1f} MB). Maximum is {MAX_FILE_SIZE_MB} MB.",
        )

    # Persist file
    file_url = await storage.save(filename=filename, content=content)

    # Extract raw text
    parse_result = parse_document(filename=filename, content=content)

    # Save resume record
    resume = Resume(
        user_id=current_user.id,
        file_url=file_url,
        original_filename=filename,
        raw_text=parse_result.raw_text or None,
    )
    db.add(resume)
    await db.flush()
    await db.refresh(resume)

    preview = (parse_result.raw_text or "")[:300]
    
    # Queue the background segmentation task if we have text
    if parse_result.raw_text and not parse_result.ocr_required:
        background_tasks.add_task(process_resume_background, resume.id, parse_result.raw_text)

    return ResumeUploadResponse(
        resume_id=resume.id,
        original_filename=filename,
        raw_text_preview=preview,
        ocr_required=parse_result.ocr_required,
        message=(
            "Resume uploaded. OCR required — text extraction not possible for scanned PDFs."
            if parse_result.ocr_required
            else "Resume uploaded and text extracted successfully."
        ),
    )


@router.get("/", response_model=list[ResumeResponse])
async def list_resumes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all resumes belonging to the current user."""
    result = await db.execute(
        select(Resume)
        .where(Resume.user_id == current_user.id)
        .order_by(Resume.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{resume_id}", response_model=ResumeResponse)
async def get_resume(
    resume_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single resume by ID (must belong to current user)."""
    result = await db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == current_user.id)
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
    return resume


@router.post("/{resume_id}/analyze", response_model=ResumeAnalysis)
async def analyze_resume_endpoint(
    resume_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Run analysis on a parsed resume.
    """
    result = await db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == current_user.id)
    )
    resume = result.scalar_one_or_none()
    
    if not resume:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
        
    if not resume.parsed_json:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Resume has not been parsed yet or parsing failed."
        )

    analysis_result = await analyze_resume(resume.parsed_json)
    
    # Save the result
    resume.ats_score = analysis_result.ats_score
    resume.analysis_report = analysis_result.model_dump()
    await db.commit()
    
    return analysis_result


@router.post("/{resume_id}/rewrite", response_model=RewriteResponse)
async def rewrite_resume_endpoint(
    resume_id: uuid.UUID,
    body: RewriteRequest = RewriteRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate bullet point and section rewrites for a parsed resume, optionally tailored to a job description.
    """
    result = await db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == current_user.id)
    )
    resume = result.scalar_one_or_none()
    
    if not resume:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")
        
    if not resume.parsed_json:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Resume has not been parsed yet or parsing failed."
        )

    rewrite_result = await rewrite_resume(resume.parsed_json, body)

    # Persist artifact
    artifact = GeneratedArtifact(
        resume_id=resume.id,
        type=ArtifactType.REWRITE,
        content=rewrite_result.model_dump()
    )
    db.add(artifact)
    await db.commit()
    
    return rewrite_result


@router.post("/{resume_id}/match-jobs", response_model=MatchJobsResponse)
async def match_jobs_endpoint(
    resume_id: uuid.UUID,
    body: MatchJobsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Search job postings, calculate similarity score against resume text & skills, and return ranked job matches.
    """
    result = await db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == current_user.id)
    )
    resume = result.scalar_one_or_none()

    if not resume:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

    return await match_resume_to_jobs(db, resume, body)


async def _get_user_resume_and_job(
    resume_id: uuid.UUID,
    job_id: Optional[uuid.UUID],
    db: AsyncSession,
    user_id: uuid.UUID,
):
    res_stmt = select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
    resume = (await db.execute(res_stmt)).scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resume not found")

    job = None
    if job_id:
        job_stmt = select(JobPosting).where(JobPosting.id == job_id)
        job = (await db.execute(job_stmt)).scalar_one_or_none()

    return resume, job


@router.post("/{resume_id}/cover-letter", response_model=CoverLetterResponse)
async def cover_letter_endpoint(
    resume_id: uuid.UUID,
    job_id: Optional[uuid.UUID] = None,
    body: CoverLetterRequest = CoverLetterRequest(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a tailored cover letter for a candidate resume and optional target job."""
    resume, job = await _get_user_resume_and_job(resume_id, job_id, db, current_user.id)
    result = await generate_cover_letter(resume, job, body)

    # Save artifact
    artifact = GeneratedArtifact(
        resume_id=resume.id,
        job_id=job.id if job else None,
        type=ArtifactType.cover_letter,
        content=result.model_dump(),
    )
    db.add(artifact)
    await db.commit()

    return result


@router.post("/{resume_id}/interview-questions", response_model=InterviewQuestionsResponse)
async def interview_questions_endpoint(
    resume_id: uuid.UUID,
    job_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate technical and behavioral interview preparation questions and notes."""
    resume, job = await _get_user_resume_and_job(resume_id, job_id, db, current_user.id)
    result = await generate_interview_questions(resume, job)

    # Save artifact
    artifact = GeneratedArtifact(
        resume_id=resume.id,
        job_id=job.id if job else None,
        type=ArtifactType.interview_questions,
        content=result.model_dump(),
    )
    db.add(artifact)
    await db.commit()

    return result


@router.get("/{resume_id}/skill-gap", response_model=SkillGapResponse)
async def skill_gap_endpoint(
    resume_id: uuid.UUID,
    job_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Perform a skill gap analysis comparing candidate skills against job requirements."""
    resume, job = await _get_user_resume_and_job(resume_id, job_id, db, current_user.id)
    result = await analyze_skill_gap(resume, job)

    # Save artifact
    artifact = GeneratedArtifact(
        resume_id=resume.id,
        job_id=job.id if job else None,
        type=ArtifactType.skill_gap,
        content=result.model_dump(),
    )
    db.add(artifact)
    await db.commit()

    return result




