import logging
from typing import List, Optional
from src.scrapers.base import BaseScraper
from src.models.job import JobPosting
from src.config import settings

logger = logging.getLogger(__name__)

class ArbeitnowScraper(BaseScraper):
    """Scraper for Arbeitnow Jobs API."""

    def __init__(self):
        super().__init__(name="Arbeitnow", base_url="https://www.arbeitnow.com/api/job-board-api")

    def fetch_jobs(self, query: Optional[str] = None, limit: int = 40) -> List[JobPosting]:
        jobs: List[JobPosting] = []
        try:
            response = self.get_with_retry(self.base_url)
            if not response or response.status_code != 200:
                self.log("Arbeitnow API unavailable", level="warning")
                return []

            data = response.json()
            items = data.get("data", [])

            for item in items[:limit]:
                title = item.get("title", "").strip()
                company = item.get("company_name", "").strip()
                apply_url = item.get("url") or f"https://www.arbeitnow.com/view/{item.get('slug', '')}"
                if not title or not company or not self.is_valid_url(apply_url):
                    continue

                # Filter by query if supplied
                raw_desc = item.get("description", "")
                cleaned_desc = self.clean_html(raw_desc)
                is_remote = bool(item.get("remote", True))
                location = item.get("location") or ("Remote / Europe" if is_remote else "Germany / Europe")
                combined_text = f"{title} {company} {location} {cleaned_desc}".lower()

                if query and query.lower() not in combined_text:
                    continue

                tags = item.get("tags", [])
                skills = self.extract_skills(combined_text, existing_skills=tags)
                level, is_fresher = self.detect_fresher_and_level(title, cleaned_desc)
                geo = self.detect_region(location, cleaned_desc)
                role_domain = self.detect_role_domain(title, cleaned_desc)

                job = JobPosting(
                    source="arbeitnow",
                    source_name="Arbeitnow",
                    source_job_id=str(item.get("slug") or ""),
                    title=title,
                    company=company,
                    location=location,
                    city=geo.get("city"),
                    country=geo.get("country", "Europe"),
                    region=geo.get("region", "Europe"),
                    role_domain=role_domain,
                    remote=is_remote,
                    remote_type="Remote" if is_remote else "Onsite",
                    employment_type="Full-time",
                    salary_min=None,
                    salary_max=None,
                    salary_currency="EUR",
                    description=cleaned_desc[:3000],
                    skills=skills,
                    experience_level=level,
                    apply_url=apply_url,
                    source_url=apply_url,
                    published_at=str(item.get("created_at")),
                    status="ACTIVE",
                    verification_status="VERIFIED",
                    is_fresher=is_fresher
                )

                valid, reason = self.validate_job(job)
                if valid:
                    jobs.append(job)
                else:
                    self.log(f"Rejected job: {reason}", level="warning")

        except Exception as e:
            self.log(f"Error fetching jobs from Arbeitnow: {e}", level="error")

        return jobs

