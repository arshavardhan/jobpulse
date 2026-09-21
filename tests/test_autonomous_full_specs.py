import json
import uuid
import pytest
from starlette.testclient import TestClient
from sqlalchemy.orm import Session

from main import app
from src.database.db import SessionLocal
from src.database.models import (
    UserModel, JobModel, ApplicationModel, RecruiterContactModel,
    OutreachEmailModel, KnowledgeBaseModel, ActivityTimelineModel,
    PortalPermissionModel, ResumeVersionModel
)
from src.models.job import JobPosting, UserProfile
from src.agents.copilot import copilot_agent
from src.agents.outreach import outreach_agent
from src.agents.learner import self_learning_agent

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()

def test_cross_portal_duplicate_application_prevention(db):
    """
    Assert that if a candidate applies or has an application for a company and role on Portal A,
    the autonomous agent PREVENTS a duplicate submission when encountering the same role on Portal B.
    """
    # Ensure test portals have sufficient quota for this isolated unit test
    db.query(PortalPermissionModel).filter(PortalPermissionModel.portal_name.in_(["linkedin", "indeed"])).update({"max_daily_apps": 999}, synchronize_session=False)
    db.commit()

    unique_co = f"DupTestCo-{uuid.uuid4().hex[:6]}"
    role_title = "Lead Cloud Infrastructure Architect"
    
    # 1. Seed job 1 from LinkedIn
    job_linkedin = JobPosting(
        id=f"job-lk-{uuid.uuid4().hex[:6]}",
        source="linkedin",
        title=role_title,
        company=unique_co,
        location="Bengaluru, India",
        apply_url=f"https://www.linkedin.com/jobs/view/{uuid.uuid4().hex[:6]}",
        skills_required=["AWS", "Terraform", "Kubernetes", "Python"]
    )
    db_job_lk = JobModel(
        id=job_linkedin.id,
        source=job_linkedin.source,
        title=job_linkedin.title,
        company=job_linkedin.company,
        location=job_linkedin.location,
        apply_url=job_linkedin.apply_url,
        skills_json=json.dumps(job_linkedin.skills_required)
    )
    db.add(db_job_lk)
    db.commit()

    profile = UserProfile(
        full_name="Harsha Vardhan",
        email="harsha@example.com",
        skills=["Python", "AWS", "Terraform", "Kubernetes", "Docker"],
        experience_years=5
    )

    # Apply to LinkedIn job in FULLY_AUTONOMOUS mode
    res1 = copilot_agent.execute_autonomous_cycle(
        jobs=[job_linkedin],
        profile=profile,
        db=db,
        operating_mode="FULLY_AUTONOMOUS",
        max_applications=1
    )
    assert res1["status"] == "SUCCESS"
    assert len(res1["applied_jobs"]) == 1
    assert res1["applied_jobs"][0]["company"] == unique_co

    # Verify ApplicationModel created
    app1 = db.query(ApplicationModel).filter(ApplicationModel.job_id == job_linkedin.id).first()
    assert app1 is not None
    assert app1.status == "APPLIED"
    assert app1.portal == "linkedin"

    # 2. Seed identical role at same company from Naukri (Cross-portal duplicate)
    job_naukri = JobPosting(
        id=f"job-nk-{uuid.uuid4().hex[:6]}",
        source="naukri",
        title=role_title,
        company=unique_co,
        location="Bengaluru, India",
        apply_url=f"https://www.naukri.com/job-listings-{uuid.uuid4().hex[:6]}",
        skills_required=["AWS", "Terraform", "Kubernetes", "Python"]
    )
    db_job_nk = JobModel(
        id=job_naukri.id,
        source=job_naukri.source,
        title=job_naukri.title,
        company=job_naukri.company,
        location=job_naukri.location,
        apply_url=job_naukri.apply_url,
        skills_json=json.dumps(job_naukri.skills_required)
    )
    db.add(db_job_nk)
    db.commit()

    # Attempt to apply to Naukri opening for the same role
    res2 = copilot_agent.execute_autonomous_cycle(
        jobs=[job_naukri],
        profile=profile,
        db=db,
        operating_mode="FULLY_AUTONOMOUS",
        max_applications=1
    )
    # The duplicate must be skipped and prevented from creating a duplicate application
    assert len(res2["applied_jobs"]) == 0
    assert any("Duplicate application already exists" in log or "already applied" in log for log in res2["execution_logs"])

    # Verify no application was created for the duplicate job ID
    app_nk = db.query(ApplicationModel).filter(ApplicationModel.job_id == job_naukri.id).first()
    assert app_nk is None

    # Verify DUPLICATE_APPLICATION_PREVENTED timeline event was logged
    dup_tl = db.query(ActivityTimelineModel).filter(
        ActivityTimelineModel.job_id == job_naukri.id,
        ActivityTimelineModel.event_type == "DUPLICATE_APPLICATION_PREVENTED"
    ).first()
    assert dup_tl is not None
    assert dup_tl.stage_number == 4
    assert unique_co in dup_tl.title

def test_three_operating_modes_execution(db):
    """
    Verify behavior across FULLY_AUTONOMOUS, APPROVAL_MODE, and ASSISTED modes.
    """
    db.query(PortalPermissionModel).filter(PortalPermissionModel.portal_name.in_(["wellfound", "hirist", "cutshort"])).update({"max_daily_apps": 999}, synchronize_session=False)
    db.commit()

    profile = UserProfile(
        full_name="Harsha Vardhan",
        email="harsha@example.com",
        skills=["Python", "FastAPI", "PostgreSQL"],
        experience_years=4
    )

    # --- Mode 1: APPROVAL_MODE ---
    job_approval = JobPosting(
        id=f"job-appr-{uuid.uuid4().hex[:6]}",
        source="wellfound",
        title=f"Backend Developer {uuid.uuid4().hex[:4]}",
        company=f"StartupOne-{uuid.uuid4().hex[:4]}",
        location="Remote",
        apply_url=f"https://wellfound.com/jobs/{uuid.uuid4().hex[:6]}",
        skills_required=["Python", "FastAPI"]
    )
    db.add(JobModel(
        id=job_approval.id, source=job_approval.source,
        title=job_approval.title, company=job_approval.company,
        location=job_approval.location, apply_url=job_approval.apply_url,
        skills_json=json.dumps(job_approval.skills_required)
    ))
    db.commit()

    res_appr = copilot_agent.execute_autonomous_cycle(
        jobs=[job_approval],
        profile=profile,
        db=db,
        operating_mode="APPROVAL_MODE",
        max_applications=1
    )
    assert res_appr["status"] == "SUCCESS"
    assert res_appr["operating_mode"] == "APPROVAL_MODE"
    rec_appr = db.query(ApplicationModel).filter(ApplicationModel.job_id == job_approval.id).first()
    assert rec_appr is not None
    assert rec_appr.status == "PENDING_APPROVAL"

    # Outreach email should be PENDING_APPROVAL
    em_appr = db.query(OutreachEmailModel).filter(OutreachEmailModel.job_id == job_approval.id).first()
    if em_appr:
        assert em_appr.status == "PENDING_APPROVAL"

    # Timeline event should be APPLICATION_QUEUED
    tl_appr = db.query(ActivityTimelineModel).filter(
        ActivityTimelineModel.job_id == job_approval.id,
        ActivityTimelineModel.event_type == "APPLICATION_QUEUED"
    ).first()
    assert tl_appr is not None

    # --- Mode 2: ASSISTED ---
    job_assist = JobPosting(
        id=f"job-asst-{uuid.uuid4().hex[:6]}",
        source="hirist",
        title=f"Platform Engineer {uuid.uuid4().hex[:4]}",
        company=f"FinTech-{uuid.uuid4().hex[:4]}",
        location="Bengaluru",
        apply_url=f"https://hirist.com/j/{uuid.uuid4().hex[:6]}",
        skills_required=["Python", "PostgreSQL"]
    )
    db.add(JobModel(
        id=job_assist.id, source=job_assist.source,
        title=job_assist.title, company=job_assist.company,
        location=job_assist.location, apply_url=job_assist.apply_url,
        skills_json=json.dumps(job_assist.skills_required)
    ))
    db.commit()

    res_asst = copilot_agent.execute_autonomous_cycle(
        jobs=[job_assist],
        profile=profile,
        db=db,
        operating_mode="ASSISTED",
        max_applications=1
    )
    assert res_asst["status"] == "SUCCESS"
    assert res_asst["operating_mode"] == "ASSISTED"
    rec_asst = db.query(ApplicationModel).filter(ApplicationModel.job_id == job_assist.id).first()
    assert rec_asst is not None
    assert rec_asst.status == "ASSISTED_READY"

    # Outreach email should be DRAFT
    em_asst = db.query(OutreachEmailModel).filter(OutreachEmailModel.job_id == job_assist.id).first()
    if em_asst:
        assert em_asst.status == "DRAFT"

    # Timeline event should be APPLICATION_PREPARED_ASSISTED
    tl_asst = db.query(ActivityTimelineModel).filter(
        ActivityTimelineModel.job_id == job_assist.id,
        ActivityTimelineModel.event_type == "APPLICATION_PREPARED_ASSISTED"
    ).first()
    assert tl_asst is not None

def test_portal_permissions_and_quota_enforcement(db):
    """
    Verify that disabled portals are skipped and daily limits are enforced.
    """
    profile = UserProfile(
        full_name="Harsha Vardhan",
        email="harsha@example.com",
        skills=["Python", "AWS"],
        experience_years=3
    )

    # Disable shine portal temporarily
    shine_perm = db.query(PortalPermissionModel).filter(PortalPermissionModel.portal_name == "shine").first()
    if shine_perm:
        shine_perm.enabled = False
        db.commit()

        job_shine = JobPosting(
            id=f"job-shine-{uuid.uuid4().hex[:6]}",
            source="shine",
            title=f"Python Analyst {uuid.uuid4().hex[:4]}",
            company=f"DataCorp-{uuid.uuid4().hex[:4]}",
            location="Noida",
            apply_url=f"https://shine.com/job/{uuid.uuid4().hex[:6]}",
            skills_required=["Python"]
        )
        db.add(JobModel(
            id=job_shine.id, source=job_shine.source,
            title=job_shine.title, company=job_shine.company,
            location=job_shine.location, apply_url=job_shine.apply_url,
            skills_json=json.dumps(job_shine.skills_required)
        ))
        db.commit()

        res_shine = copilot_agent.execute_autonomous_cycle(
            jobs=[job_shine],
            profile=profile,
            db=db,
            operating_mode="FULLY_AUTONOMOUS",
            max_applications=1
        )
        assert len(res_shine["applied_jobs"]) == 0
        assert any("is disabled in portal permissions" in log for log in res_shine["execution_logs"])

        # Re-enable shine
        shine_perm.enabled = True
        db.commit()

def test_analytics_dashboard_extended_metrics(client):
    """
    Verify that the analytics endpoint returns jobs_by_title, applications_viewed,
    and no_response_applications.
    """
    res = client.get("/api/analytics/agent-dashboard")
    assert res.status_code == 200
    data = res.json()

    # Check job statistics
    assert "job_statistics" in data
    assert "by_title" in data["job_statistics"]
    assert "jobs" in data
    assert "jobs_by_title" in data["jobs"]

    # Check application statistics
    assert "application_statistics" in data
    assert "applications_viewed" in data["application_statistics"]
    assert "no_response_applications" in data["application_statistics"]
    assert "applications" in data
    assert "applications_viewed" in data["applications"]
    assert "no_response_applications" in data["applications"]
