from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class ApplicationStatus(str, Enum):
    DISCOVERED = "DISCOVERED"
    SHORTLISTED = "SHORTLISTED"
    APPLIED = "APPLIED"
    INTERVIEWING = "INTERVIEWING"
    OFFER = "OFFER"
    REJECTED = "REJECTED"

class TailoredPackage(BaseModel):
    job_id: str
    job_title: str
    company: str
    cover_letter: str
    resume_bullet_recommendations: List[str] = Field(default_factory=list)
    interview_prep_qa: List[Dict[str, str]] = Field(default_factory=list)
    custom_pitch: str = ""

class ApplicationCreate(BaseModel):
    job_id: str
    status: ApplicationStatus = ApplicationStatus.SHORTLISTED
    notes: Optional[str] = ""
    tailored_cover_letter: Optional[str] = ""
    interview_date: Optional[str] = None

class ApplicationUpdate(BaseModel):
    status: Optional[ApplicationStatus] = None
    notes: Optional[str] = None
    tailored_cover_letter: Optional[str] = None
    interview_date: Optional[str] = None

class ApplicationRecordSchema(BaseModel):
    id: int
    job_id: str
    job_title: str
    company: str
    location: str
    url: str
    source: str
    status: ApplicationStatus
    notes: Optional[str] = ""
    tailored_cover_letter: Optional[str] = ""
    interview_date: Optional[str] = None
    match_score: Optional[float] = None
    created_at: str
    updated_at: str
