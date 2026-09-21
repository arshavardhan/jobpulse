import pytest
import json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from main import app
from src.services.ats_detector import detect_ats, discover_company_career_page
from src.scrapers.registry import registry, SourceRegistry, SourceDefinition
from src.scrapers.greenhouse import GreenhouseScraper
from src.scrapers.ashby import AshbyScraper
from src.scrapers.authorized_sources import LinkedInJobSource, IndeedJobSource, NaukriJobSource
from src.database.db import SessionLocal
from src.database.models import JobModel, ContactMessageModel, JobReportModel

client = TestClient(app)

def test_ats_detector_patterns():
    # Test HTML snippet detection for Greenhouse
    gh_html = '<html><body><div>Apply on <a href="https://boards.greenhouse.io/figma/jobs/123">Careers</a></div></body></html>'
    res = detect_ats("https://figma.com/careers", gh_html)
    assert res["ats_type"] == "greenhouse"
    assert res["slug"] == "figma"

    # Test Ashby
    ashby_html = '<html><body><iframe src="https://jobs.ashbyhq.com/linear"></iframe></body></html>'
    res = detect_ats("https://linear.app/jobs", ashby_html)
    assert res["ats_type"] == "ashby"
    assert res["slug"] == "linear"

    # Test Lever
    lever_html = '<html><body><a href="https://jobs.lever.co/meesho/abcdef">Join us</a></body></html>'
    res = detect_ats("https://meesho.io/careers", lever_html)
    assert res["ats_type"] == "lever"
    assert res["slug"] == "meesho"

    # Test Workable
    workable_html = '<html><body><a href="https://apply.workable.com/example-corp/j/123">Jobs</a></body></html>'
    res = detect_ats("https://example.com", workable_html)
    assert res["ats_type"] == "workable"
    assert res["slug"] == "example-corp"

    # Test Unknown
    res = detect_ats("https://plain-site.com", "<html><body>No ATS here</body></html>")
    assert res["ats_type"] == "unknown"

def test_source_registry_and_compliance_boundaries():
    reg = SourceRegistry()
    definitions = reg.get_all_definitions()
    assert len(definitions) >= 10

    # Test compliance-first partner sources
    linkedin = reg.get_source("linkedin")
    assert linkedin is not None
    assert linkedin.requires_auth is True
    assert linkedin.enabled is False
    assert linkedin.auth_status in ("AUTHORIZATION_REQUIRED", "UNCONFIGURED")

    indeed = reg.get_source("indeed")
    assert indeed is not None
    assert indeed.requires_auth is True
    assert indeed.enabled is False

    naukri = reg.get_source("naukri")
    assert naukri is not None
    assert naukri.requires_auth is True
    assert naukri.enabled is False

    # Check active scrapers instantiation
    active = reg.get_active_scrapers()
    assert len(active) > 0
    names = [getattr(s, "name", "") for s in active]
    assert "Hasjob" in names
    assert "Remotive" in names

def test_greenhouse_scraper_parsing():
    scraper = GreenhouseScraper("acme", "Acme Corp")
    fake_payload = {
        "jobs": [
            {
                "id": 998877,
                "title": "Senior Backend Engineer (Python)",
                "absolute_url": "https://boards.greenhouse.io/acme/jobs/998877",
                "location": {"name": "Bengaluru, India"},
                "content": "<p>We are looking for Python and FastAPI experts with Docker experience.</p>",
                "updated_at": "2026-03-20T10:00:00Z"
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_payload

    with patch.object(scraper.session, "get", return_value=mock_resp):
        jobs = scraper.fetch_jobs(limit=5)
        assert len(jobs) == 1
        j = jobs[0]
        assert j.company == "Acme Corp"
        assert j.source == "greenhouse"
        assert "python" in [s.lower() for s in j.skills]
        assert "Bengaluru" in j.location or "India" in j.location
        assert j.apply_url == "https://boards.greenhouse.io/acme/jobs/998877"

def test_ashby_scraper_parsing():
    scraper = AshbyScraper("acme", "Acme Tech")
    fake_payload = {
        "jobs": [
            {
                "id": "ashby-001",
                "title": "Staff Infrastructure Engineer",
                "department": "Engineering",
                "location": "Remote - India",
                "isRemote": True,
                "employmentType": "FullTime",
                "descriptionHtml": "<p>Build Kubernetes clusters and Python microservices.</p>",
                "publishedAt": "2026-03-20T12:00:00Z",
                "jobUrl": "https://jobs.ashbyhq.com/acme/ashby-001"
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_payload

    with patch.object(scraper.session, "get", return_value=mock_resp):
        jobs = scraper.fetch_jobs(limit=5)
        assert len(jobs) == 1
        j = jobs[0]
        assert j.company == "Acme Tech"
        assert j.source == "ashby"
        assert j.remote is True
        assert j.apply_url == "https://jobs.ashbyhq.com/acme/ashby-001"

def test_contact_and_report_endpoints():
    # 1. Test POST /api/contact
    contact_data = {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "subject": "Inquiry about partnership",
        "category": "Partnership",
        "message": "We would like to integrate our company job board."
    }
    resp = client.post("/api/contact", json=contact_data)
    assert resp.status_code == 200
    res_json = resp.json()
    assert res_json["email"] == "jane@example.com"
    assert res_json["status"] == "RECEIVED"
    assert "id" in res_json

    # Verify in DB
    db = SessionLocal()
    try:
        msg = db.query(ContactMessageModel).filter(ContactMessageModel.id == res_json["id"]).first()
        assert msg is not None
        assert msg.name == "Jane Doe"
    finally:
        db.close()

    # 2. Test POST /api/jobs/{id}/report
    # Create or fetch a real job to report
    db = SessionLocal()
    try:
        test_job = db.query(JobModel).first()
        if not test_job:
            test_job = JobModel(
                id="test-job-report-1",
                source="test",
                source_name="Test Source",
                title="Test Role",
                company="Test Corp",
                location="Bengaluru",
                apply_url="https://example.com/test-job",
                source_url="https://example.com/test-job"
            )
            db.add(test_job)
            db.commit()
            db.refresh(test_job)

        job_id = test_job.id
    finally:
        db.close()

    report_data = {
        "reason": "Broken link",
        "details": "The application page returns a 404.",
        "reporter_email": "candidate@example.com"
    }
    rep_resp = client.post(f"/api/jobs/{job_id}/report", json=report_data)
    assert rep_resp.status_code == 200
    rep_json = rep_resp.json()
    assert rep_json["job_id"] == job_id
    assert rep_json["reason"] == "Broken link"
    assert rep_json["status"] == "PENDING"

    # 3. Test GET /api/sources/health
    health_resp = client.get("/api/sources/health")
    assert health_resp.status_code == 200
    health_data = health_resp.json()
    assert isinstance(health_data, list)
    assert len(health_data) > 0
    # Verify LinkedIn/Indeed/Naukri boundaries are listed
    source_names = [h["source"] for h in health_data]
    assert "linkedin" in source_names
    assert "indeed" in source_names
    assert "naukri" in source_names

    # 4. Test GET /api/companies
    comp_resp = client.get("/api/companies")
    assert comp_resp.status_code == 200
    comp_data = comp_resp.json()
    assert isinstance(comp_data, list)
