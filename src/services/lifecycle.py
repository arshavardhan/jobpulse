import logging
from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional, Dict, Any, List
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError
from sqlalchemy.orm import Session

from src.models.job import normalize_url, compute_hash
from src.database.models import JobModel

logger = logging.getLogger(__name__)

DIRECT_EMPLOYER_SOURCES = {"lever", "greenhouse", "ashby", "workable", "smartrecruiters", "hasjob"}

SOURCE_PRIORITY_MAP = {
    "lever": 100,
    "greenhouse": 100,
    "ashby": 100,
    "workable": 95,
    "smartrecruiters": 95,
    "hasjob": 90,
    "remotive": 80,
    "himalayas": 80,
    "weworkremotely": 75,
    "jobicy": 75,
    "arbeitnow": 70,
    "remoteok": 70,
    "web": 50
}

def get_source_priority(source: str) -> int:
    """Return numeric priority rank for a source (higher is more direct / canonical)."""
    source_lower = (source or "").lower()
    for k, v in SOURCE_PRIORITY_MAP.items():
        if k in source_lower:
            return v
    return 50

def is_direct_source(source: str) -> bool:
    """Return True if source is a direct company ATS or career board rather than general aggregator."""
    return any(d in (source or "").lower() for d in DIRECT_EMPLOYER_SOURCES)

def verify_job_url(apply_url: str, timeout: int = 5) -> Tuple[str, Optional[int]]:
    """
    Verify reachability of an application URL.
    Returns (status, http_code):
      - ('VERIFIED', 200) -> Reachable
      - ('EXPIRED', 404/410) -> Confirmed gone
      - ('UNREACHABLE', code) -> Rate limited, temporary timeout, or server 5xx (do NOT expire)
      - ('INVALID', None) -> Malformed URL
    """
    if not apply_url or not isinstance(apply_url, str):
        return "INVALID", None

    url_str = apply_url.strip()
    if not (url_str.startswith("http://") or url_str.startswith("https://")):
        return "INVALID", None

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    try:
        # Try HEAD first for minimal payload
        resp = requests.head(url_str, headers=headers, timeout=timeout, allow_redirects=True)
        # If server disallows HEAD (405 Method Not Allowed), retry with streaming GET
        if resp.status_code == 405:
            resp = requests.get(url_str, headers=headers, timeout=timeout, allow_redirects=True, stream=True)

        status_code = resp.status_code

        if 200 <= status_code < 400:
            return "VERIFIED", status_code
        elif status_code in (404, 410):
            return "EXPIRED", status_code
        elif status_code in (403, 429) or status_code >= 500:
            return "UNREACHABLE", status_code
        else:
            return "UNREACHABLE", status_code

    except (Timeout, ConnectionError):
        return "UNREACHABLE", None
    except RequestException:
        return "UNREACHABLE", None
    except Exception:
        return "INVALID", None

def run_lifecycle_freshness_check(db: Session, max_unseen_days: int = 14) -> Dict[str, int]:
    """
    Apply lifecycle transitions:
    ACTIVE -> STALE (if not seen for > max_unseen_days)
    """
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=max_unseen_days)
    stale_jobs = db.query(JobModel).filter(
        JobModel.status == "ACTIVE",
        JobModel.last_seen_at < cutoff_date
    ).all()

    marked_stale = 0
    for job in stale_jobs:
        job.status = "STALE"
        marked_stale += 1

    if marked_stale > 0:
        db.commit()
        logger.info(f"[Lifecycle] Transitioned {marked_stale} jobs from ACTIVE to STALE.")

    return {"marked_stale": marked_stale}

def batch_verify_active_job_urls(db: Session, limit: int = 20) -> Dict[str, Any]:
    """
    Verify URLs of active jobs that haven't been verified recently.
    """
    jobs = db.query(JobModel).filter(
        JobModel.status == "ACTIVE",
        (JobModel.verification_status == "UNVERIFIED") | (JobModel.last_verified_at == None)
    ).limit(limit).all()

    verified = 0
    unreachable = 0
    expired = 0

    for job in jobs:
        ver_status, code = verify_job_url(job.apply_url)
        job.last_verified_at = datetime.now(timezone.utc)
        job.verification_status = ver_status

        if ver_status == "VERIFIED":
            verified += 1
        elif ver_status == "EXPIRED":
            job.status = "EXPIRED"
            expired += 1
        else:
            unreachable += 1

    db.commit()
    return {
        "checked_count": len(jobs),
        "verified": verified,
        "unreachable": unreachable,
        "expired": expired
    }
