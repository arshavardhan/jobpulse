import logging
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup
from src.scrapers.base import BaseScraper
from src.models.job import JobPosting, normalize_url

logger = logging.getLogger(__name__)

class AshbyScraper(BaseScraper):
    """
    Reusable Ashby ATS Career Scraper.
    Fetches genuine live jobs from Ashby public job board API:
    https://api.ashbyhq.com/posting-api/job-board/{company_slug}
    """

    def __init__(self, company_slug: str, company_name: Optional[str] = None):
        self.company_slug = company_slug.strip().lower()
        self.company_name = company_name or self.company_slug.capitalize()
        endpoint = f"https://api.ashbyhq.com/posting-api/job-board/{self.company_slug}"
        super().__init__(
            name=f"Ashby-{self.company_name}",
            base_url=endpoint
        )
        self.ats_type = "ashby"

    def fetch_jobs(self, query: Optional[str] = None, limit: int = 30) -> List[JobPosting]:
        jobs: List[JobPosting] = []
        response = self.get_with_retry(self.base_url)
        if not response or response.status_code != 200:
            self.log(f"Ashby endpoint unavailable for {self.company_slug} (status={response.status_code if response else 'None'})", level="warning")
            return []

        try:
            data = response.json()
            items = data.get("jobs", []) if isinstance(data, dict) else []
            if not isinstance(items, list):
                return []

            for item in items[:limit * 2]:
                title = (item.get("title") or "").strip()
                if not title:
                    continue

                location = (item.get("location") or "Remote").strip()
                is_rem = bool(item.get("isRemote") or "remote" in location.lower() or "remote" in title.lower())

                # Parse clean description
                raw_html = item.get("descriptionHtml") or ""
                description = ""
                if raw_html:
                    try:
                        soup = BeautifulSoup(raw_html, "html.parser")
                        description = soup.get_text(separator="\n", strip=True)
                    except Exception:
                        description = raw_html[:1500]

                # Direct apply URL
                job_url = item.get("jobUrl") or f"https://jobs.ashbyhq.com/{self.company_slug}/{item.get('id')}"
                apply_url = item.get("applyUrl") or job_url

                geo = self.detect_region(location, description)
                region = geo.get("region", "Global")
                city = geo.get("city")
                country = geo.get("country", "India" if region == "India" else "Unknown")
                is_rem = is_rem or geo.get("remote", False)
                exp_level, is_fresh = self.detect_fresher_and_level(title, description)
                extracted_skills = self.extract_skills(f"{title} {description}")
                role_domain = self.detect_role_domain(title, description)

                job_id = f"ashby_{self.company_slug}_{item.get('id')}"
                norm_apply = normalize_url(apply_url)

                job = JobPosting(
                    id=job_id,
                    source="ashby",
                    source_name=f"Ashby ({self.company_name})",
                    source_job_id=str(item.get("id")),
                    title=title,
                    company=self.company_name,
                    description=description[:3000] if description else f"{title} at {self.company_name}",
                    location=location,
                    city=city,
                    country=country,
                    region=region,
                    role_domain=role_domain,
                    remote=is_rem,
                    remote_type="Remote" if is_rem else "Onsite",
                    employment_type=item.get("employmentType") or "Full-time",
                    experience_level=exp_level,
                    is_fresher=is_fresh,
                    skills=extracted_skills,
                    apply_url=norm_apply or apply_url,
                    source_url=job_url,
                    published_at=item.get("publishedAt"),
                    canonical_source="ashby",
                    discovered_via="company_career_page",
                    sources=[f"Ashby ({self.company_name})"],
                    status="ACTIVE",
                    verification_status="VERIFIED"
                )

                if query and not (query.lower() in title.lower() or query.lower() in description.lower()):
                    continue

                jobs.append(job)
                if len(jobs) >= limit:
                    break

            self.log(f"Successfully processed {len(jobs)} jobs from Ashby ({self.company_name}).")
            return jobs

        except Exception as e:
            self.log(f"Error parsing Ashby response for {self.company_slug}: {e}", level="warning")
            return []
