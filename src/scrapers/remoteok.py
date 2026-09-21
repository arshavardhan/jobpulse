import logging
from typing import List, Optional
from src.scrapers.base import BaseScraper
from src.models.job import JobPosting
from src.config import settings

logger = logging.getLogger(__name__)

class RemoteOKScraper(BaseScraper):
    """Scraper for RemoteOK jobs API with fallback scraping."""

    def __init__(self):
        super().__init__(name="RemoteOK", base_url="https://remoteok.com/api")

    def fetch_jobs(self, query: Optional[str] = None, limit: int = 40) -> List[JobPosting]:
        jobs: List[JobPosting] = []
        try:
            url = self.base_url
            if query:
                url = f"{self.base_url}?tag={query.lower().strip()}"
            
            response = self.get_with_retry(url)
            if not response or response.status_code != 200:
                self.log("RemoteOK API unavailable", level="warning")
                return []

            data = response.json()
            # RemoteOK's first item is usually a legal disclaimer metadata dict
            items = data[1:] if isinstance(data, list) and len(data) > 1 else []

            for item in items[:limit]:
                if not isinstance(item, dict):
                    continue
                
                title = item.get("position", "").strip()
                company = item.get("company", "").strip()
                apply_url = item.get("url") or f"https://remoteok.com/remote-jobs/{item.get('id', '')}"
                if not title or not company or not self.is_valid_url(apply_url):
                    continue

                raw_desc = item.get("description", "")
                cleaned_desc = self.clean_html(raw_desc)
                location = item.get("location") or "Worldwide / Remote"
                tags = item.get("tags", [])
                
                skills = self.extract_skills(f"{title} {cleaned_desc}", existing_skills=tags)
                level, is_fresher = self.detect_fresher_and_level(title, cleaned_desc)

                salary_min = float(item.get("salary_min")) if item.get("salary_min") else None
                salary_max = float(item.get("salary_max")) if item.get("salary_max") else None
                geo = self.detect_region(location, cleaned_desc)
                role_domain = self.detect_role_domain(title, cleaned_desc)

                job = JobPosting(
                    source="remoteok",
                    source_name="RemoteOK",
                    source_job_id=str(item.get("id") or ""),
                    title=title,
                    company=company,
                    location=location,
                    city=geo.get("city"),
                    country=geo.get("country", "Worldwide"),
                    region=geo.get("region", "Global"),
                    role_domain=role_domain,
                    remote=True,
                    remote_type="Remote",
                    employment_type="Full-time",
                    salary_min=salary_min,
                    salary_max=salary_max,
                    salary_currency="USD",
                    description=cleaned_desc[:3000],
                    skills=skills,
                    experience_level=level,
                    apply_url=apply_url,
                    source_url=apply_url,
                    published_at=item.get("date"),
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
            self.log(f"Error fetching jobs from RemoteOK: {e}", level="error")

        return jobs

