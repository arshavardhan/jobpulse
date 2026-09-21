import pytest
from fastapi.testclient import TestClient
from main import app
from src.scrapers.base import BaseScraper
from src.database.db import SessionLocal
from src.database.models import JobModel

client = TestClient(app)

class DummyScraper(BaseScraper):
    def fetch_jobs(self, query=None, limit=20):
        return []

def test_detect_role_domains():
    scraper = DummyScraper(name="TestScraper", base_url="https://example.com")
    
    # 1. Product
    assert scraper.detect_role_domain("Senior Product Manager", "Lead cross-functional roadmap") == "Product"
    assert scraper.detect_role_domain("Associate Technical PM", "PRD specs and user stories") == "Product"
    
    # 2. Design
    assert scraper.detect_role_domain("Lead UI/UX Designer", "Figma design systems and prototyping") == "Design"
    assert scraper.detect_role_domain("Product Designer", "Wireframing and user research") == "Design"
    
    # 3. Data & AI
    assert scraper.detect_role_domain("Senior Data Scientist", "Machine learning and PyTorch") == "Data & AI"
    assert scraper.detect_role_domain("Machine Learning Engineer", "LLM fine-tuning") == "Data & AI"
    assert scraper.detect_role_domain("Data Analyst", "Tableau and SQL dashboards") == "Data & AI"
    
    # 4. Marketing
    assert scraper.detect_role_domain("Growth Marketing Manager", "SEO and SEM performance") == "Marketing"
    assert scraper.detect_role_domain("Content Marketing Specialist", "Copywriting and social media") == "Marketing"
    
    # 5. Sales
    assert scraper.detect_role_domain("Enterprise Account Executive", "B2B SaaS sales outreach") == "Sales"
    assert scraper.detect_role_domain("Business Development Representative", "Cold outreach and CRM") == "Sales"
    
    # 6. Operations & HR
    assert scraper.detect_role_domain("Head of People Operations", "HR generalist and talent acquisition") == "Operations & HR"
    assert scraper.detect_role_domain("Technical Recruiter", "Talent sourcing and hiring") == "Operations & HR"
    
    # 7. Finance
    assert scraper.detect_role_domain("Senior Financial Analyst", "Financial modeling and forecasting") == "Finance"
    assert scraper.detect_role_domain("Corporate Accountant", "General ledger and bookkeeping") == "Finance"
    
    # 8. Customer Support
    assert scraper.detect_role_domain("Customer Support Specialist", "Zendesk ticket resolution") == "Customer Support"
    assert scraper.detect_role_domain("Customer Success Manager", "Client onboarding and retention") == "Customer Support"
    
    # 9. QA
    assert scraper.detect_role_domain("QA Automation Engineer", "Selenium and Cypress testing") == "QA"
    assert scraper.detect_role_domain("SDET II", "Automation testing and Playwright") == "QA"
    
    # 10. Engineering
    assert scraper.detect_role_domain("Senior Backend Engineer", "Python FastAPI and PostgreSQL") == "Engineering"
    assert scraper.detect_role_domain("Full Stack Developer", "React and Node.js") == "Engineering"

def test_extract_skills_multi_role():
    scraper = DummyScraper(name="TestScraper", base_url="https://example.com")
    
    # PM skills
    pm_skills = scraper.extract_skills("We need experience in product management, roadmapping, PRD, and Jira with agile sprints.")
    assert "product management" in pm_skills
    assert "roadmapping" in pm_skills
    assert "jira" in pm_skills
    assert "agile" in pm_skills
    
    # Design skills
    design_skills = scraper.extract_skills("Proficiency in Figma, UI/UX, wireframing, and design systems.")
    assert "figma" in design_skills
    assert "ui/ux" in design_skills
    assert "design systems" in design_skills
    
    # Marketing skills
    mktg_skills = scraper.extract_skills("Strong track record in SEO, content marketing, and Google Analytics.")
    assert "seo" in mktg_skills
    assert "google analytics" in mktg_skills
    
    # Sales skills
    sales_skills = scraper.extract_skills("Experience with Salesforce CRM, lead generation, and B2B cold outreach.")
    assert "salesforce" in sales_skills
    assert "crm" in sales_skills

def test_jobs_domains_endpoint():
    res = client.get("/api/jobs/domains")
    assert res.status_code == 200
    data = res.json()
    assert "domains" in data
    assert "total_active" in data
    domains = [d["name"] for d in data["domains"]]
    assert "Engineering" in domains
    assert "Product" in domains
    assert "Design" in domains
    assert "Data & AI" in domains
    assert "Marketing" in domains
    assert "Sales" in domains

def test_jobs_role_domain_filter():
    res = client.get("/api/jobs?role_domain=Engineering&limit=10")
    assert res.status_code == 200
    jobs = res.json()
    for j in jobs:
        assert j.get("role_domain") == "Engineering"
