import pytest
from unittest.mock import patch, MagicMock
from src.scrapers.base import BaseScraper
from src.scrapers.hasjob import HasjobScraper
from src.scrapers.lever import LeverCareerScraper
from src.scrapers.remotive import RemotiveScraper
from tests.fixtures import SAMPLE_HASJOB_ATOM_XML, SAMPLE_LEVER_MEESHO_JSON, SAMPLE_REMOTIVE_JSON

class ConcreteScraper(BaseScraper):
    def fetch_jobs(self, query=None, limit=10):
        return []

def test_base_scraper_skill_extraction():
    scraper = ConcreteScraper("TestScraper", "https://example.com")
    text = "Looking for an engineer proficient in Python, PyTorch, LangChain, and Docker with SQL expertise."
    skills = scraper.extract_skills(text)
    
    assert "python" in skills
    assert "pytorch" in skills
    assert "langchain" in skills
    assert "docker" in skills
    assert "sql" in skills

def test_base_scraper_fresher_and_seniority_detection():
    scraper = ConcreteScraper("TestScraper", "https://example.com")
    
    # Positive fresher cases
    lvl1, is_f1 = scraper.detect_fresher_and_level("Python Developer Intern", "6 month internship for freshers")
    assert is_f1 is True
    assert lvl1 == "Fresher / Entry"

    lvl2, is_f2 = scraper.detect_fresher_and_level("Graduate Engineer Trainee", "Entry level role for campus grads")
    assert is_f2 is True
    assert lvl2 == "Fresher / Entry"

    # Strict false positive prevention: "Senior Engineer mentoring freshers" must NOT be fresher!
    lvl3, is_f3 = scraper.detect_fresher_and_level("Senior Python Engineer", "You will mentor freshers and junior interns")
    assert is_f3 is False
    assert lvl3 == "Senior"

    lvl4, is_f4 = scraper.detect_fresher_and_level("Engineering Lead", "Leading a team of 10 developers")
    assert is_f4 is False
    assert lvl4 == "Lead"

def test_base_scraper_region_detection():
    scraper = ConcreteScraper("TestScraper", "https://example.com")

    # Indian city onsite
    geo1 = scraper.detect_region("Bengaluru, Karnataka, India")
    assert geo1["region"] == "India"
    assert geo1["city"] == "Bengaluru"
    assert geo1["country"] == "India"
    assert geo1["remote"] is False

    # Indian city remote
    geo2 = scraper.detect_region("Hyderabad (Remote India)")
    assert geo2["region"] == "India"
    assert geo2["city"] == "Hyderabad"
    assert geo2["remote"] is True

    # Global remote
    geo3 = scraper.detect_region("Remote / Worldwide")
    assert geo3["region"] == "Global"
    assert geo3["remote"] is True

def test_base_scraper_url_validation():
    scraper = ConcreteScraper("TestScraper", "https://example.com")

    assert scraper.is_valid_url("https://jobs.lever.co/meesho/123/apply") is True
    assert scraper.is_valid_url("https://hasjob.co/company/abc") is True
    assert scraper.is_valid_url("http://example.com/job") is False  # example.com is rejected as dummy
    assert scraper.is_valid_url("ftp://server/file") is False
    assert scraper.is_valid_url("") is False
    assert scraper.is_valid_url(None) is False

def test_hasjob_scraper_parsing_offline():
    scraper = HasjobScraper()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = SAMPLE_HASJOB_ATOM_XML.encode("utf-8")

    with patch.object(scraper, "get_with_retry", return_value=mock_resp):
        jobs = scraper.fetch_jobs(limit=10)
        assert len(jobs) == 2
        
        senior_job = jobs[0]
        assert senior_job.title == "Senior Backend Python Engineer"
        assert senior_job.region == "India"
        assert senior_job.city == "Bengaluru"
        assert "python" in senior_job.skills
        assert senior_job.apply_url.startswith("https://hasjob.co/")

        intern_job = jobs[1]
        assert intern_job.title == "Machine Learning Intern / Fresher"
        assert intern_job.is_fresher is True
        assert intern_job.region == "India"
        assert intern_job.city == "Hyderabad"

def test_lever_career_scraper_parsing_offline():
    scraper = LeverCareerScraper("meesho", "Meesho")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_LEVER_MEESHO_JSON

    with patch.object(scraper, "get_with_retry", return_value=mock_resp):
        jobs = scraper.fetch_jobs(limit=10)
        assert len(jobs) == 2

        sde = jobs[0]
        assert sde.company == "Meesho"
        assert "Software Development Engineer" in sde.title
        assert sde.region == "India"
        assert sde.city == "Bengaluru"
        assert sde.apply_url == "https://jobs.lever.co/meesho/7d9af9b5-c1c7-48ec-bbb5-9b25e49f6596/apply"

        trainee = jobs[1]
        assert trainee.is_fresher is True
        assert trainee.company == "Meesho"

def test_remotive_scraper_parsing_offline():
    scraper = RemotiveScraper()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = SAMPLE_REMOTIVE_JSON

    with patch.object(scraper, "get_with_retry", return_value=mock_resp):
        jobs = scraper.fetch_jobs(limit=10)
        assert len(jobs) == 1
        j = jobs[0]
        assert j.company == "Lemon.io"
        assert "python" in j.skills
        assert j.remote is True
        assert j.apply_url.startswith("https://remotive.com/")
