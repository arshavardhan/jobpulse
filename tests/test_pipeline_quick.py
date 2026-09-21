from src.agents import AnalystAgent, TailorAgent, MarketIntelligenceAgent, TrackerAgent
from src.models.job import JobPosting
from src.database import init_db, SessionLocal

def test_pipeline_quick():
    init_db()
    db = SessionLocal()

    analyst = AnalystAgent()
    profile = analyst.parse_resume_file("data/demo/sample_resume_aiml.txt")
    assert profile.full_name == "Alex Chen"
    assert len(profile.skills) >= 10

    # Build genuine JobPosting objects
    jobs = [
        JobPosting(
            id="test-job-sde",
            source="lever",
            source_name="Meesho Careers (Lever)",
            title="Senior AI/ML & Python Platform Engineer",
            company="Meesho",
            location="Bengaluru, Karnataka, India",
            city="Bengaluru",
            country="India",
            region="India",
            remote=False,
            skills=["python", "pytorch", "fastapi", "docker", "sql", "machine learning"],
            description="Developing high-throughput inference APIs with Python and PyTorch.",
            apply_url="https://jobs.lever.co/meesho/test-job-sde/apply",
            url="https://jobs.lever.co/meesho/test-job-sde/apply"
        ),
        JobPosting(
            id="test-job-fresher",
            source="hasjob",
            source_name="Hasjob.co",
            title="Data Science Intern (Fresher)",
            company="DataCraft",
            location="Hyderabad, Telangana, India",
            city="Hyderabad",
            country="India",
            region="India",
            is_fresher=True,
            experience_level="Fresher / Entry",
            remote=True,
            skills=["python", "sql", "pandas", "numpy"],
            description="Internship opportunity for fresh graduates in data analytics.",
            apply_url="https://hasjob.co/datacraft/intern-1",
            url="https://hasjob.co/datacraft/intern-1"
        )
    ]
    assert len(jobs) > 0

    matches = analyst.rank_jobs(profile, jobs)
    assert len(matches) == len(jobs)
    assert matches[0].match_score > 60

    tailor = TailorAgent()
    package = tailor.generate_tailored_package(profile, jobs[0], matches[0])
    assert len(package.cover_letter) > 100
    assert len(package.interview_prep_qa) >= 3

    market = MarketIntelligenceAgent()
    analytics = market.analyze_market(jobs, profile)
    assert analytics["total_jobs"] == len(jobs)
    assert analytics["candidate_market_fit"] is not None

    db.close()
    print("ALL CORE PIPELINE CHECKS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_pipeline_quick()
