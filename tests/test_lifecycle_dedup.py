import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta
from requests.exceptions import Timeout, HTTPError

from src.models.job import normalize_url, JobPosting, compute_hash
from src.services.lifecycle import verify_job_url, run_lifecycle_freshness_check, is_direct_source
from src.database.db import init_db, SessionLocal
from src.database.models import JobModel

def test_url_normalization():
    # Strips tracking query parameters, trailing slash, lowercases host
    raw1 = "https://jobs.lever.co/meesho/123/apply/?utm_source=linkedin&utm_medium=feed&ref=job_board"
    norm1 = normalize_url(raw1)
    assert norm1 == "https://jobs.lever.co/meesho/123/apply"
    assert "utm_source" not in norm1
    assert "utm_medium" not in norm1
    assert "ref" not in norm1

    raw2 = "HTTP://HASJOB.CO/company/role/"
    norm2 = normalize_url(raw2)
    assert norm2 == "http://hasjob.co/company/role"

def test_content_hash_consistency():
    j1 = JobPosting(
        title="Software Engineer",
        company="Meesho",
        location="Bengaluru",
        description="Developing Python APIs for payment gateway.",
        apply_url="https://jobs.lever.co/meesho/123/apply"
    )
    j2 = JobPosting(
        title="  Software   Engineer  ",
        company="Meesho",
        location="Bengaluru, Karnataka",
        description="Developing Python APIs for payment gateway.",
        apply_url="https://jobs.lever.co/meesho/456/apply"
    )
    # Content hash should be identical because normalized title, company, description match
    assert j1.content_hash == j2.content_hash

def test_verify_job_url_outcomes():
    # 1. 200 OK -> VERIFIED
    mock_200 = MagicMock(status_code=200)
    with patch("requests.head", return_value=mock_200):
        status, code = verify_job_url("https://jobs.lever.co/meesho/123/apply")
        assert status == "VERIFIED"
        assert code == 200

    # 2. 404 Not Found -> EXPIRED
    mock_404 = MagicMock(status_code=404)
    with patch("requests.head", return_value=mock_404):
        status, code = verify_job_url("https://jobs.lever.co/meesho/expired-123/apply")
        assert status == "EXPIRED"
        assert code == 404

    # 3. 429 Rate Limit -> UNREACHABLE (Must NOT expire!)
    mock_429 = MagicMock(status_code=429)
    with patch("requests.head", return_value=mock_429):
        status, code = verify_job_url("https://himalayas.app/jobs/busy")
        assert status == "UNREACHABLE"
        assert code == 429

    # 4. Timeout / Network error -> UNREACHABLE (Must NOT expire!)
    with patch("requests.head", side_effect=Timeout("Connection timed out")):
        status, code = verify_job_url("https://hasjob.co/slow")
        assert status == "UNREACHABLE"
        assert code is None

    # 5. Invalid URL
    status, code = verify_job_url("invalid-url-without-scheme")
    assert status == "INVALID"

def test_lifecycle_freshness_check():
    init_db()
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    old_time = now - timedelta(days=20)

    # Insert an old job
    old_job = JobModel(
        id="test-old-job-99",
        title="Old Developer Role",
        company="PastTech",
        location="Remote",
        apply_url="https://jobs.lever.co/old/99/apply",
        description="Old role description",
        status="ACTIVE",
        first_seen_at=old_time,
        last_seen_at=old_time
    )
    db.merge(old_job)
    db.commit()

    # Run check with 14-day threshold
    res = run_lifecycle_freshness_check(db, max_unseen_days=14)
    assert res["marked_stale"] >= 1

    updated = db.query(JobModel).filter(JobModel.id == "test-old-job-99").first()
    assert updated.status == "STALE"

    db.delete(updated)
    db.commit()
    db.close()

def test_direct_source_preference():
    assert is_direct_source("lever") is True
    assert is_direct_source("hasjob") is True
    assert is_direct_source("jobicy") is False
    assert is_direct_source("remoteok") is False
