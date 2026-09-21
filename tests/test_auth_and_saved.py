import pytest
import uuid
from fastapi.testclient import TestClient
from main import app
from src.database.db import init_db

@pytest.fixture(scope="module")
def client():
    init_db()
    with TestClient(app) as client:
        yield client

def test_auth_registration_and_login(client):
    test_email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    test_password = "SecretPassword123"

    # 1. Register new user
    reg_resp = client.post("/api/auth/register", json={
        "email": test_email,
        "password": test_password,
        "full_name": "Deepika Sharma",
        "preferred_role": "Full Stack Engineer",
        "preferred_location": "Bengaluru, India"
    })
    assert reg_resp.status_code == 200, reg_resp.text
    data = reg_resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == test_email
    assert data["user"]["full_name"] == "Deepika Sharma"
    token = data["access_token"]

    # 2. Duplicate registration fails
    dup_resp = client.post("/api/auth/register", json={
        "email": test_email,
        "password": test_password,
        "full_name": "Deepika Sharma"
    })
    assert dup_resp.status_code == 400

    # 3. Login with correct password
    login_resp = client.post("/api/auth/login", json={
        "email": test_email,
        "password": test_password
    })
    assert login_resp.status_code == 200
    assert "access_token" in login_resp.json()

    # 4. Login with incorrect password
    bad_login = client.post("/api/auth/login", json={
        "email": test_email,
        "password": "WrongPassword"
    })
    assert bad_login.status_code == 401

    # 5. Access protected /auth/me
    headers = {"Authorization": f"Bearer {token}"}
    me_resp = client.get("/api/auth/me", headers=headers)
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["email"] == test_email
    assert me_data["full_name"] == "Deepika Sharma"

    # 6. Update profile via /auth/profile
    update_resp = client.put("/api/auth/profile", headers=headers, json={
        "preferred_role": "Staff AI Engineer",
        "skills": ["Python", "PyTorch", "FastAPI", "PostgreSQL", "Docker"],
        "years_of_experience": 4.5,
        "summary": "AI researcher specializing in LLM application architecture."
    })
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["preferred_role"] == "Staff AI Engineer"
    assert "PyTorch" in updated["skills"]
    assert updated["years_of_experience"] == 4.5

def test_saved_jobs_workflow(client):
    test_email = f"saver_{uuid.uuid4().hex[:8]}@example.com"
    reg_resp = client.post("/api/auth/register", json={
        "email": test_email,
        "password": "SaverPassword123",
        "full_name": "Job Saver User"
    })
    token = reg_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch a live job from DB
    jobs_resp = client.get("/api/jobs?limit=5", headers=headers)
    assert jobs_resp.status_code == 200
    jobs = jobs_resp.json()
    assert len(jobs) > 0
    target_job = jobs[0]
    target_id = target_job["id"]

    # 1. Save the job
    save_resp = client.post(f"/api/saved-jobs/{target_id}", headers=headers)
    assert save_resp.status_code == 200
    assert save_resp.json()["is_saved"] is True

    # 2. Get saved jobs
    saved_list_resp = client.get("/api/saved-jobs", headers=headers)
    assert saved_list_resp.status_code == 200
    saved_list = saved_list_resp.json()
    assert len(saved_list) >= 1
    assert any(item["job_id"] == target_id for item in saved_list)

    # 3. Check /jobs/{id} returns is_saved=True
    detail_resp = client.get(f"/api/jobs/{target_id}", headers=headers)
    assert detail_resp.status_code == 200
    assert detail_resp.json()["is_saved"] is True

    # 4. Unsave job
    unsave_resp = client.delete(f"/api/saved-jobs/{target_id}", headers=headers)
    assert unsave_resp.status_code == 200
    assert unsave_resp.json()["is_saved"] is False

    # 5. Verify no longer in saved list
    after_unsave = client.get("/api/saved-jobs", headers=headers).json()
    assert not any(item["job_id"] == target_id for item in after_unsave)

def test_ats_checker_endpoint(client):
    # Fetch a job to test ATS checking against real job description
    jobs_resp = client.get("/api/jobs?limit=1")
    job = jobs_resp.json()[0]

    ats_resp = client.post("/api/ats/check", json={
        "job_id": job["id"],
        "resume_text": "Worked on backend microservices. Responsible for writing code in python and fixing bugs.",
        "target_role": job["title"]
    })
    assert ats_resp.status_code == 200
    result = ats_resp.json()
    assert "overall_score" in result
    assert "keyword_match_score" in result
    assert "detected_errors" in result
    assert "tailored_resume_bullet_fixes" in result
    assert len(result["detected_errors"]) > 0
    assert len(result["tailored_resume_bullet_fixes"]) > 0
