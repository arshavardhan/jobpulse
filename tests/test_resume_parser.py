import io
import pymupdf as fitz
from fastapi.testclient import TestClient
from main import app
from src.services.resume_parser import clean_extracted_text, parse_resume_bytes

client = TestClient(app)

def test_clean_extracted_text_noise_removal():
    noisy_input = (
        "John Doe\n\n"
        "\uf0b7 Developed micro-\nservices using Python and FastAPI.\x00\x01\n"
        "\u2022 Imple-\nmented Kubernetes clusters with Docker.\n\n\n\n"
        "Page 1 of 2\n"
        "Proficient in SQL and AWS cloud systems."
    )
    cleaned = clean_extracted_text(noisy_input)
    # Check that null bytes are stripped
    assert "\x00" not in cleaned
    assert "\x01" not in cleaned
    # Check that hyphenated words are merged
    assert "microservices" in cleaned
    assert "Implemented" in cleaned
    # Check that bullets are normalized
    assert "* Developed" in cleaned or "- Developed" in cleaned or "* " in cleaned
    # Check that page number lines are stripped
    assert "Page 1 of 2" not in cleaned
    # Check that excessive newlines are collapsed
    assert "\n\n\n" not in cleaned

def test_parse_resume_bytes_with_real_pdf():
    # Generate an in-memory PDF with 2 columns
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Sarah Jenkins\nSenior Backend Engineer\nsarah.jenkins@example.com\n(555) 234-5678")
    page.insert_text((50, 150), "Experience: 5+ years of experience in distributed systems.")
    page.insert_text((50, 200), "Skills: Python, Docker, FastAPI, PostgreSQL, Kubernetes, Redis.")
    pdf_bytes = doc.tobytes()

    result = parse_resume_bytes(pdf_bytes, "sarah_resume.pdf")
    assert result["success"] is True
    assert "Sarah Jenkins" in result["name"] or "Jenkins" in result["clean_text"]
    assert result["email"] == "sarah.jenkins@example.com"
    assert result["years_of_experience"] >= 5.0
    assert "python" in [s.lower() for s in result["skills"]]
    assert "fastapi" in [s.lower() for s in result["skills"]]

def test_resume_parse_api_endpoint():
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "David Miller\ndavid.miller@tech.org\nPython Engineer with 3 years of experience.")
    pdf_bytes = doc.tobytes()

    files = {"file": ("david_miller.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    resp = client.post("/api/resume/parse", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "david.miller@tech.org" == data["email"]
    assert "python" in [s.lower() for s in data["skills"]]
    assert data["years_of_experience"] == 3.0
