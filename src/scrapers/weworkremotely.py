import logging
import xml.etree.ElementTree as ET
from typing import List, Optional
from src.scrapers.base import BaseScraper
from src.models.job import JobPosting
from src.config import settings

logger = logging.getLogger(__name__)

WWR_FEEDS = [
    ("https://weworkremotely.com/categories/remote-programming-jobs.rss", "Engineering"),
    ("https://weworkremotely.com/categories/remote-design-jobs.rss", "Design"),
    ("https://weworkremotely.com/categories/remote-product-jobs.rss", "Product"),
    ("https://weworkremotely.com/categories/remote-customer-support-jobs.rss", "Customer Support"),
    ("https://weworkremotely.com/categories/remote-sales-and-marketing-jobs.rss", "Marketing"),
    ("https://weworkremotely.com/categories/remote-management-and-finance-jobs.rss", "Finance"),
    ("https://weworkremotely.com/categories/remote-devops-sysadmin-jobs.rss", "Engineering")
]

class WeWorkRemotelyScraper(BaseScraper):
    """Scraper for WeWorkRemotely open RSS feeds covering all major startup and remote career disciplines."""

    def __init__(self):
        super().__init__(name="WeWorkRemotely", base_url="https://weworkremotely.com")

    def fetch_jobs(self, query: Optional[str] = None, limit: int = 40) -> List[JobPosting]:
        jobs: List[JobPosting] = []
        seen_urls = set()
        per_feed_limit = max(8, limit // len(WWR_FEEDS) + 2)

        for feed_url, default_domain in WWR_FEEDS:
            if len(jobs) >= limit:
                break
            try:
                response = self.get_with_retry(feed_url)
                if not response or response.status_code != 200:
                    continue

                root = ET.fromstring(response.content)
                items = root.findall("./channel/item")

                feed_count = 0
                for item in items:
                    if feed_count >= per_feed_limit or len(jobs) >= limit:
                        break

                    raw_title = item.find("title").text if item.find("title") is not None else ""
                    apply_url = item.find("link").text if item.find("link") is not None else ""
                    raw_desc = item.find("description").text if item.find("description") is not None else ""
                    pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""

                    if not raw_title or not self.is_valid_url(apply_url) or apply_url in seen_urls:
                        continue

                    # WWR titles are usually formatted as "Company: Job Title"
                    if ":" in raw_title:
                        company, title = [p.strip() for p in raw_title.split(":", 1)]
                    else:
                        company, title = "Remote Tech", raw_title.strip()

                    cleaned_desc = self.clean_html(raw_desc)
                    combined = f"{title} {company} {cleaned_desc}".lower()

                    if query and query.lower() not in combined:
                        continue

                    seen_urls.add(apply_url)
                    skills = self.extract_skills(combined)
                    level, is_fresher = self.detect_fresher_and_level(title, cleaned_desc)
                    geo = self.detect_region("Remote / Worldwide", cleaned_desc)
                    role_domain = self.detect_role_domain(title, cleaned_desc) or default_domain

                    job = JobPosting(
                        source="weworkremotely",
                        source_name="WeWorkRemotely",
                        source_job_id=apply_url.split("/")[-1] if "/" in apply_url else None,
                        title=title,
                        company=company,
                        location="Remote / Worldwide",
                        city=geo.get("city"),
                        country=geo.get("country", "Worldwide"),
                        region=geo.get("region", "Global"),
                        role_domain=role_domain,
                        remote=True,
                        remote_type="Remote",
                        employment_type="Full-time",
                        salary_min=None,
                        salary_max=None,
                        salary_currency="USD",
                        description=cleaned_desc[:3000],
                        skills=skills,
                        experience_level=level,
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
                        feed_count += 1
                    else:
                        self.log(f"Rejected job: {reason}", level="warning")

            except Exception as e:
                self.log(f"Error fetching from WeWorkRemotely feed {feed_url}: {e}", level="warning")

        return jobs

