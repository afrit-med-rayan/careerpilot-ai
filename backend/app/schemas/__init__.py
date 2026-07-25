import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Resume ────────────────────────────────────────────────────────────────────

class ResumeResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    file_url: str
    original_filename: str
    raw_text: str | None = None
    parsed_json: dict | None = None
    ats_score: int | None = None
    analysis_report: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ResumeUploadResponse(BaseModel):
    resume_id: uuid.UUID
    original_filename: str
    raw_text_preview: str  # First 300 chars for quick sanity check
    ocr_required: bool = False
    message: str
