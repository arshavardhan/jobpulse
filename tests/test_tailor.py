import pytest
from src.agents import AnalystAgent, TailorAgent
from src.models.job import JobPosting, UserProfile

@pytest.fixture
def tailor():
    return TailorAgent()

@pytest.fixture
def analyst():
    return AnalystAgent()

def test_tailored_package_generation(tailor, analyst):
    profile = UserProfile(
        full_name="Alex Chen",
        email="alex@example.com",
        skills=["python", "langchain", "docker", "fastapi"],
        years_of_experience=3.0
    )
    job = JobPosting(
        title="Agentic AI Developer",
        company="CognitiveLab",
        location="Remote",
        description="Build multi-agent frameworks using Python, LangChain, and FastAPI.",
        skills_required=["python", "langchain", "fastapi", "aws"],
        url="https://example.com/job/agentic"
    )
    match = analyst.calculate_match(profile, job)
    pkg = tailor.generate_tailored_package(profile, job, match)

    assert "CognitiveLab" in pkg.cover_letter
    assert "Alex Chen" in pkg.cover_letter
    assert len(pkg.resume_bullet_recommendations) >= 3
    assert len(pkg.interview_prep_qa) >= 3
    assert all("question" in item for item in pkg.interview_prep_qa)
    assert all("talking_points" in item for item in pkg.interview_prep_qa)
