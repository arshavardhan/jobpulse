import re
import time
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError, HTTPError

from src.models.job import JobPosting, normalize_url, compute_hash
from src.config import settings

logger = logging.getLogger(__name__)

# Comprehensive multi-role skill dictionary covering all major career domains
COMMON_TECH_SKILLS = [
    # Engineering & DevOps
    "python", "java", "javascript", "typescript", "c++", "c#", "golang", "rust", "ruby", "php", "scala",
    "pytorch", "tensorflow", "scikit-learn", "keras", "pandas", "numpy",
    "sql", "postgresql", "mongodb", "redis", "mysql", "cassandra",
    "fastapi", "flask", "django", "spring", "express", "node.js", "next.js", "react", "vue", "angular",
    "docker", "kubernetes", "aws", "gcp", "azure", "git", "ci/cd", "linux", "terraform",
    "langchain", "langgraph", "llm", "rag", "transformers", "huggingface", "openai",
    "microservices", "rest api", "graphql", "system design", "grpc",
    
    # Data Science, AI & Analytics
    "data science", "data analytics", "machine learning", "deep learning", "nlp", "computer vision",
    "tableau", "power bi", "spark", "kafka", "snowflake", "airflow", "dbt", "data engineering",
    "agentic ai", "vector database", "qdrant", "chroma", "pinecone", "statistics", "bigquery",
    
    # Product Management
    "product management", "roadmapping", "user stories", "prd", "jira", "agile", "scrum",
    "feature prioritization", "a/b testing", "okrs", "user research", "market research",
    
    # UI/UX & Product Design
    "figma", "ui/ux", "wireframing", "prototyping", "design systems", "sketch", "adobe xd",
    "user journey", "interaction design", "visual design", "user testing", "responsive design",
    
    # Marketing & Growth
    "seo", "sem", "content marketing", "copywriting", "google analytics", "digital marketing",
    "social media marketing", "email marketing", "growth hacking", "hubspot", "meta ads", "google ads",
    
    # Sales & Business Development
    "sales", "business development", "lead generation", "crm", "salesforce", "cold outreach",
    "account management", "b2b", "prospecting", "pipeline management", "negotiation",
    
    # Operations, HR & Talent Acquisition
    "talent acquisition", "recruitment", "onboarding", "hris", "payroll", "people operations",
    "employee relations", "performance management", "sourcing", "compliance",
    
    # Finance & Accounting
    "financial modeling", "accounting", "bookkeeping", "budgeting", "quickbooks", "auditing",
    "financial analysis", "forecasting", "taxation", "excel", "financial reporting",
    
    # Customer Support & Success
    "customer support", "customer success", "zendesk", "intercom", "freshdesk", "ticket resolution",
    "client onboarding", "troubleshooting", "crm support", "retention",
    
    # QA & Quality Assurance
    "qa", "quality assurance", "selenium", "playwright", "cypress", "manual testing",
    "automation testing", "test automation", "sdet", "unit testing", "integration testing"
]

# Major Indian cities for geographic tagging
INDIAN_CITIES = [
    "bengaluru", "bangalore", "hyderabad", "gurgaon", "gurugram", "pune", "mumbai",
    "delhi", "new delhi", "noida", "chennai", "kolkata", "ahmedabad", "surat",
    "jaipur", "kochi", "coimbatore", "indore", "chandigarh", "thiruvananthapuram",
    "bhopal", "nagpur", "lucknow", "visakhapatnam", "vadodara", "mysore", "mysuru"
]

INDIAN_STATES = [
    "karnataka", "telangana", "maharashtra", "tamil nadu", "delhi", "haryana",
    "uttar pradesh", "kerala", "gujarat", "west bengal", "rajasthan", "punjab",
    "andhra pradesh", "madhya pradesh"
]

class BaseScraper(ABC):
    """Abstract base class for robust, production-grade job scrapers with full lifecycle."""

    def __init__(self, name: str, base_url: str):
        self.name = name
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": settings.DEFAULT_USER_AGENT,
            "Accept": "text/html,application/json,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })

    def log(self, message: str, level: str = "info"):
        prefix = f"[{self.name}] "
        if level == "warning":
            logger.warning(prefix + message)
        elif level == "error":
            logger.error(prefix + message)
        else:
            logger.info(prefix + message)

    def get_with_retry(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
        max_retries: int = 3,
        backoff_factor: float = 1.0
    ) -> Optional[requests.Response]:
        """Execute GET request with exponential backoff and rate-limit handling."""
        timeout_val = timeout or settings.SCRAPER_TIMEOUT
        current_headers = headers or {}

        for attempt in range(1, max_retries + 1):
            try:
                response = self.session.get(url, params=params, headers=current_headers, timeout=timeout_val)
                
                # Handle rate limiting (429)
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    sleep_time = int(retry_after) if (retry_after and retry_after.isdigit()) else (backoff_factor * (2 ** (attempt - 1)))
                    self.log(f"Rate limited (429). Backing off for {sleep_time}s (attempt {attempt}/{max_retries}).", level="warning")
                    time.sleep(min(sleep_time, 10))
                    continue

                if response.status_code >= 500:
                    self.log(f"Server error {response.status_code}. Retrying in {backoff_factor * attempt}s...", level="warning")
                    time.sleep(backoff_factor * attempt)
                    continue

                return response

            except (Timeout, ConnectionError) as e:
                self.log(f"Network error on attempt {attempt}/{max_retries}: {e}", level="warning")
                if attempt < max_retries:
                    time.sleep(backoff_factor * (2 ** (attempt - 1)))
                else:
                    self.log(f"Failed all {max_retries} attempts for {url}", level="error")
                    return None
            except RequestException as e:
                self.log(f"Request exception: {e}", level="error")
                return None

        return None

    def clean_html(self, html_content: str) -> str:
        """Strip HTML tags and normalize whitespace."""
        if not html_content:
            return ""
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            text = soup.get_text(separator=" ")
            return re.sub(r"\s+", " ", text).strip()
        except Exception:
            # Fallback simple regex
            return re.sub(r"\s+", " ", re.sub(r"<[^<]+?>", " ", html_content)).strip()

    def is_valid_url(self, url: str) -> bool:
        """Validate that the apply URL uses HTTP/HTTPS and has a valid domain."""
        if not url or not isinstance(url, str):
            return False
        url_strip = url.strip()
        if not (url_strip.startswith("http://") or url_strip.startswith("https://")):
            return False
        try:
            parsed = urlparse(url_strip)
            netloc = parsed.netloc.lower()
            if not netloc or "." not in netloc:
                return False
            # Reject dummy or localhost URLs
            if "localhost" in netloc or "127.0.0.1" in netloc or "example.com" in netloc:
                return False
            return True
        except Exception:
            return False

    def extract_skills(self, text: str, existing_skills: Optional[List[str]] = None) -> List[str]:
        """Extract matched tech skills with word boundaries and no fabrication."""
        found = set()
        if existing_skills:
            for s in existing_skills:
                if isinstance(s, str) and s.strip():
                    found.add(s.strip().lower())

        lowered = text.lower()
        for skill in COMMON_TECH_SKILLS:
            pattern = r"\b" + re.escape(skill) + r"\b"
            if re.search(pattern, lowered):
                found.add(skill)

        return sorted(list(found))

    def detect_region(self, location: str, description: str = "") -> Dict[str, Any]:
        """
        Geographic classification distinguishing Indian cities, North America, Europe,
        while maintaining independent remote flags.
        """
        combined = f"{location or ''} {description[:400] or ''}".lower()
        loc_lowered = (location or "").lower()

        # Check for remote signals (independent from geography)
        remote_signals = ["remote", "work from home", "wfh", "anywhere", "telecommute", "distributed"]
        is_remote = any(sig in loc_lowered for sig in remote_signals) or any(sig in combined[:200] for sig in remote_signals)
        remote_type = "Remote" if is_remote else ("Hybrid" if "hybrid" in loc_lowered else "Onsite")

        # Indian geography check
        detected_city = None
        for city in INDIAN_CITIES:
            if re.search(r"\b" + re.escape(city) + r"\b", loc_lowered) or re.search(r"\b" + re.escape(city) + r"\b", combined):
                detected_city = city.capitalize()
                if city == "bangalore":
                    detected_city = "Bengaluru"
                elif city == "gurugram":
                    detected_city = "Gurgaon"
                break

        is_india = (
            detected_city is not None or
            re.search(r"\bindia\b", loc_lowered) or
            re.search(r"\bindia\b", combined) or
            any(re.search(r"\b" + re.escape(st) + r"\b", loc_lowered) for st in INDIAN_STATES)
        )

        if is_india:
            return {
                "country": "India",
                "city": detected_city,
                "region": "India",
                "remote": is_remote,
                "remote_type": remote_type
            }

        # North America check
        na_signals = ["united states", "usa", "us remote", "u.s.", "san francisco", "new york", "seattle", "canada", "toronto"]
        if any(re.search(r"\b" + re.escape(s) + r"\b", loc_lowered) for s in na_signals):
            return {
                "country": "United States" if "canada" not in loc_lowered else "Canada",
                "city": None,
                "region": "North America",
                "remote": is_remote,
                "remote_type": remote_type
            }

        # Europe check
        eu_signals = ["united kingdom", "uk", "germany", "berlin", "london", "france", "paris", "netherlands", "amsterdam", "spain", "europe"]
        if any(re.search(r"\b" + re.escape(s) + r"\b", loc_lowered) for s in eu_signals):
            return {
                "country": "Europe",
                "city": None,
                "region": "Europe",
                "remote": is_remote,
                "remote_type": remote_type
            }

        return {
            "country": "Worldwide" if is_remote else "Global",
            "city": None,
            "region": "Global",
            "remote": is_remote or True,
            "remote_type": remote_type
        }

    def detect_experience_level(self, title: str, description: str = "") -> str:
        """Heuristic to detect experience level with high sensitivity for freshers/entry-level."""
        level, _ = self.detect_fresher_and_level(title, description)
        return level

    def detect_fresher_and_level(
        self,
        title: str,
        description: str = "",
        requirements: Optional[str] = "",
        employment_type: Optional[str] = ""
    ) -> Tuple[str, bool]:
        """
        High-precision fresher / entry-level detection with protection against false positives.
        Example: 'Senior Engineer mentoring freshers' -> Senior (NOT fresher).
        """
        title_lower = str(title or "").lower()
        desc_lower = str(description or "")[:800].lower()
        if isinstance(requirements, list):
            req_lower = " ".join(str(r) for r in requirements).lower()
        else:
            req_lower = str(requirements or "").lower()

        if isinstance(employment_type, list):
            emp_lower = " ".join(str(e) for e in employment_type).lower()
        else:
            emp_lower = str(employment_type or "").lower()

        # 1. Negative Signals (Seniority in Title or Lead requirements take strict precedence)
        senior_title_indicators = [
            "senior", "sr.", "sr ", "lead", "principal", "staff", "architect",
            "director", "head of", "vp", "vice president", "manager", "team lead"
        ]
        if any(ind in title_lower for ind in senior_title_indicators):
            if any(l in title_lower for l in ["lead", "principal", "staff", "architect", "director", "head of", "vp"]):
                return "Lead", False
            return "Senior", False

        # Check high years of experience in requirements
        high_exp = ["5+ years", "5+ yrs", "6+ years", "7+ years", "8+ years", "10+ years"]
        if any(h in req_lower or h in desc_lower[:300] for h in high_exp):
            return "Senior", False

        # 2. Positive Fresher / Entry Signals
        fresher_keywords = [
            "intern", "internship", "fresher", "graduate trainee", "campus",
            "new grad", "entry level", "entry-level", "junior", "jr.", "jr ",
            "associate engineer", "trainee", "0-1 year", "0-2 year", "0-1 yr",
            "0-2 yr", "0 years", "no experience required", "early career"
        ]

        if any(k in title_lower for k in fresher_keywords) or any(k in emp_lower for k in ["intern", "internship", "trainee"]):
            return "Fresher / Entry", True

        if any(k in desc_lower[:350] for k in fresher_keywords):
            return "Fresher / Entry", True

        # Check Mid-Level vs Senior default
        if "3+ years" in desc_lower or "4+ years" in desc_lower or "mid-level" in desc_lower:
            return "Mid-Level", False

        return "Mid-Level", False

    def is_fresher_friendly(self, title: str, description: str = "") -> bool:
        """Convenience method checking if role is fresher-friendly."""
        _, is_fresher = self.detect_fresher_and_level(title, description)
        return is_fresher

    def detect_role_domain(self, title: str, description: str = "") -> str:
        """Classify job into one of the 10 core career role domains."""
        t = (title or "").lower()
        d = (description or "")[:500].lower()
        
        # QA / Testing
        if any(k in t for k in ["quality assurance", "test engineer", "automation test", "tester", "testing"]) or re.search(r"\b(qa|sdet)\b", t):
            return "QA"
        
        # Data & AI
        if any(k in t for k in ["data scientist", "machine learning", "ml engineer", "ai engineer", "data engineer", "data analyst", "bi analyst", "deep learning", "nlp", "computer vision", "analytics engineer", "artificial intelligence"]):
            return "Data & AI"
            
        # Product Management
        if any(k in t for k in ["product manager", "product management", "technical product", "associate product", "group product", "head of product", "director of product", "vp of product", "product lead", "product owner", "scrum master", "program manager"]) or re.search(r"\b(pm|tpm|apm)\b", t):
            return "Product"
            
        # UI/UX & Product Design
        if any(k in t for k in ["design", "ui/ux", "ux/ui", "product design", "graphic design", "visual design", "interaction design", "user experience", "brand designer", "ux designer", "ui designer"]):
            return "Design"
            
        # Marketing & Growth
        if any(k in t for k in ["marketing", "growth", "seo", "sem", "content writer", "copywriter", "social media", "brand marketing", "demand gen", "digital marketing", "communications"]):
            return "Marketing"
            
        # Sales & BD
        if any(k in t for k in ["sales", "account executive", "business development", "account manager", "partnership", "sales development", "client relationship"]) or re.search(r"\b(bdr|sdr)\b", t):
            return "Sales"
            
        # Customer Support & Success
        if any(k in t for k in ["customer support", "customer success", "client success", "technical support", "support specialist", "customer care", "help desk", "support engineer", "service representative"]):
            return "Customer Support"
            
        # Finance & Accounting
        if any(k in t for k in ["finance", "financial", "accounting", "accountant", "controller", "bookkeeper", "tax", "audit", "treasury", "billing"]):
            return "Finance"
            
        # Operations & HR / Talent
        if any(k in t for k in ["human resources", "people operations", "people ops", "talent acquisition", "recruiter", "recruiting", "hr generalist", "hr manager", "operations manager", "office manager", "chief of staff"]):
            return "Operations & HR"
            
        # Default to Engineering for software/dev or general technical positions
        return "Engineering"

    def validate_job(self, job: JobPosting) -> Tuple[bool, str]:
        """Ensure job has minimum genuine fields and a valid application URL."""
        if not job.title or len(job.title.strip()) < 2:
            return False, "Missing or empty job title"
        if not job.company or len(job.company.strip()) < 2:
            return False, "Missing or empty company name"
        apply_url = job.apply_url or job.url
        if not self.is_valid_url(apply_url):
            return False, f"Invalid or non-HTTP application URL: {apply_url}"
        return True, "Valid"

    @abstractmethod
    def fetch_jobs(self, query: Optional[str] = None, limit: int = 20) -> List[JobPosting]:
        """Subclasses must implement this to return normalized, validated JobPosting objects."""
        pass

