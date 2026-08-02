from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class CoverLetterRequest(BaseModel):
    tone: Literal["formal", "conversational", "enthusiastic"] = Field(
        default="formal", description="Desired tone of the cover letter"
    )


class CoverLetterResponse(BaseModel):
    cover_letter: str = Field(description="The complete generated cover letter text")


class InterviewQuestionItem(BaseModel):
    question: str = Field(description="Tailored interview question")
    type: Literal["technical", "behavioral"] = Field(description="Question type")
    suggested_answer_notes: str = Field(description="Key talking points based on resume experience")


class InterviewQuestionsResponse(BaseModel):
    questions: List[InterviewQuestionItem] = []


class SkillGapResponse(BaseModel):
    matched_skills: List[str] = []
    missing_skills: List[str] = []
    match_percentage: int = Field(ge=0, le=100, description="Skill match percentage")
