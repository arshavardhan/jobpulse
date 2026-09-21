import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from main import app
from src.database.db import SessionLocal
from src.database.models import JobModel, ApplicationModel

@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client

def test_auto_apply_bot_batch_execution(client):
    """Verify autonomous auto-apply bot batches applications and records them in the database."""
    res = client.post("/api/copilot/auto-apply-batch?count=3")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ["SUCCESS", "NO_JOBS"]
    assert "execution_logs" in data
    assert isinstance(data["execution_logs"], list)
    assert len(data["execution_logs"]) > 0

    if data["status"] == "SUCCESS":
        assert data["applied_count"] > 0
        assert len(data["applied_jobs"]) == data["applied_count"]
        first_applied = data["applied_jobs"][0]
        assert "job_id" in first_applied
        assert "match_score" in first_applied
        assert first_applied["status"] == "APPLIED_SUCCESSFULLY"

        # Check DB persistence
        db = SessionLocal()
        app_rec = db.query(ApplicationModel).filter(ApplicationModel.job_id == first_applied["job_id"]).first()
        assert app_rec is not None
        assert app_rec.status == "APPLIED"
        assert "JobPulse" in app_rec.notes
        db.close()

def test_auto_apply_run_alias(client):
    """Verify /api/auto-apply/run endpoint alias functions identically."""
    res = client.post("/api/auto-apply/run?count=2&min_match_score=50")
    assert res.status_code == 200
    data = res.json()
    assert "execution_logs" in data

def test_single_job_copilot_apply(client):
    """Verify 1-Click Copilot application on an individual job."""
    jobs_res = client.get("/api/jobs?limit=5")
    assert jobs_res.status_code == 200
    jobs = jobs_res.json()
    assert len(jobs) > 0
    target_job = jobs[0]

    # Apply via copilot
    apply_res = client.post(f"/api/copilot/apply-one/{target_job['id']}")
    assert apply_res.status_code == 200
    apply_data = apply_res.json()
    assert apply_data["status"] == "SUCCESS"
    assert apply_data["job_id"] == target_job["id"]
    assert "message" in apply_data

    # Verify DB record
    db = SessionLocal()
    rec = db.query(ApplicationModel).filter(ApplicationModel.job_id == target_job["id"]).first()
    assert rec is not None
    assert rec.status == "APPLIED"
    assert rec.tailored_cover_letter != ""
    db.close()

def test_no_vendor_names_in_index_html():
    """Verify zero occurrences of Lever, Greenhouse, or Ashby in user-facing index.html."""
    html_path = Path("src/frontend/index.html")
    assert html_path.exists()
    content = html_path.read_text(encoding="utf-8").lower()

    assert "lever" not in content, "Found 'lever' in index.html"
    assert "greenhouse" not in content, "Found 'greenhouse' in index.html"
    assert "ashby" not in content, "Found 'ashby' in index.html"
