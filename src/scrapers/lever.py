import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from src.scrapers.base import BaseScraper
from src.models.job import JobPosting

logger = logging.getLogger(__name__)

class BaseATSScraper(BaseScraper):
    """Base class for ATS integrations (Lever, Greenhouse, Ashby, Workable, etc.)."""

    def __init__(self, name: str, base_url: str, ats_type: str):
        super().__init__(name=name, base_url=base_url)
        self.ats_type = ats_type

class LeverCareerScraper(BaseATSScraper):
    """
    Reusable Lever ATS Career Scraper.
    Accepts any company slug (e.g. 'meesho', 'cred') and fetches directly from
    Lever's public JSON postings endpoint.
    """

    def __init__(self, company_slug: str, company_name: Optional[str] = None):
        self.company_slug = company_slug.strip().lower()
        self.display_name = company_name or self.company_slug.capitalize()
        endpoint = f"https://api.lever.co/v0/postings/{self.company_slug}?mode=json"
        super().__init__(
            name=f"Lever-{self.display_name}",
            base_url=endpoint,
            ats_type="lever"
        )

    def fetch_jobs(self, query: Optional[str] = None, limit: int = 30) -> List[JobPosting]:
        jobs: List[JobPosting] = []
        response = self.get_with_retry(self.base_url)
        if not response or response.status_code != 200:
            self.log(f"Lever endpoint unavailable for {self.company_slug}", level="warning")
            return []

        try:
            items = response.json()
            if not isinstance(items, list):
                self.log(f"Malformed response format from Lever for {self.company_slug}", level="warning")
                return []

            for item in items[:limit * 2]:
                title = (item.get("text") or "").strip()
                if not title:
                    continue

                categories = item.get("categories") or {}
                location = categories.get("location") or "Bengaluru, Karnataka, India"
                team = categories.get("team")
                department = categories.get("department")
                commitment = categories.get("commitment") or "Full Time Employee"

                # Direct Apply URL & Source URL
                apply_url = item.get("applyUrl") or f"https://jobs.lever.co/{self.company_slug}/{item.get('id')}/apply"
                source_url = item.get("hostedUrl") or f"https://jobs.lever.co/{self.company_slug}/{item.get('id')}"

                if not self.is_valid_url(apply_url):
                    continue

                raw_desc = item.get("descriptionPlain") or item.get("description") or ""
                description = self.clean_html(raw_desc)

                # Filter by keyword if provided
                combined = f"{title} {self.display_name} {location} {department or ''} {team or ''} {description}".lower()
                if query and query.lower() not in combined:
                    continue

                # Region, fresher, and skill extraction
                geo = self.detect_region(location, description)
                level, is_fresher = self.detect_fresher_and_level(
                    title=title,
                    description=description,
                    employment_type=commitment
                )
                skills = self.extract_skills(combined)
                role_domain = self.detect_role_domain(title, description)

                # Created at
                created_ts = item.get("createdAt")
                published_at = None
                if created_ts:
                    try:
                        published_at = datetime.fromtimestamp(created_ts / 1000, tz=timezone.utc).isoformat()
                    except Exception:
                        pass

                job = JobPosting(
                    source="lever",
                    source_name=f"{self.display_name} Careers (Lever)",
                    source_job_id=str(item.get("id")),
                    title=title,
                    company=self.display_name,
                    location=location,
                    city=geo.get("city"),
                    country=geo.get("country", "India"),
                    region=geo.get("region", "India"),
                    role_domain=role_domain,
                    remote=geo.get("remote", False),
                    remote_type=geo.get("remote_type", "Onsite"),
                    employment_type=commitment,
                    experience_level=level,
                    salary_min=None,
                    salary_max=None,
                    salary_currency="INR" if geo.get("region") == "India" else "USD",
                    skills=skills,
                    apply_url=apply_url,
                    source_url=source_url,
                    published_at=published_at,
                    status="ACTIVE",
                    verification_status="VERIFIED",
                    is_fresher=is_fresher
                )

                valid, reason = self.validate_job(job)
                if valid:
                    jobs.append(job)
                    if len(jobs) >= limit:
                        break
                else:
                    self.log(f"Rejected invalid job from Lever ({self.company_slug}): {reason}", level="warning")

        except Exception as e:
            self.log(f"Error parsing Lever response for {self.company_slug}: {e}", level="error")

        return jobs
