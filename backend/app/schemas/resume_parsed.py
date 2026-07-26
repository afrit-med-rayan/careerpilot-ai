from typing import List, Optional
from pydantic import BaseModel


class ContactInfo(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None


class ExperienceItem(BaseModel):
    title: str
    company: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    bullets: List[str] = []


class EducationItem(BaseModel):
    degree: str
    institution: str
    year: Optional[str] = None


class ProjectItem(BaseModel):
    name: str
    description: str


class ParsedResume(BaseModel):
    contact: ContactInfo
    summary: Optional[str] = None
    experience: List[ExperienceItem] = []
    education: List[EducationItem] = []
    skills: List[str] = []
    certifications: List[str] = []
    projects: List[ProjectItem] = []
