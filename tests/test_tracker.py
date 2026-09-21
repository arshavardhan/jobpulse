import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import Base, JobModel
from src.agents import TrackerAgent
from src.models.application import ApplicationCreate, ApplicationUpdate, ApplicationStatus

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Add sample job
    job = JobModel(
        id="job-test-123",
        title="Software Engineer",
        company="Tech Co",
        location="Remote",
        description="Engineering role",
        url="http://test.com"
    )
    session.add(job)
    session.commit()

    yield session
    session.close()

def test_tracker_lifecycle(db_session):
    tracker = TrackerAgent()

    # 1. Add to tracker
    create_payload = ApplicationCreate(
        job_id="job-test-123",
        status=ApplicationStatus.SHORTLISTED,
        notes="Applied via website"
    )
    record = tracker.add_to_tracker(db_session, create_payload)
    assert record.job_id == "job-test-123"
    assert record.status == ApplicationStatus.SHORTLISTED

    # 2. Update status to INTERVIEWING
    update_payload = ApplicationUpdate(
        status=ApplicationStatus.INTERVIEWING,
        interview_date="2026-10-15"
    )
    updated = tracker.update_application(db_session, record.id, update_payload)
    assert updated.status == ApplicationStatus.INTERVIEWING
    assert updated.interview_date == "2026-10-15"

    # 3. Funnel metrics
    funnel = tracker.get_funnel_metrics(db_session)
    assert funnel["total_tracked"] == 1
    assert funnel["counts"]["INTERVIEWING"] == 1

    # 4. Delete application
    deleted = tracker.delete_application(db_session, record.id)
    assert deleted is True
    assert len(tracker.list_applications(db_session)) == 0
