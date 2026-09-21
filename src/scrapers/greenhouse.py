import logging
from typing import List, Optional, Dict, Any
from bs4 import BeautifulSoup
from src.scrapers.base import BaseScraper
from src.models.job import JobPosting, normalize_url

logger = logging.getLogger(__name__)

class GreenhouseScraper(BaseScraper):
    """
    Reusable Greenhouse ATS Career Scraper.
    Fetches genuine live jobs from public Greenhouse boards API:
    https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true
    """

    def __init__(self, board_token: str, company_name: Optional[str] = None):
        self.board_token = board_token.strip().lower()
        self.company_name = company_name or self.board_token.capitalize()
        endpoint = f"https://boards-api.greenhouse.io/v1/boards/{self.board_token}/jobs?content=true"
        super().__init__(
            name=f"Greenhouse-{self.company_name}",
            base_url=endpoint
        )
        self.ats_type = "greenhouse"

    def fetch_jobs(self, query: Optional[str] = None, limit: int = 30) -> List[JobPosting]:
        jobs: List[JobPosting] = []
        response = self.get_with_retry(self.base_url)
        if not response or response.status_code != 200:
            self.log(f"Greenhouse endpoint unavailable for {self.board_token} (status={response.status_code if response else 'None'})", level="warning")
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

                location_obj = item.get("location") or {}
                location = location_obj.get("name") if isinstance(location_obj, dict) else str(location_obj or "Remote")
                if not location:
                    location = "Remote"

                # Parse clean text from content HTML
                raw_html = item.get("content") or ""
                description = ""
                if raw_html:
                    try:
                        soup = BeautifulSoup(raw_html, "html.parser")
                        description = soup.get_text(separator="\n", strip=True)
                    except Exception:
                        description = raw_html[:1500]

                # Direct apply URL & source URL
                apply_url = item.get("absolute_url") or f"https://boards.greenhouse.io/{self.board_token}/jobs/{item.get('id')}"
                source_url = apply_url

                # Extract metadata
                is_rem = bool("remote" in location.lower() or "remote" in title.lower() or "anywhere" in location.lower())
                geo = self.detect_region(location, description)
                region = geo.get("region", "Global")
                city = geo.get("city")
                country = geo.get("country", "India" if region == "India" else "Unknown")
                is_rem = is_rem or geo.get("remote", False)
                exp_level, is_fresh = self.detect_fresher_and_level(title, description)
                extracted_skills = self.extract_skills(f"{title} {description}")
                role_domain = self.detect_role_domain(title, description)

                job_id = f"gh_{self.board_token}_{item.get('id')}"
                norm_apply = normalize_url(apply_url)

                job = JobPosting(
                    id=job_id,
                    source="greenhouse",
                    source_name=f"Greenhouse ({self.company_name})",
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
                    employment_type="Full-time",
                    experience_level=exp_level,
                    is_fresher=is_fresh,
                    skills=extracted_skills,
                    apply_url=norm_apply or apply_url,
                    source_url=source_url,
                    published_at=item.get("updated_at"),
                    canonical_source="greenhouse",
                    discovered_via="company_career_page",
                    sources=[f"Greenhouse ({self.company_name})"],
                    status="ACTIVE",
                    verification_status="VERIFIED"
                )

                if query and not (query.lower() in title.lower() or query.lower() in description.lower()):
                    continue

                jobs.append(job)
                if len(jobs) >= limit:
                    break

            self.log(f"Successfully processed {len(jobs)} jobs from Greenhouse ({self.company_name}).")
            return jobs

        except Exception as e:
            self.log(f"Error parsing Greenhouse response for {self.board_token}: {e}", level="warning")
            return []
