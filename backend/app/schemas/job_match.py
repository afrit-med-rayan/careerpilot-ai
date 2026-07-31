import uuid
from typing import List, Optional
from pydantic import BaseModel, Field


class MatchJobsRequest(BaseModel):
    query: str = Field(..., description="Job role or search query (e.g. 'Software Engineer', 'Data Scientist')")
    location: Optional[str] = Field(default=None, description="Optional location filter (e.g. 'Remote', 'New York')")


class JobMatchItem(BaseModel):
    job_id: uuid.UUID
    external_id: str
    source: str
    title: str
    company: str
    description: str
    location: Optional[str] = None
    url: str
    similarity_score: float = Field(ge=0.0, le=1.0, description="Semantic similarity score between resume and job")


class MatchJobsResponse(BaseModel):
    matches: List[JobMatchItem] = []
