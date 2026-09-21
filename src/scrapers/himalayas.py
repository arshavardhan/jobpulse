import logging
from typing import List, Optional
from src.scrapers.base import BaseScraper
from src.models.job import JobPosting
from src.config import settings

logger = logging.getLogger(__name__)

class HimalayasScraper(BaseScraper):
    """Scraper for Himalayas Jobs API covering global remote software and AI engineering roles."""

    def __init__(self):
        super().__init__(name="Himalayas", base_url="https://himalayas.app/jobs/api")

    def fetch_jobs(self, query: Optional[str] = None, limit: int = 40) -> List[JobPosting]:
        jobs: List[JobPosting] = []
        try:
            params = {"limit": limit}
            response = self.get_with_retry(self.base_url, params=params)
            if not response or response.status_code != 200:
                self.log(f"Himalayas API unavailable", level="warning")
                return []

            data = response.json()
            items = data.get("jobs", [])

            for item in items[:limit]:
                title = item.get("title", "").strip()
                company = item.get("companyName", "").strip()
                apply_url = item.get("applicationLink") or f"https://himalayas.app/jobs/{item.get('guid', '')}"
                if not title or not company or not self.is_valid_url(apply_url):
                    continue

                raw_desc = item.get("description") or item.get("excerpt", "")
                cleaned_desc = self.clean_html(raw_desc)
                location = item.get("location") or "Worldwide / Remote"
                combined = f"{title} {company} {location} {cleaned_desc}".lower()

                if query and query.lower() not in combined:
                    continue

                tags = item.get("categories", [])
                skills = self.extract_skills(combined, existing_skills=tags)
                
                # Check seniority from Himalayas payload
                seniority_list = item.get("seniority", [])
                if any("entry" in str(s).lower() or "junior" in str(s).lower() for s in seniority_list):
                    level = "Fresher / Entry"
                    is_fresher = True
                else:
                    level, is_fresher = self.detect_fresher_and_level(title, cleaned_desc)

                salary_min = None
                salary_max = None
                try:
                    if item.get("minSalary"):
                        salary_min = float(item.get("minSalary"))
                    if item.get("maxSalary"):
                        salary_max = float(item.get("maxSalary"))
                except (ValueError, TypeError):
                    pass

                geo = self.detect_region(location, cleaned_desc)
                role_domain = self.detect_role_domain(title, cleaned_desc)

                job = JobPosting(
                    source="himalayas",
                    source_name="Himalayas",
                    source_job_id=str(item.get("guid") or ""),
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
                    salary_currency=item.get("currency") or "USD",
                    description=cleaned_desc[:3000],
                    skills=skills,
                    experience_level=level,
                    apply_url=apply_url,
                    source_url=f"https://himalayas.app/jobs/{item.get('guid', '')}",
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
            self.log(f"Error fetching from Himalayas: {e}", level="error")

        return jobs

