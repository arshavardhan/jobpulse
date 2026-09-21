import re
import logging
import xml.etree.ElementTree as ET
from typing import List, Optional
from urllib.parse import urlparse

from src.scrapers.base import BaseScraper
from src.models.job import JobPosting

logger = logging.getLogger(__name__)

class HasjobScraper(BaseScraper):
    """Live Atom feed scraper for Hasjob.co (India's premier open tech community job board)."""

    def __init__(self):
        super().__init__(name="Hasjob", base_url="https://hasjob.co/feed")

    def fetch_jobs(self, query: Optional[str] = None, limit: int = 25) -> List[JobPosting]:
        jobs: List[JobPosting] = []
        response = self.get_with_retry(self.base_url)
        if not response or response.status_code != 200:
            self.log("Failed to fetch Hasjob Atom feed", level="warning")
            return []

        try:
            # Hasjob uses Atom namespace
            root = ET.fromstring(response.content)
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            entries = root.findall("atom:entry", ns)

            for entry in entries[:limit * 2]:
                title = entry.findtext("atom:title", default="", namespaces=ns).strip()
                if not title:
                    continue

                link_el = entry.find("atom:link", ns)
                apply_url = ""
                if link_el is not None:
                    apply_url = link_el.attrib.get("href", "").strip()
                if not apply_url:
                    apply_url = entry.findtext("atom:id", default="", namespaces=ns).strip()

                if not self.is_valid_url(apply_url):
                    continue

                # Derive company name from Hasjob URL or content
                # Format: https://hasjob.co/<company-domain>/<slug>
                company = "Hasjob Partner"
                parsed_url = urlparse(apply_url)
                parts = [p for p in parsed_url.path.strip("/").split("/") if p]
                if parts and len(parts) >= 1:
                    raw_domain = parts[0]
                    # clean company name from domain (e.g. 'nexailabs.com' -> 'Naxailabs')
                    cleaned_name = raw_domain.split(".")[0].capitalize()
                    if len(cleaned_name) >= 2:
                        company = cleaned_name

                raw_location = entry.findtext("atom:location", default="", namespaces=ns).strip() or "India"
                content_html = entry.findtext("atom:content", default="", namespaces=ns)
                description = self.clean_html(content_html)

                # Query filter if supplied
                combined = f"{title} {company} {raw_location} {description}".lower()
                if query and query.lower() not in combined:
                    continue

                # Region & fresher analysis
                geo = self.detect_region(raw_location, description)
                level, is_fresher = self.detect_fresher_and_level(title, description)
                skills = self.extract_skills(combined)
                pub_date = entry.findtext("atom:published", default="", namespaces=ns)
                role_domain = self.detect_role_domain(title, description)

                job = JobPosting(
                    source="hasjob",
                    source_name="Hasjob.co",
                    source_job_id=parts[-1] if len(parts) > 1 else None,
                    title=title,
                    company=company,
                    location=raw_location,
                    city=geo.get("city"),
                    country=geo.get("country", "India"),
                    region=geo.get("region", "India"),
                    role_domain=role_domain,
                    remote=geo.get("remote", False),
                    remote_type=geo.get("remote_type", "Onsite"),
                    employment_type="Internship" if is_fresher else "Full-time",
                    experience_level=level,
                    salary_min=None,
                    salary_max=None,
                    salary_currency="INR" if geo.get("region") == "India" else "USD",
                    skills=skills,
                    apply_url=apply_url,
                    source_url=apply_url,
                    published_at=pub_date,
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
                    self.log(f"Rejected invalid job from Hasjob: {reason}", level="warning")

        except Exception as e:
            self.log(f"Error parsing Hasjob Atom feed: {e}", level="error")

        return jobs
