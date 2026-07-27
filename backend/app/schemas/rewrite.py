from typing import List, Optional
from pydantic import BaseModel, Field


class RewriteRequest(BaseModel):
    job_description: Optional[str] = Field(
        default=None,
        description="Optional target job description to tailor bullet points towards."
    )


class RewriteItem(BaseModel):
    original: str = Field(description="The original resume bullet point or text snippet.")
    rewritten: str = Field(description="The improved, impact-driven bullet point.")
    reason: str = Field(description="Explanation of why this rewrite is better (e.g., strong action verb, metrics structure).")


class RewriteResponse(BaseModel):
    rewrites: List[RewriteItem] = []
