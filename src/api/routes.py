import os
import json
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, Response
from sqlalchemy.orm import Session
from src.database.db import get_db
from src.database.models import (
    JobModel, ApplicationModel, ProfileModel, UserModel, SavedJobModel,
    CompanySourceModel, ContactMessageModel, JobReportModel,
    PortalPermissionModel, ResumeVersionModel, RecruiterContactModel,
    OutreachEmailModel, KnowledgeBaseModel, PendingQuestionModel,
    ActivityTimelineModel, LearningMetricModel
)
from src.models.job import JobPosting, UserProfile, MatchResult, JobFilter
from src.models.application import (
    ApplicationStatus, ApplicationCreate, ApplicationUpdate, 
    ApplicationRecordSchema, TailoredPackage
)
from src.models.user import (
    UserRegisterRequest, UserLoginRequest, AuthTokenResponse,
    UserResponse, UserProfileUpdateRequest, SavedJobResponse,
    ATSCheckRequest, ATSCheckResponse, CustomTailorRequest,
    ContactMessageRequest, ContactMessageResponse, JobReportRequest,
    JobReportResponse, CompanySummary,
    CandidatePreferencesRequest, CandidatePreferencesResponse,
    PortalPermissionUpdate, LaTeXResumeRequest, ColdEmailSendRequest,
    ConfirmQuestionRequest, SimulateRecruiterResponseRequest,
    KnowledgeBaseAddRequest
)
from src.services.auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, get_optional_current_user
)
from src.services.ats_checker import analyze_ats_compliance
from src.services.resume_parser import parse_resume_bytes
from src.services.latex_resume_generator import generate_latex_resume
from src.scrapers import registry
from src.agents import (
    ScoutAgent, AnalystAgent, TailorAgent, MarketIntelligenceAgent, TrackerAgent, llm
)
from src.agents.outreach import outreach_agent
from src.agents.learner import self_learning_agent
from src.analytics import AnalyticsEngine

logger = logging.getLogger(__name__)
api_router = APIRouter(prefix="/api")

# Initialize agent instances
scout_agent = ScoutAgent()
analyst_agent = AnalystAgent()
tailor_agent = TailorAgent()
market_agent = MarketIntelligenceAgent()
tracker_agent = TrackerAgent()
analytics_engine = AnalyticsEngine()

# Helpers
def _get_active_profile(db: Session, user: Optional[UserModel] = None) -> UserProfile:
    if user:
        return UserProfile(
            full_name=user.full_name,
            email=user.email,
            skills=user.skills or ["python", "fastapi", "sql"],
            target_roles=[user.preferred_role] if user.preferred_role else ["Software Engineer"],
            years_of_experience=user.years_of_experience or 2.0,
            summary=user.summary or ""
        )
    rec = db.query(ProfileModel).filter(ProfileModel.id == 1).first()
    if rec and rec.data:
        try:
            return UserProfile(**rec.data)
        except Exception:
            pass
    # Default initial profile
    return UserProfile(
        full_name="Candidate",
        email="candidate@example.com",
        skills=["python", "pytorch", "langchain", "sql", "fastapi", "docker", "web scraping", "beautifulsoup"],
        target_roles=["AI/ML Engineer", "Data Scientist", "Python Developer"],
        years_of_experience=2.0,
        summary="Experienced AI & Data systems engineer specializing in multi-agent orchestration and automated pipelines."
    )

def _save_active_profile(db: Session, profile: UserProfile) -> None:
    rec = db.query(ProfileModel).filter(ProfileModel.id == 1).first()
    if not rec:
        rec = ProfileModel(id=1, data_json=json.dumps(profile.model_dump()))
        db.add(rec)
    else:
        rec.data_json = json.dumps(profile.model_dump())
    db.commit()

def _user_to_response(user: UserModel, db: Session) -> UserResponse:
    saved_count = db.query(SavedJobModel).filter(SavedJobModel.user_id == user.id).count()
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        preferred_role=user.preferred_role or "Software Engineer",
        experience_level=user.experience_level or "Mid-Level",
        preferred_location=user.preferred_location or "Remote",
        remote_preference=user.remote_preference or "Remote / Hybrid",
        years_of_experience=user.years_of_experience or 2.0,
        skills=user.skills,
        summary=user.summary or "",
        saved_jobs_count=saved_count
    )

def _job_model_to_dict(r: JobModel, is_saved: bool = False) -> Dict[str, Any]:
    return {
        "id": r.id,
        "title": r.title,
        "company": r.company,
        "description": r.description or "",
        "location": r.location,
        "city": r.city,
        "country": r.country,
        "region": getattr(r, "region", "India"),
        "role_domain": getattr(r, "role_domain", "Engineering") or "Engineering",
        "is_fresher": getattr(r, "is_fresher", False),
        "remote": r.remote,
        "is_remote": r.remote,
        "remote_type": r.remote_type,
        "employment_type": r.employment_type,
        "salary_min": r.salary_min,
        "salary_max": r.salary_max,
        "salary_currency": r.salary_currency,
        "currency": r.salary_currency,
        "skills": r.skills_required,
        "skills_required": r.skills_required,
        "experience_level": r.experience_level,
        "apply_url": r.apply_url,
        "url": r.apply_url,
        "source": r.source,
        "source_name": r.source_name,
        "canonical_source": getattr(r, "canonical_source", r.source) or r.source,
        "discovered_via": getattr(r, "discovered_via", r.source) or r.source,
        "sources": r.sources if hasattr(r, "sources") else [r.source],
        "source_job_id": r.source_job_id,
        "published_at": r.published_at,
        "posted_date": r.published_at,
        "first_seen_at": r.first_seen_at.isoformat() if r.first_seen_at else None,
        "last_seen_at": r.last_seen_at.isoformat() if r.last_seen_at else None,
        "last_verified_at": r.last_verified_at.isoformat() if r.last_verified_at else None,
        "status": r.status,
        "verification_status": r.verification_status,
        "is_saved": is_saved
    }

def _job_model_to_posting(r: JobModel) -> JobPosting:
    return JobPosting(
        id=r.id,
        source=r.source,
        source_name=r.source_name,
        canonical_source=getattr(r, "canonical_source", r.source) or r.source,
        discovered_via=getattr(r, "discovered_via", r.source) or r.source,
        sources=r.sources if hasattr(r, "sources") else [r.source],
        source_job_id=r.source_job_id,
        title=r.title,
        company=r.company,
        location=r.location,
        city=r.city,
        country=r.country,
        region=getattr(r, "region", "India"),
        role_domain=getattr(r, "role_domain", "Engineering") or "Engineering",
        is_fresher=getattr(r, "is_fresher", False),
        remote=r.remote,
        is_remote=r.remote,
        remote_type=r.remote_type,
        employment_type=r.employment_type,
        salary_min=r.salary_min,
        salary_max=r.salary_max,
        salary_currency=r.salary_currency,
        currency=r.salary_currency,
        description=r.description,
        skills=r.skills_required,
        skills_required=r.skills_required,
        experience_level=r.experience_level,
        apply_url=r.apply_url,
        source_url=r.source_url or r.apply_url,
        url=r.apply_url,
        published_at=r.published_at,
        posted_date=r.published_at,
        status=r.status,
        verification_status=r.verification_status
    )

# Endpoints

@api_router.get("/system/status")
def get_system_status(db: Session = Depends(get_db)):
    """System health check, total jobs count, and active LLM configuration."""
    active_count = db.query(JobModel).filter(JobModel.status == "ACTIVE").count()
    verified_count = db.query(JobModel).filter(JobModel.verification_status == "VERIFIED").count()
    total_count = db.query(JobModel).count()
    app_count = db.query(ApplicationModel).count()
    profile = _get_active_profile(db)
    
    return {
        "status": "healthy",
        "jobs_in_database": active_count,
        "total_jobs_stored": total_count,
        "verified_live_jobs": verified_count,
        "applications_tracked": app_count,
        "candidate_name": profile.full_name,
        "candidate_skills_count": len(profile.skills),
        "llm_provider": llm.provider,
        "available_sources": [s.name for s in scout_agent.scrapers],
        "source_health": scout_agent.get_source_health_summary(db)
    }

# Authentication & User Profile Endpoints

@api_router.post("/auth/register", response_model=AuthTokenResponse)
def register_user(payload: UserRegisterRequest, db: Session = Depends(get_db)):
    """Register a new user account with secure bcrypt hashing."""
    email_clean = payload.email.strip().lower()
    if not email_clean or "@" not in email_clean:
        raise HTTPException(status_code=400, detail="A valid email address is required")
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long")

    existing = db.query(UserModel).filter(UserModel.email == email_clean).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists")

    hashed_pw = hash_password(payload.password)
    user = UserModel(
        email=email_clean,
        hashed_password=hashed_pw,
        full_name=payload.full_name.strip() or "Job Seeker",
        preferred_role=payload.preferred_role or "Software Engineer",
        experience_level=payload.experience_level or "Mid-Level",
        preferred_location=payload.preferred_location or "Bengaluru, India",
        remote_preference=payload.remote_preference or "Remote / Hybrid",
        years_of_experience=2.0,
        skills_json=json.dumps(["Python", "FastAPI", "SQL", "Docker"]),
        summary=""
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id), "email": user.email})
    return AuthTokenResponse(
        access_token=token,
        token_type="bearer",
        user=_user_to_response(user, db)
    )

@api_router.post("/auth/login", response_model=AuthTokenResponse)
def login_user(payload: UserLoginRequest, db: Session = Depends(get_db)):
    """Authenticate user and return JWT bearer token."""
    email_clean = payload.email.strip().lower()
    user = db.query(UserModel).filter(UserModel.email == email_clean).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"sub": str(user.id), "email": user.email})
    return AuthTokenResponse(
        access_token=token,
        token_type="bearer",
        user=_user_to_response(user, db)
    )

@api_router.get("/auth/me", response_model=UserResponse)
def get_current_user_profile(
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve the currently authenticated user's profile."""
    return _user_to_response(user, db)

@api_router.put("/auth/profile", response_model=UserResponse)
def update_current_user_profile(
    payload: UserProfileUpdateRequest,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update profile and job preferences for the authenticated user."""
    if payload.full_name is not None:
        user.full_name = payload.full_name.strip()
    if payload.preferred_role is not None:
        user.preferred_role = payload.preferred_role.strip()
    if payload.experience_level is not None:
        user.experience_level = payload.experience_level.strip()
    if payload.preferred_location is not None:
        user.preferred_location = payload.preferred_location.strip()
    if payload.remote_preference is not None:
        user.remote_preference = payload.remote_preference.strip()
    if payload.years_of_experience is not None:
        user.years_of_experience = payload.years_of_experience
    if payload.skills is not None:
        user.skills_json = json.dumps(payload.skills)
    if payload.summary is not None:
        user.summary = payload.summary
    if payload.resume_text is not None:
        user.resume_text = payload.resume_text

    db.commit()
    db.refresh(user)
    return _user_to_response(user, db)

@api_router.get("/profile", response_model=UserProfile)
def get_profile(
    user: Optional[UserModel] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Get active candidate profile."""
    return _get_active_profile(db, user)

@api_router.post("/profile", response_model=UserProfile)
def update_profile(profile: UserProfile, db: Session = Depends(get_db)):
    """Update candidate profile manually."""
    _save_active_profile(db, profile)
    return profile

@api_router.post("/profile/upload-resume")
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload resume (PDF or TXT), parse candidate skills and profile, and save as active."""
    content = await file.read()
    filename = file.filename or "resume.txt"
    temp_path = f"data/temp_{filename}"
    
    with open(temp_path, "wb") as f:
        f.write(content)
        
    try:
        profile = analyst_agent.parse_resume_file(temp_path)
        _save_active_profile(db, profile)
        return {
            "message": "Resume successfully parsed and indexed.",
            "profile": profile
        }
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@api_router.post("/scout/hunt")
def execute_job_hunt(
    query: Optional[str] = Query(None, description="Keywords for job titles/tags"),
    limit_per_source: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Trigger Scout Agent to autonomously harvest jobs across multiple live sources."""
    new_jobs = scout_agent.execute_hunt(query=query, limit_per_source=limit_per_source, db=db)
    total_in_db = db.query(JobModel).filter(JobModel.status == "ACTIVE").count()
    
    return {
        "message": f"Hunt complete. Discovered {len(new_jobs)} genuine opportunities.",
        "harvested_count": len(new_jobs),
        "total_jobs_in_database": total_in_db,
        "source_health": scout_agent.latest_source_health,
        "sample_titles": [j.title for j in new_jobs[:5]]
    }

@api_router.get("/scout/health")
def get_source_health(db: Session = Depends(get_db)):
    """Get live health and performance metrics for all external job sources."""
    return scout_agent.get_source_health_summary(db)

@api_router.post("/jobs/verify-urls")
def verify_jobs_urls(limit: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    """Run verification against active application URLs."""
    from src.services.lifecycle import batch_verify_active_job_urls
    return batch_verify_active_job_urls(db, limit=limit)

@api_router.get("/jobs/domains")
def get_job_domains(db: Session = Depends(get_db)):
    """Return count of active jobs grouped by career role domain."""
    from sqlalchemy import func
    rows = db.query(JobModel.role_domain, func.count(JobModel.id)).filter(JobModel.status == "ACTIVE").group_by(JobModel.role_domain).all()
    domain_counts = {r[0] or "Engineering": r[1] for r in rows}
    all_domains = [
        "Engineering", "Product", "Design", "Data & AI", "Marketing",
        "Sales", "Operations & HR", "Finance", "Customer Support", "QA"
    ]
    return {
        "domains": [{"name": d, "count": domain_counts.get(d, 0)} for d in all_domains],
        "total_active": sum(domain_counts.values())
    }

@api_router.get("/jobs")
def list_jobs(
    query: Optional[str] = None,
    role_domain: Optional[str] = None,
    region: Optional[str] = None,
    country: Optional[str] = None,
    city: Optional[str] = None,
    fresher_only: bool = False,
    remote_only: bool = False,
    source: Optional[str] = None,
    skills: Optional[str] = None,
    experience: Optional[str] = None,
    status: str = "ACTIVE",
    min_salary: Optional[float] = None,
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "date_desc",
    user: Optional[UserModel] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """List jobs stored in database with structured filters, sorting, and pagination."""
    q = db.query(JobModel)

    if status.upper() != "ALL":
        q = q.filter(JobModel.status == status.upper())

    if query and query.strip():
        term = f"%{query.strip()}%"
        q = q.filter(
            (JobModel.title.ilike(term)) |
            (JobModel.company.ilike(term)) |
            (JobModel.description.ilike(term)) |
            (JobModel.location.ilike(term)) |
            (JobModel.role_domain.ilike(term))
        )

    if role_domain and role_domain.lower() != "all":
        q = q.filter(JobModel.role_domain.ilike(role_domain.strip()))

    if remote_only:
        q = q.filter((JobModel.remote == True) | (JobModel.location.ilike("%remote%")))
    if region and region.lower() != "all":
        q = q.filter(JobModel.region.ilike(region))
    if country:
        q = q.filter(JobModel.country.ilike(country))
    if city:
        q = q.filter(JobModel.city.ilike(city))
    if source:
        q = q.filter(JobModel.source.ilike(f"%{source}%"))
    if experience:
        q = q.filter(JobModel.experience_level.ilike(f"%{experience}%"))
    if fresher_only:
        q = q.filter((JobModel.is_fresher == True) | (JobModel.experience_level.ilike("%fresher%") | JobModel.experience_level.ilike("%entry%")))
    if min_salary:
        q = q.filter((JobModel.salary_min >= min_salary) | (JobModel.salary_max >= min_salary))
    if skills:
        for sk in [s.strip() for s in skills.split(",") if s.strip()]:
            q = q.filter(JobModel.skills_json.ilike(f"%{sk}%"))

    if sort_by == "salary_desc":
        q = q.order_by(JobModel.salary_max.desc().nullslast(), JobModel.created_at.desc())
    elif sort_by == "title_asc":
        q = q.order_by(JobModel.title.asc())
    else:
        q = q.order_by(JobModel.created_at.desc())

    records = q.offset(offset).limit(limit).all()
    
    saved_ids = set()
    if user:
        saved_rows = db.query(SavedJobModel.job_id).filter(SavedJobModel.user_id == user.id).all()
        saved_ids = {r[0] for r in saved_rows}

    return [_job_model_to_dict(r, is_saved=(r.id in saved_ids)) for r in records]

@api_router.get("/jobs/{job_id}")
def get_job_detail(
    job_id: str,
    user: Optional[UserModel] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve full details for a single job posting by ID."""
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    is_saved = False
    if user:
        is_saved = db.query(SavedJobModel).filter(
            SavedJobModel.user_id == user.id,
            SavedJobModel.job_id == job_id
        ).first() is not None
        
    return _job_model_to_dict(job, is_saved=is_saved)

# Saved Jobs Endpoints

@api_router.get("/saved-jobs", response_model=List[SavedJobResponse])
def get_saved_jobs(
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all saved jobs for the authenticated user."""
    saved_records = (
        db.query(SavedJobModel)
        .filter(SavedJobModel.user_id == user.id)
        .order_by(SavedJobModel.saved_at.desc())
        .all()
    )
    results = []
    for s in saved_records:
        if s.job:
            results.append(SavedJobResponse(
                id=s.id,
                job_id=s.job_id,
                saved_at=s.saved_at.isoformat() if s.saved_at else "",
                job=_job_model_to_dict(s.job, is_saved=True)
            ))
    return results

@api_router.post("/saved-jobs/{job_id}")
def save_job(
    job_id: str,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save a job posting to user's saved list."""
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found")
        
    existing = db.query(SavedJobModel).filter(
        SavedJobModel.user_id == user.id,
        SavedJobModel.job_id == job_id
    ).first()
    
    if not existing:
        saved = SavedJobModel(user_id=user.id, job_id=job_id)
        db.add(saved)
        db.commit()
        
    return {"message": "Job saved successfully", "job_id": job_id, "is_saved": True}

@api_router.delete("/saved-jobs/{job_id}")
def unsave_job(
    job_id: str,
    user: UserModel = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a job posting from user's saved list."""
    existing = db.query(SavedJobModel).filter(
        SavedJobModel.user_id == user.id,
        SavedJobModel.job_id == job_id
    ).first()
    
    if existing:
        db.delete(existing)
        db.commit()
        
    return {"message": "Job removed from saved list", "job_id": job_id, "is_saved": False}

# Resume Document Upload & Denoised Extraction

@api_router.post("/resume/parse")
async def parse_resume_upload(file: UploadFile = File(...)):
    """Parse uploaded resume PDF or text file with layout-aware block extraction and noise filtering."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File exceeds 10MB limit")

    result = parse_resume_bytes(contents, file.filename)
    if not result["clean_text"]:
        raise HTTPException(status_code=422, detail="Could not extract readable text from document. Please ensure it is not an image-only scan.")

    return result

# ATS Score & Compliance Analysis

@api_router.post("/ats/check", response_model=ATSCheckResponse)
@api_router.post("/ats-check", response_model=ATSCheckResponse)
def check_ats_score(
    payload: ATSCheckRequest,
    user: Optional[UserModel] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Analyze resume compliance, detect errors, and generate tailored fixes."""
    job_title = payload.target_role or "Software Engineer"
    job_company = "Target Employer"
    job_description = payload.job_description or payload.custom_job_description or ""
    job_skills: List[str] = []

    if payload.job_id:
        job = db.query(JobModel).filter(JobModel.id == payload.job_id).first()
        if job:
            job_title = job.title
            job_company = job.company
            if not job_description:
                job_description = job.description or ""
            job_skills = job.skills_required or []

    # Get candidate info
    profile = _get_active_profile(db, user)
    candidate_skills = profile.skills or []

    years_exp = payload.candidate_years_exp
    if years_exp is None and payload.experience_level:
        el_lower = payload.experience_level.lower()
        if "fresher" in el_lower or "entry" in el_lower:
            years_exp = 0.5
        elif "senior" in el_lower or "lead" in el_lower:
            years_exp = 6.0
        else:
            years_exp = 3.0
    if years_exp is None:
        years_exp = profile.years_of_experience or 2.0

    resume_text = payload.resume_text or profile.summary or ""
    if user and user.resume_text and not payload.resume_text:
        resume_text = user.resume_text

    return analyze_ats_compliance(
        candidate_skills=candidate_skills,
        resume_text=resume_text,
        years_exp=years_exp,
        job_title=job_title,
        job_company=job_company,
        job_description=job_description,
        job_skills=job_skills
    )

@api_router.get("/match", response_model=List[MatchResult])
@api_router.post("/match", response_model=List[MatchResult])
def compute_job_matches(
    query: Optional[str] = None,
    region: Optional[str] = None,
    fresher_only: bool = False,
    limit: int = 50,
    user: Optional[UserModel] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Run Analyst Agent to calculate hybrid ATS & semantic match scores with region and fresher filtering."""
    profile = _get_active_profile(db, user)
    records = db.query(JobModel).filter(JobModel.status == "ACTIVE").all()
    if not records:
        scout_agent.execute_hunt(limit_per_source=8, db=db)
        records = db.query(JobModel).filter(JobModel.status == "ACTIVE").all()

    jobs: List[JobPosting] = []
    for r in records:
        # Region filter (India vs Global)
        job_region = getattr(r, "region", "India")
        if region and region.lower() != "all" and region.lower() != job_region.lower():
            continue

        # Fresher filter
        is_fresher = getattr(r, "is_fresher", False) or "fresher" in str(r.experience_level).lower() or "entry" in str(r.experience_level).lower()
        if fresher_only and not is_fresher:
            continue

        if query:
            match_str = f"{r.title} {r.company} {r.description} {r.location} {getattr(r, 'role_domain', '')}".lower()
            if query.lower() not in match_str:
                continue

        jobs.append(_job_model_to_posting(r))

    ranked = analyst_agent.rank_jobs(profile, jobs)
    return ranked[:limit]


@api_router.get("/subscription/status")
def get_subscription():
    """Get user subscription status, daily application credits, and entitlements."""
    from src.agents.copilot import copilot_agent
    return copilot_agent.get_subscription_status()

@api_router.post("/subscription/upgrade")
def upgrade_subscription(tier: str = "PRO"):
    """Upgrade user subscription to Pro or Lifetime tier for unlimited LazyApply auto-apply."""
    from src.agents.copilot import copilot_agent
    return copilot_agent.upgrade_subscription(tier=tier)

@api_router.post("/copilot/auto-apply-batch")
@api_router.post("/auto-apply/run")
def execute_lazyapply_batch(
    region: Optional[str] = None,
    fresher_only: bool = False,
    count: int = 5,
    role_query: Optional[str] = None,
    min_match_score: Optional[float] = None,
    user: Optional[UserModel] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """LazyApply & JobPilot-style 1-Click bulk auto-apply bot applying to top matching jobs with ATS credentials."""
    from src.agents.copilot import copilot_agent
    profile = _get_active_profile(db, user)
    
    # Get top matching jobs with optional role filter
    all_ranked = compute_job_matches(
        query=role_query,
        region=region,
        fresher_only=fresher_only,
        limit=max(count * 20, 100),
        user=user,
        db=db
    )
    if not all_ranked:
        return {
            "status": "NO_JOBS",
            "message": "No jobs found matching criteria.",
            "applied_count": 0,
            "applied_jobs": [],
            "execution_logs": ["Search yielded zero active jobs matching specified filters."]
        }

    # Filter by minimum match threshold if specified
    if min_match_score:
        all_ranked = [m for m in all_ranked if m.match_score >= min_match_score]
        if not all_ranked:
            return {
                "status": "NO_JOBS",
                "message": f"No jobs met the minimum ATS threshold of {min_match_score}%.",
                "applied_count": 0,
                "applied_jobs": [],
                "execution_logs": [f"Zero jobs reached the {min_match_score}% threshold."]
            }

    applied_job_ids = set(
        r[0] for r in db.query(ApplicationModel.job_id).filter(
            ApplicationModel.status.in_(["APPLIED", "INTERVIEW", "INTERVIEWING", "ACCEPTED", "OFFER"])
        ).all()
    )
    unapplied_ranked = [m for m in all_ranked if m.job_id not in applied_job_ids]
    candidate_pool = unapplied_ranked if unapplied_ranked else all_ranked
    ranked_subset = candidate_pool[:max(count * 5, 25)]
    job_ids = [m.job_id for m in ranked_subset]
    score_map = {m.job_id: m.match_score for m in ranked_subset}

    job_records = db.query(JobModel).filter(JobModel.id.in_(job_ids)).all()
    # Preserve score ordering
    record_map = {r.id: r for r in job_records}
    ordered_records = [record_map[jid] for jid in job_ids if jid in record_map]
    jobs_to_apply = [_job_model_to_posting(r) for r in ordered_records]

    return copilot_agent.execute_lazyapply_batch(
        jobs=jobs_to_apply,
        profile=profile,
        db=db,
        max_count=count,
        match_scores=score_map
    )

@api_router.post("/copilot/apply-one/{job_id}")
def apply_single_job_copilot(
    job_id: str,
    user: Optional[UserModel] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """1-Click Copilot Auto-Apply for an individual job posting."""
    from src.agents.copilot import copilot_agent
    job_record = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job_record:
        raise HTTPException(status_code=404, detail="Job not found")

    profile = _get_active_profile(db, user)
    job = _job_model_to_posting(job_record)
    match = analyst_agent.calculate_match(profile, job)
    return copilot_agent.apply_single_job(job, profile, db, match_score=match.match_score)

@api_router.get("/copilot/autofill/{job_id}")
@api_router.post("/copilot/autofill/{job_id}")
def get_copilot_autofill(
    job_id: str,
    user: Optional[UserModel] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Generate complete JobCopilot & FastApply auto-fill dossier, custom screening answers, and ATS scorecard."""
    from src.agents.copilot import copilot_agent
    job_record = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job_record:
        raise HTTPException(status_code=404, detail="Job not found")

    profile = _get_active_profile(db, user)
    job = _job_model_to_posting(job_record)

    match = analyst_agent.calculate_match(profile, job)
    return copilot_agent.generate_autofill_package(profile, job, match)

@api_router.post("/tailor/custom", response_model=TailoredPackage)
def generate_custom_tailored_package(
    payload: CustomTailorRequest,
    user: Optional[UserModel] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Generate tailored package for custom or external job description."""
    import hashlib
    profile = _get_active_profile(db, user)
    if payload.candidate_years_exp is not None:
        profile.years_of_experience = payload.candidate_years_exp
    if payload.resume_text:
        profile.summary = payload.resume_text

    target_role = payload.target_role or "Software Engineer"
    company = payload.company or "Target Employer"
    desc = payload.custom_job_description or f"Engineering role requiring {target_role} expertise."

    job_id = f"custom_{hashlib.md5(desc.encode()).hexdigest()[:10]}"
    job = JobPosting(
        id=job_id,
        title=target_role,
        company=company,
        location="Remote / Hybrid",
        description=desc,
        url="https://jobcopilot.ai/custom-apply",
        source="Custom JD Workspace",
        status="ACTIVE"
    )
    match = analyst_agent.calculate_match(profile, job)
    package = tailor_agent.generate_tailored_package(profile, job, match)
    return package

@api_router.post("/tailor/{job_id}", response_model=TailoredPackage)
def generate_tailored_package(
    job_id: str,
    user: Optional[UserModel] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Generate ATS cover letter, resume bullet recommendations, and interview prep questions."""
    job_record = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job_record:
        raise HTTPException(status_code=404, detail="Job not found")

    profile = _get_active_profile(db, user)
    job = _job_model_to_posting(job_record)

    match = analyst_agent.calculate_match(profile, job)
    package = tailor_agent.generate_tailored_package(profile, job, match)
    return package

@api_router.get("/analytics")
def get_analytics(db: Session = Depends(get_db)):
    """Compute rich market analytics, salary statistics, and candidate market fit."""
    profile = _get_active_profile(db)
    records = db.query(JobModel).filter(JobModel.status == "ACTIVE").all()
    if not records:
        scout_agent.execute_hunt(limit_per_source=8, db=db)
        records = db.query(JobModel).filter(JobModel.status == "ACTIVE").all()

    jobs: List[JobPosting] = [_job_model_to_posting(r) for r in records]
    return analytics_engine.generate_dashboard_analytics(jobs, profile)



@api_router.get("/applications", response_model=List[ApplicationRecordSchema])
def list_tracked_applications(status: Optional[ApplicationStatus] = None, db: Session = Depends(get_db)):
    """List tracked applications in Kanban."""
    return tracker_agent.list_applications(db, status=status)

@api_router.post("/applications", response_model=ApplicationRecordSchema)
def track_application(payload: ApplicationCreate, db: Session = Depends(get_db)):
    """Add job to tracker or update its stage."""
    return tracker_agent.add_to_tracker(db, payload)

@api_router.put("/applications/{app_id}", response_model=ApplicationRecordSchema)
def update_application_status(app_id: int, payload: ApplicationUpdate, db: Session = Depends(get_db)):
    """Update application notes, status, or dates."""
    res = tracker_agent.update_application(db, app_id, payload)
    if not res:
        raise HTTPException(status_code=404, detail="Application record not found")
    return res

@api_router.delete("/applications/{app_id}")
def delete_tracked_application(app_id: int, db: Session = Depends(get_db)):
    """Delete application from tracker."""
    success = tracker_agent.delete_application(db, app_id)
    if not success:
        raise HTTPException(status_code=404, detail="Application record not found")
    return {"message": "Application deleted from tracker"}

@api_router.get("/applications/funnel")
def get_tracker_funnel(db: Session = Depends(get_db)):
    """Get application conversion funnel metrics."""
    return tracker_agent.get_funnel_metrics(db)

# Source Health & Discovery Endpoints

@api_router.get("/sources/health")
def get_sources_health(db: Session = Depends(get_db)):
    """Return health metrics and diagnostic state for all registered intelligence adapters."""
    return scout_agent.get_source_health_summary(db)

@api_router.get("/companies", response_model=List[CompanySummary])
def get_companies_directory(db: Session = Depends(get_db)):
    """Return directory of tracked companies, active live job counts, primary locations, and key skills."""
    records = db.query(JobModel).filter(JobModel.status == "ACTIVE").all()
    
    comp_map: Dict[str, Dict[str, Any]] = {}
    for j in records:
        c_name = (j.company or "").strip()
        if not c_name:
            continue
        key = c_name.lower()
        if key not in comp_map:
            comp_map[key] = {
                "company_name": c_name,
                "job_count": 0,
                "locations": set(),
                "skills": set(),
                "roles": []
            }
        comp_map[key]["job_count"] += 1
        if j.location:
            comp_map[key]["locations"].add(j.location.strip())
        elif j.city:
            comp_map[key]["locations"].add(j.city.strip())
        if j.skills_required:
            for s in j.skills_required[:5]:
                comp_map[key]["skills"].add(s)
        if len(comp_map[key]["roles"]) < 3 and j.title:
            comp_map[key]["roles"].append(j.title)
            
    # Also incorporate companies from data/companies.json if not already represented
    companies_path = Path(__file__).parent.parent / "data" / "companies.json"
    if companies_path.exists():
        try:
            with open(companies_path, "r", encoding="utf-8") as f:
                seed_comps = json.load(f)
                for sc in seed_comps:
                    c_name = sc.get("company_name", "").strip()
                    if c_name and c_name.lower() not in comp_map:
                        comp_map[c_name.lower()] = {
                            "company_name": c_name,
                            "job_count": 0,
                            "locations": {sc.get("country", "India")},
                            "skills": set(),
                            "roles": []
                        }
        except Exception:
            pass

    # Build response list sorted by job count descending
    result = []
    for data in comp_map.values():
        result.append(CompanySummary(
            company_name=data["company_name"],
            job_count=data["job_count"],
            primary_locations=sorted(list(data["locations"]))[:4],
            top_skills=sorted(list(data["skills"]))[:6],
            sample_roles=data["roles"][:3]
        ))
    result.sort(key=lambda x: (-x.job_count, x.company_name.lower()))
    return result

# Contact & Job Reporting Endpoints

@api_router.post("/contact", response_model=ContactMessageResponse)
def submit_contact_message(payload: ContactMessageRequest, db: Session = Depends(get_db)):
    """Submit a contact or support message, persisted to the database."""
    name_clean = payload.name.strip()
    email_clean = payload.email.strip().lower()
    subject_clean = payload.subject.strip()
    msg_clean = payload.message.strip()

    if not name_clean:
        raise HTTPException(status_code=400, detail="Name is required")
    if not email_clean or "@" not in email_clean:
        raise HTTPException(status_code=400, detail="Valid email address is required")
    if not subject_clean:
        raise HTTPException(status_code=400, detail="Subject is required")
    if not msg_clean:
        raise HTTPException(status_code=400, detail="Message content cannot be empty")

    rec = ContactMessageModel(
        name=name_clean,
        email=email_clean,
        subject=subject_clean,
        category=payload.category or "General",
        message=msg_clean,
        status="RECEIVED"
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    return ContactMessageResponse(
        id=rec.id,
        name=rec.name,
        email=rec.email,
        subject=rec.subject,
        status=rec.status,
        created_at=rec.created_at.isoformat() if rec.created_at else ""
    )

@api_router.post("/jobs/{job_id}/report", response_model=JobReportResponse)
def report_job_issue(job_id: str, payload: JobReportRequest, db: Session = Depends(get_db)):
    """Report an expired, broken, or inaccurate job listing."""
    job = db.query(JobModel).filter(JobModel.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job listing not found")

    reason_clean = payload.reason.strip()
    if not reason_clean:
        raise HTTPException(status_code=400, detail="Report reason is required")

    rec = JobReportModel(
        job_id=job_id,
        reason=reason_clean,
        details=(payload.details or "").strip(),
        reporter_email=(payload.reporter_email or "").strip() or None,
        status="PENDING"
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    return JobReportResponse(
        id=rec.id,
        job_id=rec.job_id,
        reason=rec.reason,
        status=rec.status,
        created_at=rec.created_at.isoformat() if rec.created_at else ""
    )


# =============================================================================
# AUTONOMOUS CAREER AGENT ENDPOINTS
# =============================================================================

# 1. Candidate Preferences & Operating Mode

@api_router.get("/agent/preferences", response_model=CandidatePreferencesResponse)
def get_candidate_preferences(
    user: Optional[UserModel] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Get candidate preferences, operating mode, limits, and target roles."""
    if not user:
        user = db.query(UserModel).first()

    if user:
        resp_data = {
            "full_name": user.full_name,
            "email": user.email,
            "target_job_titles": user.target_job_titles or ["Software Engineer"],
            "preferred_locations": user.preferred_locations or ["Remote", "India"],
            "experience_level": user.experience_level or "Mid-Level",
            "min_salary": user.min_salary or 500000.0,
            "salary_currency": user.salary_currency or "INR",
            "work_preference": user.work_preference or "Remote / Hybrid",
            "operating_mode": user.operating_mode or "FULLY_AUTONOMOUS",
            "max_daily_applications": user.max_daily_applications or 20,
            "max_portal_applications": user.max_portal_applications or 5,
            "master_resume_text": user.resume_text or user.summary or ""
        }
    else:
        profile = _get_active_profile(db)
        resp_data = {
            "full_name": profile.full_name,
            "email": profile.email or "candidate@example.com",
            "target_job_titles": profile.target_roles[:3] if profile.target_roles else ["Software Engineer"],
            "preferred_locations": profile.preferred_locations or ["Remote", "India", "Bengaluru"],
            "experience_level": "Mid-Level",
            "min_salary": 500000.0,
            "salary_currency": "INR",
            "work_preference": "Remote / Hybrid",
            "operating_mode": "FULLY_AUTONOMOUS",
            "max_daily_applications": 20,
            "max_portal_applications": 5,
            "master_resume_text": profile.summary or ""
        }
    resp_data["preferences"] = dict(resp_data)
    return CandidatePreferencesResponse(**resp_data)

@api_router.post("/agent/preferences")
def update_candidate_preferences(
    payload: CandidatePreferencesRequest,
    user: Optional[UserModel] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Update candidate target roles, limits, operating mode, and Master Resume."""
    if not user:
        user = db.query(UserModel).first()

    if user:
        if payload.target_job_titles is not None:
            user.target_job_titles = payload.target_job_titles[:3]
        if payload.preferred_locations is not None:
            user.preferred_locations = payload.preferred_locations
        if payload.experience_level:
            user.experience_level = payload.experience_level
        if payload.min_salary is not None:
            user.min_salary = payload.min_salary
        if payload.salary_currency:
            user.salary_currency = payload.salary_currency
        if payload.work_preference:
            user.work_preference = payload.work_preference
        if payload.operating_mode:
            user.operating_mode = payload.operating_mode
        if payload.max_daily_applications is not None:
            user.max_daily_applications = payload.max_daily_applications
        if payload.max_portal_applications is not None:
            user.max_portal_applications = payload.max_portal_applications
        if payload.master_resume_text is not None:
            user.resume_text = payload.master_resume_text
            user.summary = payload.master_resume_text
        db.commit()
        db.refresh(user)

        # Also keep active profile in sync
        profile = _get_active_profile(db)
        if payload.target_job_titles:
            profile.target_roles = payload.target_job_titles[:3]
        if payload.preferred_locations:
            profile.preferred_locations = payload.preferred_locations
        if payload.master_resume_text:
            profile.summary = payload.master_resume_text
        _save_active_profile(db, profile)
        return get_candidate_preferences(user=user, db=db)

    # Global active profile update if no user exists
    profile = _get_active_profile(db)
    if payload.target_job_titles:
        profile.target_roles = payload.target_job_titles[:3]
    if payload.preferred_locations:
        profile.preferred_locations = payload.preferred_locations
    if payload.master_resume_text:
        profile.summary = payload.master_resume_text
    _save_active_profile(db, profile)
    return get_candidate_preferences(user=None, db=db)

@api_router.get("/agent/portals")
def list_portal_permissions(db: Session = Depends(get_db)):
    """List all candidate portal permissions and daily quotas."""
    records = db.query(PortalPermissionModel).order_by(PortalPermissionModel.category, PortalPermissionModel.display_name).all()
    return [
        {
            "id": r.id,
            "portal_name": r.portal_name,
            "display_name": r.display_name,
            "category": r.category,
            "source_type": r.category,
            "enabled": r.enabled,
            "max_daily_apps": r.max_daily_apps,
            "max_daily_applications": r.max_daily_apps,
            "requires_auth": r.requires_auth,
            "auth_status": r.auth_status,
            "apply_mode": r.apply_mode,
            "description": r.description
        }
        for r in records
    ]

@api_router.put("/agent/portals/{portal_name}")
def update_portal_permission(
    portal_name: str,
    payload: PortalPermissionUpdate,
    db: Session = Depends(get_db)
):
    """Enable/disable a job portal or adjust its daily application cap."""
    rec = db.query(PortalPermissionModel).filter(PortalPermissionModel.portal_name == portal_name.lower()).first()
    if not rec:
        raise HTTPException(status_code=404, detail=f"Portal '{portal_name}' not found")

    if payload.enabled is not None:
        rec.enabled = payload.enabled
    if payload.max_daily_apps is not None:
        rec.max_daily_apps = payload.max_daily_apps
    elif payload.max_daily_applications is not None:
        rec.max_daily_apps = payload.max_daily_applications

    db.commit()
    return {
        "message": f"Portal '{rec.display_name}' updated successfully",
        "portal": rec.portal_name,
        "portal_name": rec.portal_name,
        "enabled": rec.enabled,
        "max_daily_apps": rec.max_daily_apps,
        "max_daily_applications": rec.max_daily_apps
    }


# 2. Overleaf & LaTeX Resume Generator Endpoints

@api_router.post("/resumes/generate-latex")
def generate_latex_resume_endpoint(
    payload: LaTeXResumeRequest,
    user: Optional[UserModel] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Generate job-specific compile-ready ATS LaTeX resume with Overleaf link and emphasized skills."""
    profile = _get_active_profile(db, user)
    
    # Target Job
    if payload.job_id:
        j_rec = db.query(JobModel).filter(JobModel.id == payload.job_id).first()
        if not j_rec:
            raise HTTPException(status_code=404, detail="Job not found")
        job = _job_model_to_posting(j_rec)
    else:
        job = JobPosting(
            title=payload.custom_job_title or "Software Engineer",
            company=payload.custom_company or "Target Company",
            description=payload.custom_job_description or "Software engineering role requiring modern programming practices.",
            location="Remote / Hybrid",
            url="https://jobcopilot.ai/apply"
        )

    match = analyst_agent.calculate_match(profile, job)
    template = payload.template_name or "Modern ATS LaTeX"
    res = generate_latex_resume(profile, job, match, template_name=template)

    # Persist version
    version_rec = ResumeVersionModel(
        job_id=job.id,
        version_label=res["version_label"],
        latex_source=res["latex_source"],
        template_name=template,
        emphasized_skills_json=json.dumps(res["emphasized_skills"]),
        overleaf_url=res["overleaf_url"]
    )
    db.add(version_rec)
    db.commit()
    db.refresh(version_rec)

    res["id"] = version_rec.id
    res["latex_code"] = res["latex_source"]

    # Link to application if exists, or create one
    app_rec = db.query(ApplicationModel).filter(ApplicationModel.job_id == job.id).first()
    if app_rec:
        app_rec.resume_version_id = version_rec.id
        app_rec.latex_resume_code = res["latex_source"]
        app_rec.overleaf_url = res["overleaf_url"]
        db.commit()
        db.refresh(app_rec)
    else:
        app_rec = ApplicationModel(
            job_id=job.id,
            status="PREPARED",
            portal=job.source or "Direct Portal",
            resume_version_id=version_rec.id,
            latex_resume_code=res["latex_source"],
            overleaf_url=res["overleaf_url"],
            match_score=match.match_score if hasattr(match, 'match_score') else 85.0
        )
        db.add(app_rec)
        db.commit()
        db.refresh(app_rec)

    res["application_id"] = app_rec.id
    return res

@api_router.get("/resumes/{app_id}/latex")
def get_application_latex_resume(app_id: int, db: Session = Depends(get_db)):
    """Retrieve LaTeX code, Overleaf link, and emphasized skills for an application."""
    app_rec = db.query(ApplicationModel).filter(ApplicationModel.id == app_id).first()
    version_rec = None
    if app_rec and app_rec.resume_version_id:
        version_rec = db.query(ResumeVersionModel).filter(ResumeVersionModel.id == app_rec.resume_version_id).first()
    elif not app_rec:
        version_rec = db.query(ResumeVersionModel).filter(ResumeVersionModel.id == app_id).first()

    if not app_rec and not version_rec:
        raise HTTPException(status_code=404, detail="Application or resume record not found")

    tex_code = (version_rec.latex_source if version_rec else None) or (app_rec.latex_resume_code if app_rec else "")
    overleaf = (version_rec.overleaf_url if version_rec else None) or (app_rec.overleaf_url if app_rec else "https://www.overleaf.com/docs")
    template = (version_rec.template_name if version_rec else None) or "Modern ATS LaTeX"
    skills = version_rec.emphasized_skills if version_rec else []

    return {
        "application_id": app_rec.id if app_rec else app_id,
        "job_id": app_rec.job_id if app_rec else (version_rec.job_id if version_rec else ""),
        "resume_version_id": version_rec.id if version_rec else (app_rec.resume_version_id if app_rec else app_id),
        "latex_source": tex_code,
        "latex_code": tex_code,
        "overleaf_url": overleaf,
        "template_name": template,
        "emphasized_skills": skills
    }

@api_router.get("/resumes/{app_id}/download-tex")
def download_tex_resume(app_id: int, db: Session = Depends(get_db)):
    """Download .tex LaTeX resume file directly."""
    app_rec = db.query(ApplicationModel).filter(ApplicationModel.id == app_id).first()
    if not app_rec:
        raise HTTPException(status_code=404, detail="Application not found")

    tex_code = app_rec.latex_resume_code
    if app_rec.resume_version_id:
        ver = db.query(ResumeVersionModel).filter(ResumeVersionModel.id == app_rec.resume_version_id).first()
        if ver and ver.latex_source:
            tex_code = ver.latex_source

    if not tex_code:
        profile = _get_active_profile(db)
        job_rec = db.query(JobModel).filter(JobModel.id == app_rec.job_id).first()
        job = _job_model_to_posting(job_rec) if job_rec else JobPosting(
            title="Software Engineer",
            company="Target Employer",
            location="Remote",
            url="https://jobcopilot.ai/apply"
        )
        pkg = generate_latex_resume(profile, job)
        tex_code = pkg["latex_source"]
        app_rec.latex_resume_code = tex_code
        db.commit()

    filename = f"Resume_Application_{app_id}.tex"
    return Response(
        content=tex_code,
        media_type="text/x-tex",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# 3. Recruiter Discovery & Cold Outreach Endpoints

@api_router.get("/outreach/contacts")
def list_discovered_contacts(company: Optional[str] = None, db: Session = Depends(get_db)):
    """List discovered HR professionals, recruiters, and talent partners."""
    query = db.query(RecruiterContactModel)
    if company:
        query = query.filter(RecruiterContactModel.company.ilike(f"%{company}%"))
    records = query.order_by(RecruiterContactModel.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "company": r.company,
            "person_name": r.person_name,
            "role_title": r.role_title,
            "email": r.email,
            "linkedin_url": r.linkedin_url,
            "confidence_score": r.confidence_score,
            "source": r.source,
            "verified": r.verified,
            "created_at": r.created_at.isoformat() if r.created_at else ""
        }
        for r in records
    ]

@api_router.get("/outreach/emails")
def list_outreach_emails(status: Optional[str] = None, db: Session = Depends(get_db)):
    """List cold outreach emails, delivery states, replies, and sentiment classifications."""
    query = db.query(OutreachEmailModel)
    if status:
        query = query.filter(OutreachEmailModel.status == status.upper())
    records = query.order_by(OutreachEmailModel.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "recipient_name": r.recipient_name,
            "recipient_email": r.recipient_email,
            "company": r.company,
            "subject": r.subject,
            "body_text": r.body_text,
            "status": r.status,
            "sent_at": r.sent_at.isoformat() if r.sent_at else None,
            "reply_status": r.reply_status,
            "reply_text": r.reply_text,
            "reply_category": r.reply_category,
            "follow_up_count": r.follow_up_count,
            "created_at": r.created_at.isoformat() if r.created_at else ""
        }
        for r in records
    ]

@api_router.post("/outreach/send")
def send_cold_email_endpoint(
    payload: ColdEmailSendRequest,
    user: Optional[UserModel] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Send or queue personalized cold email to target company recruiter."""
    job_rec = db.query(JobModel).filter(JobModel.id == payload.job_id).first()
    if not job_rec:
        raise HTTPException(status_code=404, detail="Job not found")

    profile = _get_active_profile(db, user)
    job = _job_model_to_posting(job_rec)

    # Resolve Contact
    contact = None
    if payload.contact_id:
        contact = db.query(RecruiterContactModel).filter(RecruiterContactModel.id == payload.contact_id).first()
    if not contact:
        contacts = outreach_agent.discover_contacts_for_company(job.company, job.title, db, limit=1)
        contact = contacts[0] if contacts else None

    recip_email = payload.recipient_email or (contact.email if contact else f"recruiting@{job.company.lower().replace(' ', '')}.com")
    recip_name = payload.recipient_name or (contact.person_name if contact else "Hiring Team")

    if payload.subject and payload.body_text:
        subject = payload.subject
        body = payload.body_text
    else:
        email_data = outreach_agent.generate_personalized_cold_email(profile, job, contact or RecruiterContactModel(
            company=job.company,
            person_name=recip_name,
            email=recip_email,
            role_title="Recruiter"
        ))
        subject = email_data["subject"]
        body = email_data["body_text"]

    email_rec = OutreachEmailModel(
        contact_id=contact.id if contact else None,
        job_id=job.id,
        recipient_email=recip_email,
        recipient_name=recip_name,
        company=job.company,
        subject=subject,
        body_text=body,
        status="SENT",
        sent_at=datetime.now(timezone.utc),
        reply_status="NO_REPLY"
    )
    db.add(email_rec)

    # Log timeline event
    tl = ActivityTimelineModel(
        stage_number=6,
        event_type="COLD_EMAIL_SENT",
        title=f"Personalized cold email dispatched to {recip_name} at {job.company}",
        job_id=job.id,
        company=job.company,
        details_json=json.dumps({"subject": subject, "recipient": recip_email})
    )
    db.add(tl)
    db.commit()
    db.refresh(email_rec)

    return {
        "status": "SENT",
        "email_id": email_rec.id,
        "recipient": recip_name,
        "email": recip_email,
        "subject": subject,
        "message": f"Personalized cold outreach successfully sent to {recip_name}!"
    }

@api_router.post("/outreach/simulate-response")
def simulate_recruiter_response(
    payload: SimulateRecruiterResponseRequest,
    db: Session = Depends(get_db)
):
    """Categorize inbound recruiter reply into 7 semantic classes and record learning feedback."""
    text_to_analyze = payload.reply_text or payload.response_body or ""
    cat = outreach_agent.categorize_recruiter_response(text_to_analyze)

    email_rec = None
    if payload.email_id:
        email_rec = db.query(OutreachEmailModel).filter(OutreachEmailModel.id == payload.email_id).first()
        if email_rec:
            email_rec.reply_status = "REPLIED"
            email_rec.reply_text = text_to_analyze
            email_rec.reply_category = cat["category"]
            
            # Log timeline event
            tl = ActivityTimelineModel(
                stage_number=8,
                event_type="RESPONSE_ANALYZED",
                title=f"Recruiter response analyzed: {cat['label']} from {email_rec.company}",
                job_id=email_rec.job_id,
                company=email_rec.company,
                details_json=json.dumps({"category": cat["category"], "recommended_action": cat["recommended_action"]})
            )
            db.add(tl)

            # Record Self-Learning Feedback
            self_learning_agent.record_learning_feedback("Direct Role Reference", "Modern ATS LaTeX", cat["category"], db)
            db.commit()

    return {
        "status": "ANALYZED",
        "category": cat["category"],
        "label": cat["label"],
        "sentiment_score": cat["sentiment_score"],
        "recommended_action": cat["recommended_action"]
    }

@api_router.post("/outreach/trigger-followups")
def trigger_scheduled_followups(cadence_days: int = 4, db: Session = Depends(get_db)):
    """Check unreplied emails and trigger scheduled follow-ups."""
    results = outreach_agent.schedule_followups(db, cadence_days=cadence_days)
    return {
        "status": "SUCCESS",
        "triggered_count": len(results),
        "followups_sent": len(results),
        "followups": results
    }


# 4. Self-Learning & Candidate Knowledge Base Endpoints

@api_router.get("/learner/insights")
def get_self_learning_insights(db: Session = Depends(get_db)):
    """Return empirical performance metrics and optimized generation weights."""
    return self_learning_agent.analyze_application_outcomes(db)

@api_router.get("/learner/knowledge-base")
def list_knowledge_base_items(db: Session = Depends(get_db)):
    """List verified Candidate Knowledge Base questions and answers."""
    items = db.query(KnowledgeBaseModel).order_by(KnowledgeBaseModel.use_count.desc()).all()
    return [
        {
            "id": i.id,
            "category": i.category,
            "question": i.question_pattern,
            "question_pattern": i.question_pattern,
            "verified_answer": i.verified_answer,
            "is_sensitive": i.is_sensitive,
            "use_count": i.use_count,
            "created_at": i.created_at.isoformat() if i.created_at else ""
        }
        for i in items
    ]

@api_router.post("/learner/knowledge-base")
def add_knowledge_base_item(
    payload: KnowledgeBaseAddRequest,
    db: Session = Depends(get_db)
):
    """Add a verified answer to the Candidate Knowledge Base."""
    q = payload.question_pattern or payload.question or ""
    a = payload.verified_answer or payload.answer or ""
    cat = payload.category or "career"

    rec = KnowledgeBaseModel(
        category=cat,
        question_pattern=q,
        verified_answer=a,
        is_sensitive=payload.is_sensitive,
        verified_by_user=True,
        use_count=0
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return {
        "message": "Verified answer added to Candidate Knowledge Base",
        "id": rec.id,
        "question": q,
        "question_pattern": q,
        "verified_answer": a,
        "category": cat
    }

@api_router.get("/learner/pending-questions")
def list_pending_questions(db: Session = Depends(get_db)):
    """List uncertain or sensitive application questions awaiting candidate confirmation."""
    records = db.query(PendingQuestionModel).filter(PendingQuestionModel.status == "AWAITING_CONFIRMATION").all()
    return [
        {
            "id": r.id,
            "job_id": r.job_id,
            "company": r.company,
            "question": r.question,
            "suggested_answer": r.suggested_answer,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else ""
        }
        for r in records
    ]

@api_router.post("/learner/confirm-question/{question_id}")
def confirm_pending_question_endpoint(
    question_id: int,
    payload: ConfirmQuestionRequest,
    db: Session = Depends(get_db)
):
    """Confirm candidate's verified answer for an uncertain question."""
    return self_learning_agent.confirm_pending_question(
        question_id=question_id,
        confirmed_answer=payload.confirmed_answer,
        save_to_kb=payload.save_to_knowledge_base,
        db=db
    )


# 5. Human Approval Controls & 9-Step Timeline Endpoints

@api_router.get("/agent/approvals")
def get_approval_queue(db: Session = Depends(get_db)):
    """Get pending applications and outreach emails held for candidate approval in Approval Mode."""
    pending_apps = db.query(ApplicationModel).filter(ApplicationModel.status == "PENDING_APPROVAL").all()
    pending_emails = db.query(OutreachEmailModel).filter(OutreachEmailModel.status == "PENDING_APPROVAL").all()

    app_list = []
    for a in pending_apps:
        job = db.query(JobModel).filter(JobModel.id == a.job_id).first()
        app_list.append({
            "id": a.id,
            "job_id": a.job_id,
            "title": job.title if job else "Role",
            "company": job.company if job else "Company",
            "portal": a.portal,
            "match_score": a.match_score,
            "resume_version_id": a.resume_version_id,
            "overleaf_url": a.overleaf_url,
            "created_at": a.created_at.isoformat() if a.created_at else ""
        })

    email_list = [
        {
            "id": e.id,
            "company": e.company,
            "recipient_name": e.recipient_name,
            "recipient_email": e.recipient_email,
            "subject": e.subject,
            "body_text": e.body_text,
            "created_at": e.created_at.isoformat() if e.created_at else ""
        }
        for e in pending_emails
    ]

    return {
        "pending_applications_count": len(app_list),
        "pending_emails_count": len(email_list),
        "applications": app_list,
        "pending_applications": app_list,
        "emails": email_list,
        "pending_emails": email_list
    }

@api_router.post("/agent/approvals/application/{app_id}/approve")
def approve_pending_application(app_id: int, db: Session = Depends(get_db)):
    """Approve application in queue and mark as APPLIED."""
    app = db.query(ApplicationModel).filter(ApplicationModel.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    app.status = "APPLIED"
    job = db.query(JobModel).filter(JobModel.id == app.job_id).first()

    # Log timeline event
    tl = ActivityTimelineModel(
        stage_number=4,
        event_type="APPLICATION_SUBMITTED",
        title=f"Application approved & submitted for {job.title if job else 'job'}",
        job_id=app.job_id,
        company=job.company if job else "",
        details_json='{"approved_by_candidate": true}'
    )
    db.add(tl)
    db.commit()
    return {"message": "Application approved and dispatched", "application_id": app_id, "status": "APPLIED"}

@api_router.post("/agent/approvals/application/{app_id}/reject")
def reject_pending_application(app_id: int, db: Session = Depends(get_db)):
    """Reject and dismiss a pending application."""
    app = db.query(ApplicationModel).filter(ApplicationModel.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    app.status = "REJECTED"
    db.commit()
    return {"message": "Application rejected", "application_id": app_id}

@api_router.post("/agent/approvals/email/{email_id}/approve")
def approve_pending_email(email_id: int, db: Session = Depends(get_db)):
    """Approve and dispatch a pending cold outreach email."""
    em = db.query(OutreachEmailModel).filter(OutreachEmailModel.id == email_id).first()
    if not em:
        raise HTTPException(status_code=404, detail="Outreach email not found")

    em.status = "SENT"
    em.sent_at = datetime.now(timezone.utc)

    # Log timeline event
    tl = ActivityTimelineModel(
        stage_number=6,
        event_type="COLD_EMAIL_SENT",
        title=f"Cold email approved & sent to {em.recipient_name} at {em.company}",
        job_id=em.job_id,
        company=em.company,
        details_json='{"approved_by_candidate": true}'
    )
    db.add(tl)
    db.commit()
    return {"message": "Cold email approved and sent", "email_id": email_id, "status": "SENT"}

@api_router.post("/agent/approvals/email/{email_id}/reject")
def reject_pending_email(email_id: int, db: Session = Depends(get_db)):
    """Reject a pending cold email."""
    em = db.query(OutreachEmailModel).filter(OutreachEmailModel.id == email_id).first()
    if not em:
        raise HTTPException(status_code=404, detail="Outreach email not found")
    em.status = "DISMISSED"
    db.commit()
    return {"message": "Cold email dismissed", "email_id": email_id}

@api_router.get("/agent/timeline")
def get_activity_timeline(limit: int = 50, db: Session = Depends(get_db)):
    """Fetch chronological 9-step activity timeline of agent actions."""
    events = db.query(ActivityTimelineModel).order_by(ActivityTimelineModel.timestamp.desc()).limit(limit).all()
    return [
        {
            "id": e.id,
            "stage": e.event_type,
            "stage_number": e.stage_number,
            "event_type": e.event_type,
            "title": e.title,
            "job_id": e.job_id,
            "company": e.company,
            "details": e.details,
            "timestamp": e.timestamp.isoformat() if e.timestamp else ""
        }
        for e in events
    ]

@api_router.post("/agent/run-cycle")
def trigger_autonomous_agent_cycle(
    count: int = 5,
    limit: Optional[int] = None,
    mode: Optional[str] = None,
    user: Optional[UserModel] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Trigger the autonomous agent cycle across the 9-stage pipeline."""
    from src.agents.copilot import copilot_agent
    actual_count = limit if limit is not None else count
    if not user:
        user = db.query(UserModel).first()

    profile = _get_active_profile(db, user)
    op_mode = mode or (user.operating_mode if user else "FULLY_AUTONOMOUS")

    # Get top matching jobs matching target roles, falling back to general pool if 0 matches
    query_term = profile.target_roles[0] if profile.target_roles else None
    ranked = compute_job_matches(
        query=query_term,
        limit=10000,  # fetch all — cycle now processes every suitable job
        user=user,
        db=db
    )
    if not ranked:
        ranked = compute_job_matches(
            query=None,
            limit=10000,
            user=user,
            db=db
        )

    if not ranked:
        return {
            "status": "NO_JOBS",
            "message": "No jobs found matching criteria.",
            "jobs_processed": 0,
            "applications_created": 0,
            "applied_jobs": []
        }

    applied_job_ids = set(
        r[0] for r in db.query(ApplicationModel.job_id).filter(
            ApplicationModel.status.in_(["APPLIED", "INTERVIEW", "INTERVIEWING", "ACCEPTED", "OFFER"])
        ).all()
    )
    unapplied_ranked = [m for m in ranked if m.job_id not in applied_job_ids]
    # Use ALL unapplied suitable jobs — no artificial cap.
    candidate_pool = unapplied_ranked if unapplied_ranked else ranked
    job_ids = [m.job_id for m in candidate_pool]
    score_map = {m.job_id: m.match_score for m in candidate_pool}

    job_records = db.query(JobModel).filter(JobModel.id.in_(job_ids)).all()
    record_map = {r.id: r for r in job_records}
    jobs = [_job_model_to_posting(record_map[jid]) for jid in job_ids if jid in record_map]

    res = copilot_agent.execute_autonomous_cycle(
        jobs=jobs,
        profile=profile,
        db=db,
        operating_mode=op_mode,
        max_applications=actual_count,  # kept for backward-compat but no longer a hard cap
        match_scores=score_map
    )
    res["jobs_processed"] = res.get("processed_count", len(res.get("applied_jobs", [])))
    res["applications_created"] = res.get("applied_count", len(res.get("applied_jobs", [])))
    return res



# 6. Centralized Comprehensive Analytics Dashboard Endpoint

@api_router.get("/analytics/agent-dashboard")
def get_agent_dashboard_analytics(
    user: Optional[UserModel] = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Centralized dashboard analytics covering Job Stats, Application Stats, Outreach Stats, and Learning Metrics."""
    from datetime import datetime, timezone, timedelta

    def _as_naive_utc(dt):
        if dt is None:
            return None
        if hasattr(dt, "tzinfo") and dt.tzinfo is not None:
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt

    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
    today_start = now_naive.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now_naive - timedelta(days=7)
    month_start = now_naive - timedelta(days=30)

    # 1. Job Discovery Statistics
    all_jobs = db.query(JobModel).filter(JobModel.status == "ACTIVE").all()
    total_jobs = len(all_jobs)

    jobs_by_portal = {}
    jobs_by_domain = {}
    jobs_by_company = {}
    jobs_by_title = {}
    for j in all_jobs:
        src = j.source or "Direct ATS"
        jobs_by_portal[src] = jobs_by_portal.get(src, 0) + 1

        dom = getattr(j, "role_domain", "Engineering") or "Engineering"
        jobs_by_domain[dom] = jobs_by_domain.get(dom, 0) + 1

        comp = j.company or "Other"
        jobs_by_company[comp] = jobs_by_company.get(comp, 0) + 1

        title_key = j.title or "General Role"
        jobs_by_title[title_key] = jobs_by_title.get(title_key, 0) + 1

    top_companies = sorted(jobs_by_company.items(), key=lambda x: x[1], reverse=True)[:6]

    # 2. Application Tracker Statistics
    apps = db.query(ApplicationModel).all()
    total_apps = len(apps)
    apps_submitted = sum(1 for a in apps if a.status in ["APPLIED", "INTERVIEWING", "OFFER"])
    apps_in_progress = sum(1 for a in apps if a.status in ["SHORTLISTED", "PENDING_APPROVAL", "ASSISTED_READY"])
    apps_interviewing = sum(1 for a in apps if a.status == "INTERVIEWING")
    apps_offers = sum(1 for a in apps if a.status == "OFFER")
    apps_rejections = sum(1 for a in apps if a.status == "REJECTED")
    apps_viewed = sum(1 for a in apps if a.status in ["VIEWED", "INTERVIEWING", "OFFER"] or getattr(a, "application_result", "") == "VIEWED")
    apps_no_response = sum(1 for a in apps if a.status == "APPLIED" and getattr(a, "application_result", "PENDING") in ["PENDING", "NO_RESPONSE", None])

    apps_today = sum(1 for a in apps if _as_naive_utc(a.created_at) and _as_naive_utc(a.created_at) >= today_start)
    apps_this_week = sum(1 for a in apps if _as_naive_utc(a.created_at) and _as_naive_utc(a.created_at) >= week_start)
    apps_this_month = sum(1 for a in apps if _as_naive_utc(a.created_at) and _as_naive_utc(a.created_at) >= month_start)

    # 3. Outreach & Recruiter Statistics
    contacts_count = db.query(RecruiterContactModel).count()
    emails = db.query(OutreachEmailModel).all()
    total_emails_sent = sum(1 for e in emails if e.status == "SENT")
    emails_replied = sum(1 for e in emails if e.reply_status == "REPLIED")
    positive_replies = sum(1 for e in emails if e.reply_category in ["POSITIVE", "INTERVIEW", "INTERVIEW_OPPORTUNITY"])
    negative_replies = sum(1 for e in emails if e.reply_category in ["REJECTION", "NEGATIVE"])
    followups_sent = sum(e.follow_up_count for e in emails)
    pending_followups = sum(1 for e in emails if e.status == "SENT" and e.reply_status == "NO_REPLY" and e.follow_up_count == 0)

    # 4. Email Category Distribution
    email_categories = {
        "INTERVIEW": 0,
        "POSITIVE": 0,
        "ACTION_REQUIRED": 0,
        "FOLLOWUP_REQUIRED": 0,
        "REJECTION": 0,
        "NEGATIVE": 0,
        "NEUTRAL": 0
    }
    for e in emails:
        cat = e.reply_category
        if cat:
            if cat == "INTERVIEW_OPPORTUNITY": cat = "INTERVIEW"
            if cat == "FOLLOW_UP_REQUIRED": cat = "FOLLOWUP_REQUIRED"
            if cat in email_categories:
                email_categories[cat] += 1

    # 5. Timeline Recent Items
    recent_timeline = db.query(ActivityTimelineModel).order_by(ActivityTimelineModel.timestamp.desc()).limit(8).all()

    # 6. Operating Mode & Limits
    op_mode = user.operating_mode if user else "FULLY_AUTONOMOUS"
    max_daily = user.max_daily_applications if user else 20
    max_portal = user.max_portal_applications if user else 5

    # 7. Self-Learning & Portals Lookup
    learning_insights = self_learning_agent.analyze_application_outcomes(db)
    portal_records = db.query(PortalPermissionModel).all()
    portals_dict = {
        p.portal_name: {
            "display_name": p.display_name,
            "category": p.category,
            "source_type": p.category,
            "enabled": p.enabled,
            "active_jobs": jobs_by_portal.get(p.portal_name, 0),
            "max_daily_apps": p.max_daily_apps
        }
        for p in portal_records
    }

    return {
        "operating_mode": op_mode,
        "max_daily_applications": max_daily,
        "applications_today": apps_today,
        # Direct unified structure for UI & test verification
        "jobs": {
            "total_live_jobs": total_jobs,
            "jobs_by_portal": jobs_by_portal,
            "jobs_by_domain": jobs_by_domain,
            "jobs_by_title": jobs_by_title
        },
        "applications": {
            "total_applications": total_apps,
            "resumes_synthesized": total_apps,
            "submitted": apps_submitted,
            "applications_viewed": apps_viewed,
            "no_response_applications": apps_no_response
        },
        "outreach": {
            "contacts_count": contacts_count,
            "recruiter_replies": emails_replied,
            "positive_response_rate": round((positive_replies / max(1, emails_replied)) * 100) if emails_replied > 0 else 0
        },
        "limits": {
            "operating_mode": op_mode,
            "applications_today": apps_today,
            "max_daily_applications": max_daily,
            "max_portal_applications": max_portal,
            "remaining_today": max(0, max_daily - apps_today)
        },
        "portals": portals_dict,
        "sentiment_breakdown": email_categories,
        "learning_insights": learning_insights,
        "job_statistics": {
            "total_discovered": total_jobs,
            "relevant_jobs": total_jobs,
            "total_applied": total_apps,
            "applied_today": apps_today,
            "applied_this_week": apps_this_week,
            "applied_this_month": apps_this_month,
            "by_portal": jobs_by_portal,
            "by_domain": jobs_by_domain,
            "by_title": jobs_by_title,
            "top_companies": [{"company": c[0], "count": c[1]} for c in top_companies]
        },
        "application_statistics": {
            "total_applications": total_apps,
            "submitted": apps_submitted,
            "in_progress": apps_in_progress,
            "interviewing": apps_interviewing,
            "offers": apps_offers,
            "rejections": apps_rejections,
            "applications_viewed": apps_viewed,
            "no_response_applications": apps_no_response
        },
        "outreach_statistics": {
            "contacts_discovered": contacts_count,
            "emails_sent": total_emails_sent,
            "replies_received": emails_replied,
            "positive_responses": positive_replies,
            "negative_responses": negative_replies,
            "followups_sent": followups_sent,
            "pending_followups": pending_followups,
            "category_breakdown": email_categories
        },
        "recent_timeline": [
            {
                "id": t.id,
                "stage_number": t.stage_number,
                "event_type": t.event_type,
                "title": t.title,
                "company": t.company,
                "timestamp": t.timestamp.isoformat() if t.timestamp else ""
            }
            for t in recent_timeline
        ]
    }


