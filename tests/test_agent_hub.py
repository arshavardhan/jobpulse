import pytest
from starlette.testclient import TestClient
from src.database.db import get_db, SessionLocal
from src.database.models import (
    UserModel, JobModel, ApplicationModel, RecruiterContactModel,
    OutreachEmailModel, KnowledgeBaseModel, ActivityTimelineModel
)
from main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_agent_preferences_lifecycle(client):
    """Verify getting and updating candidate preferences and operating mode."""
    # 1. GET preferences
    res = client.get("/api/agent/preferences")
    assert res.status_code == 200
    data = res.json()
    assert "preferences" in data
    assert "operating_mode" in data["preferences"]

    # 2. POST preferences update
    payload = {
        "target_job_titles": ["Staff Backend Engineer", "Python Architect", "Lead Developer"],
        "preferred_locations": ["Bengaluru", "Remote", "Hyderabad"],
        "min_salary": 2500000.0,
        "salary_currency": "INR",
        "work_preference": "REMOTE",
        "experience_level": "SENIOR",
        "operating_mode": "APPROVAL_MODE",
        "max_daily_applications": 30,
        "max_portal_applications": 12,
        "master_resume_text": "Experienced Python Engineer specializing in FastAPI, SQLAlchemy, Distributed Systems."
    }
    update_res = client.post("/api/agent/preferences", json=payload)
    assert update_res.status_code == 200
    updated = update_res.json()["preferences"]
    assert updated["operating_mode"] == "APPROVAL_MODE"
    assert updated["target_job_titles"] == ["Staff Backend Engineer", "Python Architect", "Lead Developer"]
    assert updated["max_daily_applications"] == 30
    assert updated["max_portal_applications"] == 12

    # Switch back to FULLY_AUTONOMOUS for testing
    client.post("/api/agent/preferences", json={"operating_mode": "FULLY_AUTONOMOUS"})

def test_portal_permissions_management(client):
    """Verify reading and toggling portal permissions and daily limits."""
    # 1. GET portals
    res = client.get("/api/agent/portals")
    assert res.status_code == 200
    portals = res.json()
    assert isinstance(portals, list)
    assert len(portals) >= 15

    portal_names = [p["portal_name"].lower() for p in portals]
    assert "linkedin" in portal_names
    assert "naukri" in portal_names
    assert "wellfound" in portal_names

    # 2. PUT toggle portal
    target_portal = portals[0]["portal_name"]
    curr_enabled = portals[0]["enabled"]
    new_enabled = not curr_enabled

    put_res = client.put(f"/api/agent/portals/{target_portal}", json={"enabled": new_enabled, "max_daily_applications": 15})
    assert put_res.status_code == 200
    res_data = put_res.json()
    assert res_data["portal_name"] == target_portal
    assert res_data["enabled"] == new_enabled
    assert res_data["max_daily_applications"] == 15

    # Revert back
    client.put(f"/api/agent/portals/{target_portal}", json={"enabled": curr_enabled})

def test_latex_resume_synthesis(client):
    """Verify compile-ready ATS LaTeX resume generation."""
    # Find active job
    db = SessionLocal()
    job = db.query(JobModel).first()
    db.close()
    assert job is not None

    res = client.post("/api/resumes/generate-latex", json={"job_id": job.id})
    assert res.status_code == 200
    data = res.json()
    assert "latex_code" in data
    assert "\\documentclass" in data["latex_code"]
    assert "\\begin{document}" in data["latex_code"]
    assert "\\end{document}" in data["latex_code"]
    assert "overleaf_url" in data
    assert "application_id" in data

    app_id = data["application_id"]

    # Test GET latex by application_id
    get_res = client.get(f"/api/resumes/{app_id}/latex")
    assert get_res.status_code == 200
    assert get_res.json()["latex_code"] == data["latex_code"]

    # Test download-tex endpoint
    dl_res = client.get(f"/api/resumes/{app_id}/download-tex")
    assert dl_res.status_code == 200
    assert "text/x-tex" in dl_res.headers.get("content-type", "")
    assert b"\\documentclass" in dl_res.content

def test_recruiter_outreach_and_simulation(client):
    """Verify HR recruiter discovery, cold email outreach, and 7-class reply simulation."""
    # 1. Contacts discovery
    c_res = client.get("/api/outreach/contacts")
    assert c_res.status_code == 200
    contacts = c_res.json()
    assert isinstance(contacts, list)

    # 2. Cold emails log
    e_res = client.get("/api/outreach/emails")
    assert e_res.status_code == 200
    emails = e_res.json()
    assert isinstance(emails, list)

    # 3. Simulate Inbound Recruiter Response
    db = SessionLocal()
    email_rec = db.query(OutreachEmailModel).first()
    if not email_rec:
        # Create a test email record
        email_rec = OutreachEmailModel(
            contact_id="test-c-001",
            job_id="test-j-001",
            recipient_email="recruiter@innovate.co",
            recipient_name="Alex Smith",
            company="Innovate Labs",
            subject="Application for Senior Backend Engineer",
            body_text="Dear Alex, I'm reaching out regarding your Senior Backend opening...",
            status="SENT"
        )
        db.add(email_rec)
        db.commit()
        db.refresh(email_rec)
    target_id = email_rec.id
    db.close()

    # Simulate Interview Invitation
    sim_res = client.post("/api/outreach/simulate-response", json={
        "email_id": target_id,
        "response_body": "Hi there! We would love to invite you for a 30-minute screening call this Wednesday."
    })
    assert sim_res.status_code == 200
    sim_data = sim_res.json()
    assert sim_data["category"] == "INTERVIEW"

    # Simulate Rejection
    sim_rej = client.post("/api/outreach/simulate-response", json={
        "email_id": target_id,
        "response_body": "Thank you for reaching out. We have moved forward with other applicants."
    })
    assert sim_rej.status_code == 200
    assert sim_rej.json()["category"] == "REJECTION"

    # Test Follow-up Cadence Trigger
    fu_res = client.post("/api/outreach/trigger-followups")
    assert fu_res.status_code == 200
    assert "followups_sent" in fu_res.json()

def test_self_learning_and_knowledge_base(client):
    """Verify Candidate Knowledge Base, question confirmation, and learning feedback metrics."""
    # 1. Candidate KB
    kb_res = client.get("/api/learner/knowledge-base")
    assert kb_res.status_code == 200
    facts = kb_res.json()
    assert len(facts) >= 3
    assert any("Notice Period" in (f.get("question") or f.get("question_pattern") or "") for f in facts)

    # Add verified fact
    add_res = client.post("/api/learner/knowledge-base", json={
        "question": "Willingness to travel",
        "answer": "Up to 15% domestic and international travel",
        "category": "career"
    })
    assert add_res.status_code == 200
    assert add_res.json()["verified_answer"] == "Up to 15% domestic and international travel"

    # 2. Learning Insights
    in_res = client.get("/api/learner/insights")
    assert in_res.status_code == 200
    insights = in_res.json()
    assert "current_weights" in insights
    assert "top_performing_skills" in insights

    # 3. Pending Questions
    q_res = client.get("/api/learner/pending-questions")
    assert q_res.status_code == 200
    assert isinstance(q_res.json(), list)

def test_autonomous_cycle_and_9_stage_timeline(client):
    """Verify autonomous cycle execution, approval queue, and 9-stage timeline events."""
    # Reset applications so the cycle always finds unapplied jobs
    db = SessionLocal()
    db.query(ApplicationModel).delete()
    db.commit()
    db.close()

    # 1. Run Autonomous Cycle with limit=2
    cycle_res = client.post("/api/agent/run-cycle?limit=2")
    assert cycle_res.status_code == 200
    c_data = cycle_res.json()
    assert c_data["status"] in ["SUCCESS", "NO_JOBS"]
    assert c_data["jobs_processed"] >= 0


    # 2. Activity Timeline
    tl_res = client.get("/api/agent/timeline?limit=30")
    assert tl_res.status_code == 200
    events = tl_res.json()
    assert len(events) > 0
    stages = [e["stage"] for e in events]
    # Check that core stages are recorded
    assert any(s in stages for s in ["JOB_FOUND", "RESUME_CUSTOMIZED", "APPLICATION_SUBMITTED", "HR_CONTACT_FOUND"])

    # 3. Approvals endpoint
    appr_res = client.get("/api/agent/approvals")
    assert appr_res.status_code == 200
    appr_data = appr_res.json()
    assert "pending_applications" in appr_data
    assert "pending_emails" in appr_data

def test_centralized_agent_dashboard(client):
    """Verify aggregated metrics for centralized agent dashboard."""
    res = client.get("/api/analytics/agent-dashboard")
    assert res.status_code == 200
    data = res.json()

    assert "jobs" in data
    assert data["jobs"]["total_live_jobs"] >= 1000
    assert "applications" in data
    assert "outreach" in data
    assert "limits" in data
    assert "portals" in data
    assert "sentiment_breakdown" in data
    assert "learning_insights" in data
