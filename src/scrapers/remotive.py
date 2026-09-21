import logging
from typing import List, Optional

from src.scrapers.base import BaseScraper
from src.models.job import JobPosting

logger = logging.getLogger(__name__)

class RemotiveScraper(BaseScraper):
    """Scraper for Remotive Remote Jobs API covering software engineering positions."""

    def __init__(self):
        super().__init__(name="Remotive", base_url="https://remotive.com/api/remote-jobs")

    def fetch_jobs(self, query: Optional[str] = None, limit: int = 50) -> List[JobPosting]:
        jobs: List[JobPosting] = []
        params = {"limit": limit}
        if query:
            params["search"] = query

        response = self.get_with_retry(self.base_url, params=params)
        if not response or response.status_code != 200:
            self.log("Failed to fetch jobs from Remotive API", level="warning")
            return []

        try:
            data = response.json()
            items = data.get("jobs", [])

            for item in items[:limit]:
                title = (item.get("title") or "").strip()
                company = (item.get("company_name") or "").strip()
                apply_url = (item.get("url") or "").strip()

                if not title or not company or not self.is_valid_url(apply_url):
                    continue

                raw_desc = item.get("description") or ""
                description = self.clean_html(raw_desc)
                candidate_location = item.get("candidate_required_location") or "Worldwide / Remote"
                tags = item.get("tags") or []
                salary_str = item.get("salary") or ""

                # Filter by query if provided
                combined = f"{title} {company} {candidate_location} {description} {' '.join(tags)}".lower()
                if query and query.lower() not in combined:
                    continue

                geo = self.detect_region(candidate_location, description)
                level, is_fresher = self.detect_fresher_and_level(
                    title=title,
                    description=description,
                    employment_type=item.get("job_type")
                )
                skills = self.extract_skills(combined, existing_skills=tags)
                role_domain = self.detect_role_domain(title=title, description=description)

                job = JobPosting(
                    source="remotive",
                    source_name="Remotive",
                    source_job_id=str(item.get("id")),
                    title=title,
                    company=company,
                    location=candidate_location,
                    city=geo.get("city"),
                    country=geo.get("country", "Worldwide"),
                    region=geo.get("region", "Global"),
                    role_domain=role_domain,
                    remote=True,
                    remote_type="Remote",
                    employment_type=item.get("job_type") or "Full-time",
                    experience_level=level,
                    salary_min=None,
                    salary_max=None,
                    salary_currency="USD",
                    skills=skills,
                    apply_url=apply_url,
                    source_url=apply_url,
                    published_at=item.get("publication_date"),
                    status="ACTIVE",
                    verification_status="VERIFIED",
                    is_fresher=is_fresher
                )

                valid, reason = self.validate_job(job)
                if valid:
                    jobs.append(job)
                else:
                    self.log(f"Rejected invalid job from Remotive: {reason}", level="warning")

        except Exception as e:
            self.log(f"Error parsing Remotive jobs response: {e}", level="error")

        return jobs
