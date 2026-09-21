import json
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Boolean, Text, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

def utc_now():
    return datetime.now(timezone.utc)

class JobModel(Base):
    __tablename__ = "jobs"

    id = Column(String(64), primary_key=True, index=True)
    source = Column(String(100), default="web", index=True)
    source_name = Column(String(100), default="Web")
    source_job_id = Column(String(128), nullable=True, index=True)

    title = Column(String(255), nullable=False, index=True)
    company = Column(String(255), nullable=False, index=True)
    description = Column(Text, default="", nullable=False)

    location = Column(String(255), default="Remote")
    city = Column(String(100), nullable=True, index=True)
    country = Column(String(100), nullable=True, index=True)
    region = Column(String(50), default="India", index=True)
    role_domain = Column(String(100), default="Engineering", index=True)

    remote = Column(Boolean, default=True, index=True)
    remote_type = Column(String(50), default="Remote")
    employment_type = Column(String(100), nullable=True)
    experience_level = Column(String(50), default="Mid-Level")

    salary_min = Column(Float, nullable=True)
    salary_max = Column(Float, nullable=True)
    salary_currency = Column(String(10), default="USD")

    skills_json = Column(Text, default="[]")  # Serialized list
    apply_url = Column(String(1024), nullable=False)
    source_url = Column(String(1024), nullable=True)

    published_at = Column(String(100), nullable=True)
    first_seen_at = Column(DateTime, default=utc_now)
    last_seen_at = Column(DateTime, default=utc_now, index=True)
    last_verified_at = Column(DateTime, nullable=True)

    status = Column(String(50), default="ACTIVE", index=True)  # ACTIVE, STALE, EXPIRED, REMOVED, UNKNOWN
    verification_status = Column(String(50), default="UNVERIFIED")  # VERIFIED, UNVERIFIED, UNREACHABLE, EXPIRED

    is_fresher = Column(Boolean, default=False, index=True)
    content_hash = Column(String(64), nullable=True, index=True)
    url_hash = Column(String(64), nullable=True, index=True)

    # Provenance & Multi-Source Tracking
    canonical_source = Column(String(100), nullable=True, index=True)
    discovered_via = Column(String(100), nullable=True)
    sources_json = Column(Text, default="[]")  # Serialized list of all sources reporting this opening

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    applications = relationship("ApplicationModel", back_populates="job", cascade="all, delete-orphan")
    saved_by_users = relationship("SavedJobModel", back_populates="job", cascade="all, delete-orphan")

    @property
    def is_remote(self):
        return self.remote

    @is_remote.setter
    def is_remote(self, value):
        self.remote = bool(value)

    @property
    def url(self):
        return self.apply_url

    @url.setter
    def url(self, value):
        self.apply_url = value or ""

    @property
    def currency(self):
        return self.salary_currency

    @currency.setter
    def currency(self, value):
        self.salary_currency = value or "USD"

    @property
    def posted_date(self):
        return self.published_at

    @posted_date.setter
    def posted_date(self, value):
        self.published_at = value

    @property
    def skills_required(self):
        try:
            return json.loads(self.skills_json) if self.skills_json else []
        except Exception:
            return []

    @skills_required.setter
    def skills_required(self, value):
        self.skills_json = json.dumps(value if isinstance(value, list) else [])

    @property
    def skills(self):
        return self.skills_required

    @skills.setter
    def skills(self, value):
        self.skills_required = value

    @property
    def sources(self):
        try:
            return json.loads(self.sources_json) if self.sources_json else []
        except Exception:
            return []

    @sources.setter
    def sources(self, value):
        self.sources_json = json.dumps(value if isinstance(value, list) else [])


class SourceHealthModel(Base):
    __tablename__ = "source_health"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(100), index=True)
    source_name = Column(String(100))
    started_at = Column(DateTime, default=utc_now)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(50), default="SUCCESS")  # SUCCESS, PARTIAL, FAILED, TIMEOUT
    jobs_found = Column(Integer, default=0)
    jobs_accepted = Column(Integer, default=0)
    jobs_updated = Column(Integer, default=0)
    jobs_rejected = Column(Integer, default=0)
    jobs_duplicates = Column(Integer, default=0)
    errors = Column(Text, default="")
    latency_ms = Column(Integer, default=0)


class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)

    # Career Preferences & Profile
    preferred_role = Column(String(255), nullable=True)
    experience_level = Column(String(100), default="Mid-Level")
    preferred_location = Column(String(255), default="Remote")
    remote_preference = Column(String(100), default="Remote / Hybrid")
    years_of_experience = Column(Float, default=2.0)
    skills_json = Column(Text, default="[]")
    summary = Column(Text, default="")
    resume_text = Column(Text, default="")

    # Autonomous Agent Preferences
    target_job_titles_json = Column(Text, default='["Software Engineer", "Python Developer", "AI/ML Engineer"]')
    preferred_locations_json = Column(Text, default='["Remote", "India", "Bengaluru"]')
    min_salary = Column(Float, default=500000.0)
    salary_currency = Column(String(10), default="INR")
    work_preference = Column(String(50), default="Remote / Hybrid")
    operating_mode = Column(String(50), default="FULLY_AUTONOMOUS")  # FULLY_AUTONOMOUS, APPROVAL_MODE, ASSISTED
    max_daily_applications = Column(Integer, default=20)
    max_portal_applications = Column(Integer, default=5)
    master_resume_json = Column(Text, default="{}")

    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    saved_jobs = relationship("SavedJobModel", back_populates="user", cascade="all, delete-orphan")
    applications = relationship("ApplicationModel", back_populates="user", cascade="all, delete-orphan")

    @property
    def skills(self):
        try:
            return json.loads(self.skills_json) if self.skills_json else []
        except Exception:
            return []

    @skills.setter
    def skills(self, value):
        self.skills_json = json.dumps(value if isinstance(value, list) else [])

    @property
    def target_job_titles(self):
        try:
            return json.loads(self.target_job_titles_json) if self.target_job_titles_json else ["Software Engineer"]
        except Exception:
            return ["Software Engineer"]

    @target_job_titles.setter
    def target_job_titles(self, value):
        self.target_job_titles_json = json.dumps(value if isinstance(value, list) else ["Software Engineer"])

    @property
    def preferred_locations(self):
        try:
            return json.loads(self.preferred_locations_json) if self.preferred_locations_json else ["Remote"]
        except Exception:
            return ["Remote"]

    @preferred_locations.setter
    def preferred_locations(self, value):
        self.preferred_locations_json = json.dumps(value if isinstance(value, list) else ["Remote"])


class SavedJobModel(Base):
    __tablename__ = "saved_jobs"
    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_user_job_saved"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(String(64), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    saved_at = Column(DateTime, default=utc_now)

    user = relationship("UserModel", back_populates="saved_jobs")
    job = relationship("JobModel", back_populates="saved_by_users")


class ApplicationModel(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(64), ForeignKey("jobs.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    status = Column(String(50), default="SHORTLISTED", index=True)
    portal = Column(String(100), default="Direct ATS", index=True)
    notes = Column(Text, default="")
    tailored_cover_letter = Column(Text, default="")
    resume_version_id = Column(Integer, nullable=True)
    latex_resume_code = Column(Text, default="")
    overleaf_url = Column(String(1024), nullable=True)
    questions_answered_json = Column(Text, default="{}")
    application_result = Column(String(100), default="PENDING")
    interview_date = Column(String(100), nullable=True)
    match_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    job = relationship("JobModel", back_populates="applications")
    user = relationship("UserModel", back_populates="applications")


class ProfileModel(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True)
    data_json = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    @property
    def data(self):
        try:
            return json.loads(self.data_json)
        except Exception:
            return {}

    @data.setter
    def data(self, val):
        self.data_json = json.dumps(val)


class CompanySourceModel(Base):
    __tablename__ = "company_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_name = Column(String(255), unique=True, nullable=False, index=True)
    website = Column(String(512), nullable=False)
    careers_url = Column(String(1024), nullable=True)
    detected_ats = Column(String(100), default="unknown")  # lever, greenhouse, ashby, workable, etc.
    country = Column(String(100), default="India")
    priority = Column(Integer, default=1)
    enabled = Column(Boolean, default=True, index=True)
    last_checked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now)


class ContactMessageModel(Base):
    __tablename__ = "contact_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    subject = Column(String(255), nullable=False)
    category = Column(String(100), default="General")
    message = Column(Text, nullable=False)
    status = Column(String(50), default="RECEIVED")
    created_at = Column(DateTime, default=utc_now)


class JobReportModel(Base):
    __tablename__ = "job_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(64), nullable=False, index=True)
    reason = Column(String(100), nullable=False)  # Expired, Broken link, Incorrect info, Duplicate, Other
    details = Column(Text, default="")
    reporter_email = Column(String(255), nullable=True)
    status = Column(String(50), default="PENDING")
    created_at = Column(DateTime, default=utc_now)


# =============================================================================
# AUTONOMOUS AGENT MODELS: PERMISSIONS, LATEX, OUTREACH, LEARNING, TIMELINE
# =============================================================================

class PortalPermissionModel(Base):
    __tablename__ = "portal_permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    portal_name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(100), nullable=False)
    enabled = Column(Boolean, default=True, index=True)
    max_daily_apps = Column(Integer, default=5)
    requires_auth = Column(Boolean, default=False)
    auth_status = Column(String(50), default="CONFIGURED")  # CONFIGURED, AUTHORIZATION_REQUIRED, UNCONFIGURED
    apply_mode = Column(String(50), default="PORTAL_COPILOT")  # DIRECT_API, PORTAL_COPILOT, PUBLIC_BOARD
    category = Column(String(50), default="Aggregator")  # Aggregator, Direct ATS, Specialized, Campus
    description = Column(Text, default="")
    created_at = Column(DateTime, default=utc_now)


class ResumeVersionModel(Base):
    __tablename__ = "resume_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(64), nullable=True, index=True)
    application_id = Column(Integer, nullable=True, index=True)
    version_label = Column(String(100), default="ATS-Optimized LaTeX Resume")
    latex_source = Column(Text, nullable=False)
    template_name = Column(String(100), default="Modern ATS LaTeX")
    emphasized_skills_json = Column(Text, default="[]")
    overleaf_url = Column(String(1024), nullable=True)
    created_at = Column(DateTime, default=utc_now)

    @property
    def emphasized_skills(self):
        try:
            return json.loads(self.emphasized_skills_json) if self.emphasized_skills_json else []
        except Exception:
            return []


class RecruiterContactModel(Base):
    __tablename__ = "recruiter_contacts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company = Column(String(255), nullable=False, index=True)
    person_name = Column(String(255), nullable=False)
    role_title = Column(String(255), default="Technical Recruiter / Talent Acquisition")
    email = Column(String(255), nullable=False, index=True)
    linkedin_url = Column(String(512), nullable=True)
    confidence_score = Column(Float, default=0.88)
    source = Column(String(100), default="Public Talent Intelligence")
    verified = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)


class OutreachEmailModel(Base):
    __tablename__ = "outreach_emails"

    id = Column(Integer, primary_key=True, autoincrement=True)
    contact_id = Column(Integer, ForeignKey("recruiter_contacts.id", ondelete="SET NULL"), nullable=True)
    job_id = Column(String(64), nullable=True, index=True)
    application_id = Column(Integer, nullable=True, index=True)
    user_id = Column(Integer, nullable=True)
    recipient_email = Column(String(255), nullable=False, index=True)
    recipient_name = Column(String(255), default="Hiring Team")
    company = Column(String(255), default="Target Company")
    subject = Column(String(255), nullable=False)
    body_text = Column(Text, nullable=False)
    personalized_intro = Column(Text, default="")
    status = Column(String(50), default="DRAFT", index=True)  # DRAFT, PENDING_APPROVAL, SENT, DELIVERED, BOUNCED
    sent_at = Column(DateTime, nullable=True)
    reply_status = Column(String(50), default="NO_REPLY", index=True)  # NO_REPLY, REPLIED
    reply_text = Column(Text, default="")
    reply_category = Column(String(50), nullable=True, index=True)  # POSITIVE, NEGATIVE, NEUTRAL, INTERVIEW_OPPORTUNITY, REJECTION, FOLLOW_UP_REQUIRED, ACTION_REQUIRED
    follow_up_count = Column(Integer, default=0)
    next_follow_up_date = Column(String(50), nullable=True)
    thread_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=utc_now)


class KnowledgeBaseModel(Base):
    __tablename__ = "candidate_knowledge_base"

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(100), default="General")  # General, Experience, Compensation, Legal, Availability
    question_pattern = Column(String(255), nullable=False, index=True)
    verified_answer = Column(Text, nullable=False)
    is_sensitive = Column(Boolean, default=False)
    verified_by_user = Column(Boolean, default=True)
    use_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=utc_now)


class PendingQuestionModel(Base):
    __tablename__ = "pending_questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(64), nullable=True, index=True)
    company = Column(String(255), default="")
    question = Column(Text, nullable=False)
    suggested_answer = Column(Text, default="")
    status = Column(String(50), default="AWAITING_CONFIRMATION", index=True)  # AWAITING_CONFIRMATION, CONFIRMED, SKIPPED
    user_confirmed_answer = Column(Text, default="")
    created_at = Column(DateTime, default=utc_now)


class ActivityTimelineModel(Base):
    __tablename__ = "activity_timeline"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stage_number = Column(Integer, default=1, index=True)  # 1 to 9
    event_type = Column(String(100), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    job_id = Column(String(64), nullable=True, index=True)
    company = Column(String(255), default="")
    details_json = Column(Text, default="{}")
    timestamp = Column(DateTime, default=utc_now, index=True)

    @property
    def details(self):
        try:
            return json.loads(self.details_json) if self.details_json else {}
        except Exception:
            return {}

    @details.setter
    def details(self, val):
        self.details_json = json.dumps(val if isinstance(val, dict) else {})


class LearningMetricModel(Base):
    __tablename__ = "learning_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    metric_type = Column(String(100), nullable=False, index=True)  # SUBJECT_LINE, RESUME_TEMPLATE, COVER_LETTER_STYLE, KEYWORD_PERFORMANCE, ROLE_DOMAIN_FIT
    variant_key = Column(String(255), nullable=False, index=True)
    impressions = Column(Integer, default=0)
    positive_outcomes = Column(Integer, default=0)
    conversion_rate = Column(Float, default=0.0)
    recommended_weight = Column(Float, default=1.0)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
