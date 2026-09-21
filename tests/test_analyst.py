import pytest
from src.agents import AnalystAgent
from src.models.job import JobPosting, UserProfile

@pytest.fixture
def analyst():
    return AnalystAgent()

@pytest.fixture
def sample_profile():
    return UserProfile(
        full_name="Jane Doe",
        email="jane.doe@example.com",
        skills=["python", "pytorch", "langchain", "sql", "fastapi", "docker"],
        years_of_experience=3.0,
        summary="AI engineer building LLM applications and agentic systems.",
        target_roles=["AI/ML Engineer"]
    )

@pytest.fixture
def sample_job():
    return JobPosting(
        title="AI Engineer",
        company="NeuroTech",
        location="Remote",
        description="We need an AI Engineer experienced with Python, PyTorch, and LangChain to deploy LLMs with FastAPI.",
        skills_required=["python", "pytorch", "langchain", "fastapi", "kubernetes"],
        experience_level="Mid",
        url="https://example.com/job/1"
    )

def test_resume_text_extraction(analyst):
    text = """
    John Smith
    john.smith@gmail.com
    5 years of experience in data science.
    Skills: Python, SQL, pandas, numpy, scikit-learn, Tableau.
    """
    profile = analyst.extract_profile_from_text(text)
    assert profile.full_name == "John Smith"
    assert profile.email == "john.smith@gmail.com"
    assert profile.years_of_experience == 5.0
    assert "python" in profile.skills
    assert "sql" in profile.skills
    assert "pandas" in profile.skills

def test_calculate_match(analyst, sample_profile, sample_job):
    match = analyst.calculate_match(sample_profile, sample_job)
    assert match.match_score > 60.0
    assert "python" in match.matching_skills
    assert "pytorch" in match.matching_skills
    assert "kubernetes" in match.missing_skills
    assert len(match.rationale) > 10
    assert len(match.suggested_pitch) > 10

def test_rank_jobs(analyst, sample_profile, sample_job):
    unrelated_job = JobPosting(
        title="Sales Executive",
        company="CorpSales",
        location="New York",
        description="B2B cold calling, sales pipeline, quota management.",
        skills_required=["sales", "cold calling", "crm"],
        url="https://example.com/job/2"
    )
    ranked = analyst.rank_jobs(sample_profile, [unrelated_job, sample_job])
    assert len(ranked) == 2
    assert ranked[0].job_id == sample_job.id
    assert ranked[0].match_score > ranked[1].match_score
