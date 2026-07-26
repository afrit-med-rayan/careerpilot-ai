import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_current_user
from app.db.models import Resume, User
from app.db.session import get_db, AsyncSessionLocal
from app.schemas import ResumeResponse, ResumeUploadResponse
from app.schemas.analysis import ResumeAnalysis
from app.services.analysis import analyze_resume
from app.services.parsing import parse_document, segment_resume
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

