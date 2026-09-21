import time
import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Callable, Dict, Any
from sqlalchemy.orm import Session

from src.scrapers import registry, SourceRegistry
from src.models.job import JobPosting, normalize_url
from src.database.models import JobModel, SourceHealthModel
from src.database.db import SessionLocal
from src.services.lifecycle import is_direct_source, get_source_priority

logger = logging.getLogger(__name__)

class ScoutAgent:
    """
    Autonomous Scout Agent: crawls 100% genuine external job sources,
    validates, deduplicates via multiple strategies, and manages lifecycle freshness.
    """

    def __init__(self, log_callback: Optional[Callable[[str], None]] = None):
        self.registry = registry
        # Dynamically load active genuine scrapers from registry
        self.scrapers = self.registry.get_active_scrapers()
        self.log_callback = log_callback
        self.latest_source_health: List[Dict[str, Any]] = []

    def log(self, message: str):
        logger.info(f"[ScoutAgent] {message}")
        if self.log_callback:
            self.log_callback(f"[ScoutAgent] {message}")

    def execute_hunt(
        self,
        query: Optional[str] = None,
        limit_per_source: int = 15,
        db: Optional[Session] = None
    ) -> List[JobPosting]:
        """
        Orchestrate multi-source search across live job feeds.
        One failed source NEVER stops other sources from running.
        """
        # Dynamically refresh scrapers from registry
        self.scrapers = self.registry.get_active_scrapers(db)
        self.log(f"Starting job hunt query='{query or 'All'}' across {len(self.scrapers)} active intelligence sources...")
        discovered_jobs: List[JobPosting] = []
        source_metrics: List[Dict[str, Any]] = []

        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        try:
            now_utc = datetime.now(timezone.utc)

            for scraper in self.scrapers:
                start_time = time.time()
                started_at = datetime.now(timezone.utc)
                source_id = getattr(scraper, "name", "Unknown").lower()
                source_name = getattr(scraper, "name", "Unknown")

                status = "SUCCESS"
                jobs_found = 0
                jobs_accepted = 0
                jobs_updated = 0
                jobs_rejected = 0
                jobs_duplicates = 0
                error_msg = ""
                harvested_for_scraper: List[JobPosting] = []

                self.log(f"Contacting live source: {source_name}...")
                try:
                    harvested_for_scraper = scraper.fetch_jobs(query=query, limit=limit_per_source)
                    jobs_found = len(harvested_for_scraper)
                    self.log(f"Harvested {jobs_found} raw postings from {source_name}.")
                except Exception as e:
                    status = "FAILED"
                    error_msg = str(e)
                    self.log(f"Error harvesting from {source_name}: {e}")

                elapsed_ms = int((time.time() - start_time) * 1000)

                # Deduplicate and persist immediately per source
                seen_in_batch_urls = set()
                seen_in_batch_fingerprints = set()

                for job in harvested_for_scraper:
                    # Validate URL and minimum required fields
                    valid, reason = scraper.validate_job(job)
                    if not valid:
                        jobs_rejected += 1
                        self.log(f"[{source_name}] Rejected invalid job: {reason}")
                        continue

                    # Intra-batch deduplication
                    batch_url_key = job.url_hash or job.apply_url
                    batch_fp_key = f"{job.title.strip().lower()}@{job.company.strip().lower()}"
                    if batch_url_key in seen_in_batch_urls or batch_fp_key in seen_in_batch_fingerprints:
                        jobs_duplicates += 1
                        continue
                    seen_in_batch_urls.add(batch_url_key)
                    seen_in_batch_fingerprints.add(batch_fp_key)

                    # Multi-strategy Database Deduplication:
                    # 1. By url_hash
                    # 2. By source + source_job_id
                    # 3. By content_hash
                    # 4. By normalized title + company
                    existing: Optional[JobModel] = None

                    if job.url_hash:
                        existing = db.query(JobModel).filter(JobModel.url_hash == job.url_hash).first()

                    if not existing and job.source and job.source_job_id:
                        existing = db.query(JobModel).filter(
                            JobModel.source == job.source,
                            JobModel.source_job_id == job.source_job_id
                        ).first()

                    if not existing and job.content_hash:
                        existing = db.query(JobModel).filter(JobModel.content_hash == job.content_hash).first()

                    if not existing:
                        existing = db.query(JobModel).filter(
                            JobModel.company.ilike(job.company.strip()),
                            JobModel.title.ilike(job.title.strip())
                        ).first()

                    if existing:
                        # Update freshness
                        existing.last_seen_at = now_utc

                        # Update provenance tracking
                        curr_sources = list(existing.sources or [])
                        if job.source not in curr_sources:
                            curr_sources.append(job.source)
                            existing.sources = curr_sources

                        # Canonical promotion: if current source has strictly higher priority, promote URL and canonical_source
                        curr_priority = get_source_priority(existing.canonical_source or existing.source)
                        new_priority = get_source_priority(job.source)
                        if new_priority > curr_priority:
                            existing.canonical_source = job.source
                            existing.apply_url = job.apply_url
                            existing.source = job.source
                            existing.source_name = job.source_name
                            self.log(f"Promoted {job.title} to canonical employer URL ({job.source}): {job.apply_url}")

                        jobs_updated += 1
                    else:
                        # New genuine record
                        record = JobModel(
                            id=job.id or str(uuid.uuid4()),
                            source=job.source,
                            source_name=job.source_name,
                            canonical_source=job.canonical_source or job.source,
                            discovered_via=job.discovered_via or job.source,
                            source_job_id=job.source_job_id,
                            title=job.title,
                            company=job.company,
                            description=job.description or "",
                            location=job.location,
                            city=job.city,
                            country=job.country,
                            region=job.region,
                            role_domain=getattr(job, "role_domain", "Engineering") or "Engineering",
                            remote=job.remote,
                            remote_type=job.remote_type,
                            employment_type=job.employment_type,
                            experience_level=job.experience_level,
                            salary_min=job.salary_min,
                            salary_max=job.salary_max,
                            salary_currency=job.salary_currency,
                            apply_url=job.apply_url,
                            source_url=job.source_url or job.apply_url,
                            published_at=job.published_at,
                            first_seen_at=now_utc,
                            last_seen_at=now_utc,
                            last_verified_at=now_utc,
                            status="ACTIVE",
                            verification_status=job.verification_status,
                            is_fresher=job.is_fresher,
                            content_hash=job.content_hash,
                            url_hash=job.url_hash
                        )
                        record.sources = [job.source]
                        record.skills_required = job.skills
                        db.add(record)
                        jobs_accepted += 1
                        discovered_jobs.append(job)

                db.commit()

                # Record health entry
                finished_at = datetime.now(timezone.utc)
                health_rec = {
                    "source": source_id,
                    "source_name": source_name,
                    "started_at": started_at.isoformat(),
                    "finished_at": finished_at.isoformat(),
                    "status": status if jobs_found > 0 or not error_msg else "ERROR",
                    "jobs_found": jobs_found,
                    "jobs_accepted": jobs_accepted,
                    "jobs_updated": jobs_updated,
                    "jobs_rejected": jobs_rejected,
                    "jobs_duplicates": jobs_duplicates,
                    "errors": error_msg,
                    "latency_ms": elapsed_ms
                }
                source_metrics.append(health_rec)

                # Persist health metric to database
                db_health = SourceHealthModel(
                    source=source_id,
                    source_name=source_name,
                    started_at=started_at,
                    finished_at=finished_at,
                    status=health_rec["status"],
                    jobs_found=jobs_found,
                    jobs_accepted=jobs_accepted,
                    jobs_updated=jobs_updated,
                    jobs_rejected=jobs_rejected,
                    jobs_duplicates=jobs_duplicates,
                    errors=error_msg,
                    latency_ms=elapsed_ms
                )
                db.add(db_health)
                db.commit()

                self.log(f"[{source_name}] Summary: {jobs_found} found, {jobs_accepted} added, {jobs_updated} refreshed, {jobs_duplicates} dupes, {elapsed_ms}ms.")

            # Record health metrics for authorized-only partner boundaries (LinkedIn, Indeed, Naukri)
            for s_def in self.registry.get_all_definitions():
                if s_def.requires_auth and not s_def.enabled:
                    auth_rec = {
                        "source": s_def.name,
                        "source_name": s_def.display_name,
                        "started_at": now_utc.isoformat(),
                        "finished_at": now_utc.isoformat(),
                        "status": s_def.auth_status,
                        "jobs_found": 0,
                        "jobs_accepted": 0,
                        "jobs_updated": 0,
                        "jobs_rejected": 0,
                        "jobs_duplicates": 0,
                        "errors": f"Requires authorized partner credentials ({s_def.auth_status}). Automated scraping prohibited.",
                        "latency_ms": 0
                    }
                    source_metrics.append(auth_rec)

            self.latest_source_health = source_metrics
            self.log(f"Scout Hunt completed. Discovered {len(discovered_jobs)} new listings across all live feeds.")

        except Exception as e:
            db.rollback()
            self.log(f"Database error during hunt: {e}")
        finally:
            if close_session:
                db.close()

        return discovered_jobs

    def get_source_health_summary(self, db: Optional[Session] = None) -> List[Dict[str, Any]]:
        """Return the latest source health metrics for monitoring and diagnostics."""
        close_session = False
        if db is None:
            db = SessionLocal()
            close_session = True

        try:
            # Query recent health logs from DB
            records = db.query(SourceHealthModel).order_by(SourceHealthModel.started_at.desc()).limit(100).all()
            seen: Dict[str, Dict[str, Any]] = {}
            for r in records:
                s_key = (r.source or "").lower()
                if s_key not in seen:
                    seen[s_key] = {
                        "source": r.source,
                        "source_name": r.source_name,
                        "started_at": r.started_at.isoformat() if r.started_at else None,
                        "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                        "status": r.status,
                        "jobs_found": r.jobs_found,
                        "jobs_accepted": r.jobs_accepted,
                        "jobs_updated": r.jobs_updated,
                        "jobs_rejected": r.jobs_rejected,
                        "jobs_duplicates": r.jobs_duplicates,
                        "errors": r.errors,
                        "latency_ms": r.latency_ms
                    }

            # Supplement with registered source definitions so every adapter & boundary is shown
            results = []
            for s_def in self.registry.get_all_definitions():
                s_key = s_def.name.lower()
                if s_key in seen:
                    entry = seen[s_key]
                    entry["requires_auth"] = s_def.requires_auth
                    entry["type"] = s_def.source_type
                    entry["description"] = s_def.description
                    results.append(entry)
                else:
                    results.append({
                        "source": s_def.name,
                        "source_name": s_def.display_name,
                        "started_at": None,
                        "finished_at": None,
                        "status": s_def.auth_status if s_def.requires_auth else "READY",
                        "jobs_found": 0,
                        "jobs_accepted": 0,
                        "jobs_updated": 0,
                        "jobs_rejected": 0,
                        "jobs_duplicates": 0,
                        "errors": f"Authorized partner API ({s_def.auth_status})" if s_def.requires_auth else "",
                        "latency_ms": 0,
                        "requires_auth": s_def.requires_auth,
                        "type": s_def.source_type,
                        "description": s_def.description
                    })

            return results
        finally:
            if close_session:
                db.close()

