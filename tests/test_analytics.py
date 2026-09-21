import pytest
from src.agents import MarketIntelligenceAgent
from src.models.job import JobPosting, UserProfile

@pytest.fixture
def sample_jobs():
    return [
        JobPosting(
            title="Senior AI Engineer",
            company="AI Corp",
            salary_min=140000,
            salary_max=180000,
            skills_required=["python", "pytorch", "langchain"],
            experience_level="Senior",
            remote_type="Remote",
            url="http://example.com/1",
            description="ML engineer role"
        ),
        JobPosting(
            title="Junior Data Analyst",
            company="Analytics Hub",
            salary_min=60000,
            salary_max=80000,
            skills_required=["python", "sql", "pandas"],
            experience_level="Entry",
            remote_type="Hybrid",
            url="http://example.com/2",
            description="Data analysis role"
        )
    ]

def test_market_analysis(sample_jobs):
    agent = MarketIntelligenceAgent()
    profile = UserProfile(skills=["python", "sql"])
    
    analytics = agent.analyze_market(sample_jobs, profile)
    assert analytics["total_jobs"] == 2
    assert analytics["salary_metrics"]["median"] == 115000.0  # (160k + 70k) / 2
    assert analytics["workplace_distribution"]["Remote"] == 1
    assert analytics["workplace_distribution"]["Hybrid"] == 1
    assert analytics["candidate_market_fit"] is not None
    assert analytics["candidate_market_fit"]["market_coverage_pct"] > 0
