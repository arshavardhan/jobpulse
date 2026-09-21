import logging
from typing import List, Optional
from src.scrapers.base import BaseScraper
from src.models.job import JobPosting
from src.config import settings

logger = logging.getLogger(__name__)

class JobicyScraper(BaseScraper):
    """Scraper for Jobicy Remote Jobs API."""

    def __init__(self):
        super().__init__(name="Jobicy", base_url="https://jobicy.com/api/v2/remote-jobs")

    def fetch_jobs(self, query: Optional[str] = None, limit: int = 40) -> List[JobPosting]:
        jobs: List[JobPosting] = []
        try:
            params = {"count": limit}
            response = self.get_with_retry(self.base_url, params=params)
            if not response or response.status_code != 200:
                self.log("Jobicy API unavailable", level="warning")
                return []

            data = response.json()
            items = data.get("jobs", [])

            for item in items[:limit]:
                title = item.get("jobTitle", "").strip()
                company = item.get("companyName", "").strip()
                apply_url = item.get("url") or f"https://jobicy.com/jobs/{item.get('id', '')}"
                if not title or not company or not self.is_valid_url(apply_url):
                    continue

                raw_desc = item.get("jobDescription") or item.get("jobExcerpt", "")
                cleaned_desc = self.clean_html(raw_desc)
                
                raw_geo = item.get("jobGeo") or "Remote"
                if isinstance(raw_geo, list):
                    location = ", ".join(str(g) for g in raw_geo if g) or "Remote"
                else:
                    location = str(raw_geo or "Remote")

                raw_type = item.get("jobType")
                if isinstance(raw_type, list):
                    emp_type = ", ".join(str(t) for t in raw_type if t) or "Full-time"
                else:
                    emp_type = str(raw_type or "Full-time")

                combined = f"{title} {company} {location} {cleaned_desc}".lower()

                if query and query.lower() not in combined:
                    continue

                skills = self.extract_skills(combined)
                level, is_fresher = self.detect_fresher_and_level(
                    title=title,
                    description=cleaned_desc,
                    employment_type=emp_type
                )

                salary_min = None
                salary_max = None
                try:
                    if item.get("annualSalaryMin"):
                        salary_min = float(item.get("annualSalaryMin"))
                    if item.get("annualSalaryMax"):
                        salary_max = float(item.get("annualSalaryMax"))
                except (ValueError, TypeError):
                    pass

                geo = self.detect_region(location, cleaned_desc)
                role_domain = self.detect_role_domain(title, cleaned_desc)

                job = JobPosting(
                    source="jobicy",
                    source_name="Jobicy",
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
                    employment_type=emp_type,
                    salary_min=salary_min,
                    salary_max=salary_max,
                    salary_currency=item.get("salaryCurrency") or "USD",
                    description=cleaned_desc[:3000],
                    skills=skills,
                    experience_level=level,
                    apply_url=apply_url,
                    source_url=apply_url,
                    published_at=item.get("pubDate"),
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
            self.log(f"Error fetching jobs from Jobicy: {e}", level="error")

        return jobs

