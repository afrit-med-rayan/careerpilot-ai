from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class AnalysisIssue(BaseModel):
    section: str = Field(description="e.g., 'experience', 'education', 'skills', 'summary'")
    type: Literal["weak_verb", "no_metric", "passive_voice", "missing_section", "formatting", "other"]
    detail: str = Field(description="A clear description of the issue")
    location_hint: Optional[str] = Field(default=None, description="A snippet of the text where the issue occurs, to help the user locate it")


class ResumeAnalysis(BaseModel):
    ats_score: int = Field(ge=0, le=100, description="Overall ATS score out of 100")
    issues: List[AnalysisIssue] = []
