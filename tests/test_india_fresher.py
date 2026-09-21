import pytest
from fastapi.testclient import TestClient
from main import app
from src.database.db import init_db, SessionLocal
from src.database.models import JobModel

@pytest.fixture
def client():
    return TestClient(app)

def test_india_and_fresher_jobs(client):
    init_db()
    db = SessionLocal()
    
    # Create test genuine records
    test_jobs = [
        JobModel(
            id="test-meesho-001",
            source="lever",
            source_name="Meesho Careers (Lever)",
            source_job_id="meesho-123",
            title="Software Development Engineer - Backend",
            company="Meesho",
            location="Bengaluru, Karnataka, India",
            city="Bengaluru",
            country="India",
            region="India",
            remote=False,
            remote_type="Onsite",
            employment_type="Full-time",
            experience_level="Mid-Level",
            salary_min=1800000.0,
            salary_max=2800000.0,
            salary_currency="INR",
            apply_url="https://jobs.lever.co/meesho/123/apply",
            source_url="https://jobs.lever.co/meesho/123",
            published_at="2026-09-18T10:00:00Z",
            description="Developing scalable order services in Python and FastAPI.",
            status="ACTIVE",
            verification_status="VERIFIED",
            is_fresher=False
        ),
        JobModel(
            id="test-cred-fresher-002",
            source="lever",
            source_name="CRED Careers (Lever)",
            source_job_id="cred-456",
            title="Data Science Intern / Fresher",
            company="CRED",
            location="Bengaluru, Karnataka, India",
            city="Bengaluru",
            country="India",
            region="India",
            remote=False,
            remote_type="Onsite",
            employment_type="Internship",
            experience_level="Fresher / Entry",
            salary_min=600000.0,
            salary_max=900000.0,
            salary_currency="INR",
            apply_url="https://jobs.lever.co/cred/456/apply",
            source_url="https://jobs.lever.co/cred/456",
            published_at="2026-09-18T11:00:00Z",
            description="Internship for campus graduates in Machine Learning and Python.",
            status="ACTIVE",
            verification_status="VERIFIED",
            is_fresher=True
        ),
        JobModel(
            id="test-global-003",
            source="himalayas",
            source_name="Himalayas",
            source_job_id="him-789",
            title="Senior Distributed Systems Architect",
            company="Lemon.io",
            location="Worldwide / Remote",
            city=None,
            country="Worldwide",
            region="Global",
            remote=True,
            remote_type="Remote",
            employment_type="Full-time",
            experience_level="Senior",
            salary_min=130000.0,
            salary_max=160000.0,
            salary_currency="USD",
            apply_url="https://himalayas.app/jobs/lemon-789",
            source_url="https://himalayas.app/jobs/lemon-789",
            published_at="2026-09-18T12:00:00Z",
            description="Architecting high throughput event streaming pipelines in Python and Kafka.",
            status="ACTIVE",
            verification_status="VERIFIED",
            is_fresher=False
        )
    ]

    for tj in test_jobs:
        existing = db.query(JobModel).filter(JobModel.id == tj.id).first()
        if not existing:
            tj.skills_required = ["python", "fastapi", "sql", "machine learning"]
            db.add(tj)
    db.commit()
    db.close()

    # 1. Test region=india filter
    res_india = client.get("/api/jobs?region=india")
    assert res_india.status_code == 200
    india_jobs = res_india.json()
    assert len(india_jobs) >= 2
    assert all(j["region"] == "India" for j in india_jobs)

    # 2. Test fresher_only filter
    res_fresher = client.get("/api/jobs?fresher_only=true")
    assert res_fresher.status_code == 200
    fresher_jobs = res_fresher.json()
    assert len(fresher_jobs) >= 1
    assert any(j["id"] == "test-cred-fresher-002" for j in fresher_jobs)

    # 3. Test Subscription Status
    sub_res = client.get("/api/subscription/status")
    assert sub_res.status_code == 200
    sub_data = sub_res.json()
    assert "tier" in sub_data
    assert "daily_limit" in sub_data
    assert "remaining_today" in sub_data

    # 4. Test Subscription Upgrade to PRO
    up_res = client.post("/api/subscription/upgrade?tier=PRO")
    assert up_res.status_code == 200
    assert up_res.json()["tier"] == "PRO"

    # 5. Test LazyApply batch apply
    batch_res = client.post("/api/copilot/auto-apply-batch?count=2")
    assert batch_res.status_code == 200
    batch_data = batch_res.json()
    assert batch_data["status"] == "SUCCESS"
    assert batch_data["applied_count"] > 0

    # Cleanup test records
    db = SessionLocal()
    db.query(JobModel).filter(JobModel.id.in_(["test-meesho-001", "test-cred-fresher-002", "test-global-003"])).delete()
    db.commit()
    db.close()
