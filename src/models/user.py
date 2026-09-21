from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, EmailStr

class UserRegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    preferred_role: Optional[str] = "Software Engineer"
    experience_level: Optional[str] = "Mid-Level"
    preferred_location: Optional[str] = "Bengaluru, India"
    remote_preference: Optional[str] = "Remote / Hybrid"

class UserLoginRequest(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    preferred_role: Optional[str] = None
    experience_level: str = "Mid-Level"
    preferred_location: str = "Remote"
    remote_preference: str = "Remote / Hybrid"
    years_of_experience: float = 2.0
    skills: List[str] = Field(default_factory=list)
    summary: str = ""
    saved_jobs_count: int = 0

class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class UserProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    preferred_role: Optional[str] = None
    experience_level: Optional[str] = None
    preferred_location: Optional[str] = None
    remote_preference: Optional[str] = None
    years_of_experience: Optional[float] = None
    skills: Optional[List[str]] = None
    summary: Optional[str] = None
    resume_text: Optional[str] = None

class SavedJobResponse(BaseModel):
    id: int
    job_id: str
    saved_at: str
    job: Dict[str, Any]

class ATSCheckRequest(BaseModel):
    job_id: Optional[str] = None
    custom_job_description: Optional[str] = None
    job_description: Optional[str] = None
    target_role: Optional[str] = None
    resume_text: Optional[str] = None
    candidate_years_exp: Optional[float] = None
    experience_level: Optional[str] = None

class CustomTailorRequest(BaseModel):
    target_role: Optional[str] = "Software Engineer"
    company: Optional[str] = "Target Employer"
    custom_job_description: Optional[str] = ""
    resume_text: Optional[str] = ""
    candidate_years_exp: Optional[float] = None

class ATSErrorItem(BaseModel):
    category: str  # Keyword, Experience, Formatting, Impact
    severity: str  # CRITICAL, WARNING, SUGGESTION
    message: str
    fix: str

class ATSCheckResponse(BaseModel):
    overall_score: float
    keyword_match_score: float
    semantic_relevance_score: float
    experience_alignment_score: float
    matched_skills: List[str]
    missing_critical_skills: List[str]
    detected_errors: List[ATSErrorItem]
    tailored_resume_bullet_fixes: List[str]
    actionable_recommendations: List[str]

class ContactMessageRequest(BaseModel):
    name: str
    email: str
    subject: str
    category: Optional[str] = "General"
    message: str

class ContactMessageResponse(BaseModel):
    id: int
    name: str
    email: str
    subject: str
    status: str
    created_at: str

class JobReportRequest(BaseModel):
    reason: str  # Expired, Broken link, Incorrect info, Duplicate, Other
    details: Optional[str] = ""
    reporter_email: Optional[str] = None

class JobReportResponse(BaseModel):
    id: int
    job_id: str
    reason: str
    status: str
    created_at: str

class CompanySummary(BaseModel):
    company_name: str
    job_count: int
    primary_locations: List[str]
    top_skills: List[str]
    sample_roles: List[str]

# Autonomous Career Agent Schemas
class CandidatePreferencesRequest(BaseModel):
    target_job_titles: Optional[List[str]] = Field(default_factory=lambda: ["Software Engineer", "Python Developer", "AI/ML Engineer"])
    preferred_locations: Optional[List[str]] = Field(default_factory=lambda: ["Remote", "India", "Bengaluru"])
    experience_level: Optional[str] = "Mid-Level"
    min_salary: Optional[float] = 500000.0
    salary_currency: Optional[str] = "INR"
    work_preference: Optional[str] = "Remote / Hybrid"
    operating_mode: Optional[str] = "FULLY_AUTONOMOUS"  # FULLY_AUTONOMOUS, APPROVAL_MODE, ASSISTED
    max_daily_applications: Optional[int] = 20
    max_portal_applications: Optional[int] = 5
    master_resume_text: Optional[str] = None

class CandidatePreferencesResponse(BaseModel):
    full_name: str
    email: str
    target_job_titles: List[str]
    preferred_locations: List[str]
    experience_level: str
    min_salary: float
    salary_currency: str
    work_preference: str
    operating_mode: str
    max_daily_applications: int
    max_portal_applications: int
    master_resume_text: str
    preferences: Optional[Dict[str, Any]] = None

class PortalPermissionUpdate(BaseModel):
    enabled: Optional[bool] = None
    max_daily_apps: Optional[int] = None
    max_daily_applications: Optional[int] = None

class LaTeXResumeRequest(BaseModel):
    job_id: Optional[str] = None
    custom_job_title: Optional[str] = None
    custom_company: Optional[str] = None
    custom_job_description: Optional[str] = None
    template_name: Optional[str] = "Modern ATS LaTeX"

class ColdEmailSendRequest(BaseModel):
    job_id: str
    contact_id: Optional[int] = None
    recipient_email: Optional[str] = None
    recipient_name: Optional[str] = None
    subject: Optional[str] = None
    body_text: Optional[str] = None

class ConfirmQuestionRequest(BaseModel):
    confirmed_answer: Optional[str] = None
    answer: Optional[str] = None
    save_to_knowledge_base: bool = True

class SimulateRecruiterResponseRequest(BaseModel):
    email_id: Optional[int] = None
    reply_text: Optional[str] = None
    response_body: Optional[str] = None

class KnowledgeBaseAddRequest(BaseModel):
    category: Optional[str] = "career"
    question_pattern: Optional[str] = None
    question: Optional[str] = None
    verified_answer: Optional[str] = None
    answer: Optional[str] = None
    is_sensitive: bool = False

