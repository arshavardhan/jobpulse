import pytest
from fastapi.testclient import TestClient
from main import app

from src.database.db import init_db, SessionLocal
from src.database.models import JobModel

@pytest.fixture
def client():
    init_db()
    db = SessionLocal()
    if db.query(JobModel).filter(JobModel.id == "api-test-job-001").first() is None:
        test_job = JobModel(
            id="api-test-job-001",
            source="lever",
            source_name="Meesho Careers (Lever)",
            source_job_id="meesho-api-1",
            title="Senior Python Backend Developer",
            company="Meesho",
            location="Bengaluru, Karnataka, India",
            city="Bengaluru",
            country="India",
            region="India",
            remote=False,
            experience_level="Senior",
            salary_min=1800000.0,
            salary_max=2800000.0,
            salary_currency="INR",
            apply_url="https://jobs.lever.co/meesho/api-test/apply",
            source_url="https://jobs.lever.co/meesho/api-test",
            published_at="2026-09-18T10:00:00Z",
            description="Leading microservices with Python, FastAPI, and PostgreSQL.",
            status="ACTIVE",
            verification_status="VERIFIED"
        )
        test_job.skills_required = ["python", "fastapi", "postgresql", "docker"]
        db.add(test_job)
        db.commit()
    db.close()
    with TestClient(app) as client:
        yield client
    db = SessionLocal()
    db.query(JobModel).filter(JobModel.id == "api-test-job-001").delete()
    db.commit()
    db.close()


def test_api_system_status(client):
    response = client.get("/api/system/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "jobs_in_database" in data
    assert "llm_provider" in data

def test_api_get_profile(client):
    response = client.get("/api/profile")
    assert response.status_code == 200
    data = response.json()
    assert "full_name" in data
    assert "skills" in data

def test_api_list_jobs(client):
    response = client.get("/api/jobs")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_api_match_post(client):
    response = client.post("/api/match")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if data:
        assert "match_score" in data[0]
        assert "matching_skills" in data[0]

def test_api_match_get(client):
    response = client.get("/api/match")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if data:
        assert "match_score" in data[0]

def test_api_copilot_autofill(client):
    jobs = client.get("/api/jobs").json()
    assert len(jobs) > 0
    job_id = jobs[0]["id"]
    response = client.get(f"/api/copilot/autofill/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert "dossier" in data
    assert "screening_qa" in data
    assert "copilot_steps" in data
    assert "ats_scorecard" in data
    assert data["dossier"]["full_name"] != ""

def test_api_analytics(client):
    response = client.get("/api/analytics")
    assert response.status_code == 200
    data = response.json()
    assert "charts" in data
    assert "summary" in data

def test_api_applications_crud(client):
    # First get a job id
    jobs = client.get("/api/jobs").json()
    assert len(jobs) > 0
    job_id = jobs[0]["id"]

    # 1. Create tracker application
    create_res = client.post("/api/applications", json={
        "job_id": job_id,
        "status": "SHORTLISTED",
        "notes": "Testing API application"
    })
    assert create_res.status_code == 200
    app_data = create_res.json()
    app_id = app_data["id"]

    # 2. Update application
    update_res = client.put(f"/api/applications/{app_id}", json={
        "status": "APPLIED"
    })
    assert update_res.status_code == 200
    assert update_res.json()["status"] == "APPLIED"

    # 3. Funnel check
    funnel_res = client.get("/api/applications/funnel")
    assert funnel_res.status_code == 200
    assert funnel_res.json()["total_tracked"] >= 1

    # 4. Delete application
    del_res = client.delete(f"/api/applications/{app_id}")
    assert del_res.status_code == 200
