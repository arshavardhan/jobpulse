from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator
from datetime import datetime, timezone
import hashlib
import re
import uuid
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse

def normalize_url(url: str) -> str:
    """Normalize URL by stripping tracking parameters, lowercase domain/scheme, and trailing slashes."""
    if not url:
        return ""
    try:
        parsed = urlparse(url.strip())
        scheme = parsed.scheme.lower() or "https"
        netloc = parsed.netloc.lower()
        path = parsed.path.rstrip("/")
        # Filter tracking query params
        tracking_keys = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "ref", "source", "fbclid", "gclid"}
        query_pairs = [(k, v) for k, v in parse_qsl(parsed.query) if k.lower() not in tracking_keys]
        query = urlencode(sorted(query_pairs))
        return urlunparse((scheme, netloc, path, "", query, ""))
    except Exception:
        return url.strip().rstrip("/")

def compute_hash(val: str) -> str:
    return hashlib.sha256(val.encode("utf-8")).hexdigest()

class JobPosting(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: str = "web"
    source_name: str = "Live Web"
    source_job_id: Optional[str] = None

    title: str
    company: str
    description: str = ""

    location: str = "Remote"
    city: Optional[str] = None
    country: Optional[str] = None
    region: str = "India"  # India, Global, North America, Europe
    role_domain: str = "Engineering"  # Engineering, Product, Design, Data & AI, Marketing, Sales, Operations & HR, Finance, Customer Support, QA

    remote: bool = True
    is_remote: bool = True  # backward compatibility
    remote_type: str = "Remote"  # Remote, Hybrid, Onsite

    employment_type: Optional[str] = "Full-time"
    experience_level: str = "Mid-Level"  # Fresher / Entry, Mid-Level, Senior, Lead

    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: str = "USD"
    currency: str = "USD"  # backward compatibility

    skills: List[str] = Field(default_factory=list)
    skills_required: List[str] = Field(default_factory=list)  # backward compatibility

    apply_url: str = ""
    source_url: Optional[str] = None
    url: str = ""  # backward compatibility

    published_at: Optional[str] = None
    posted_date: Optional[str] = None  # backward compatibility

    first_seen_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_seen_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_verified_at: Optional[str] = None

    status: str = "ACTIVE"  # ACTIVE, STALE, EXPIRED, REMOVED, UNKNOWN
    verification_status: str = "UNVERIFIED"  # VERIFIED, UNVERIFIED, UNREACHABLE, EXPIRED

    is_fresher: bool = False
    content_hash: str = ""
    url_hash: str = ""

    # Provenance & Multi-Source Tracking
    canonical_source: Optional[str] = None
    discovered_via: Optional[str] = None
    sources: List[str] = Field(default_factory=list)

    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @model_validator(mode="before")
    @classmethod
    def sync_aliases(cls, values: Any) -> Any:
        if not isinstance(values, dict):
            return values
        # Sync apply_url and url
        raw_url = values.get("apply_url") or values.get("url") or ""
        values["apply_url"] = raw_url
        values["url"] = raw_url

        # Sync remote and is_remote
        rem = values.get("remote", values.get("is_remote", True))
        values["remote"] = rem
        values["is_remote"] = rem

        # Sync skills and skills_required
        sk = values.get("skills", values.get("skills_required", []))
        values["skills"] = sk
        values["skills_required"] = sk

        # Sync currency and salary_currency
        curr = values.get("salary_currency", values.get("currency", "USD"))
        values["salary_currency"] = curr
        values["currency"] = curr

        # Sync published_at and posted_date
        pub = values.get("published_at") or values.get("posted_date")
        if pub is not None:
            if isinstance(pub, (int, float)):
                try:
                    pub = datetime.fromtimestamp(pub, tz=timezone.utc).isoformat()
                except Exception:
                    pub = str(pub)
            else:
                pub = str(pub)
        values["published_at"] = pub
        values["posted_date"] = pub

        return values

    def model_post_init(self, __context: Any) -> None:
        # Compute URL hash
        norm_url = normalize_url(self.apply_url or self.url)
        if not self.url_hash and norm_url:
            self.url_hash = compute_hash(norm_url)[:32]

        # Compute Content hash
        norm_title = re.sub(r"\s+", " ", self.title.strip().lower())
        norm_company = re.sub(r"\s+", " ", self.company.strip().lower())
        norm_desc_head = re.sub(r"\s+", " ", self.description[:300].strip().lower())
        if not self.content_hash:
            self.content_hash = compute_hash(f"{norm_title}|{norm_company}|{norm_desc_head}")[:32]

        # Deterministic primary ID
        if not self.id:
            if self.source and self.source_job_id:
                self.id = compute_hash(f"{self.source}:{self.source_job_id}")[:24]
            elif self.url_hash:
                self.id = self.url_hash[:24]
            else:
                self.id = compute_hash(f"{norm_title}@{norm_company}:{self.source}")[:24]


class UserProfile(BaseModel):
    full_name: str = "Candidate"
    email: Optional[str] = "candidate@example.com"
    phone: Optional[str] = None
    target_roles: List[str] = Field(default_factory=lambda: ["AI/ML Engineer", "Data Scientist", "Python Developer"])
    skills: List[str] = Field(default_factory=list)
    years_of_experience: float = 0.0  # Default to fresher/entry
    summary: str = ""
    experience_highlights: List[str] = Field(default_factory=list)
    education: List[str] = Field(default_factory=list)
    preferred_locations: List[str] = Field(default_factory=lambda: ["India", "Remote India", "Bengaluru", "Hyderabad", "Remote Global"])
    min_salary: Optional[float] = 500000.0  # INR or USD
    remote_only: bool = False

class MatchResult(BaseModel):
    job_id: str
    job_title: str
    company: str
    location: str
    city: Optional[str] = None
    country: Optional[str] = None
    region: str = "India"
    is_fresher: bool = False
    experience_level: str = "Mid-Level"
    url: str
    apply_url: Optional[str] = None
    source: str = "web"
    source_name: str = "Live Web"
    verification_status: str = "VERIFIED"
    salary_display: str = "Not Specified"
    match_score: float  # 0 to 100
    semantic_score: float  # 0 to 100
    keyword_score: float  # 0 to 100
    matching_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    rationale: str = ""
    suggested_pitch: str = ""


class JobFilter(BaseModel):
    query: Optional[str] = None
    skills: Optional[List[str]] = None
    location: Optional[str] = None
    region: Optional[str] = None  # 'india', 'global', or None
    fresher_only: bool = False
    remote_only: bool = False
    min_salary: Optional[float] = None
    sources: Optional[List[str]] = None
    limit: int = 50

class SubscriptionPlan(BaseModel):
    tier: str = "FREE"  # FREE, PRO, LIFETIME
    daily_limit: int = 5
    used_today: int = 0
    remaining_today: int = 5
    can_auto_apply: bool = False
    features: List[str] = Field(default_factory=lambda: [
        "5 Daily Job Applications",
        "AI ATS Scorecard & Skill Matcher",
        "Manual Copilot Autofill (Copy Answers)",
        "India & Global Job Access"
    ])
    pro_features: List[str] = Field(default_factory=lambda: [
        "⚡ 1-Click LazyApply Auto-Apply Bot",
        "Unlimited Daily Applications",
        "Exclusive Fresher & Campus Hiring Vault",
        "Direct Employer ATS & Enterprise Portals Auto-Fill",
        "Direct HR Referral Network Access"
    ])
