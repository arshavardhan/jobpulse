"""
Deterministic offline fixtures matching real external responses from:
- Hasjob (Atom XML)
- Lever (Meesho / CRED JSON)
- Remotive (JSON)
"""

SAMPLE_HASJOB_ATOM_XML = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>All jobs - Hasjob</title>
  <link href="https://hasjob.co/"/>
  <entry>
    <title type="text">Senior Backend Python Engineer</title>
    <id>https://hasjob.co/techinnovate.in/p98y1</id>
    <link href="https://hasjob.co/techinnovate.in/p98y1"/>
    <published>2026-09-18T11:28:04Z</published>
    <location>Bengaluru</location>
    <content type="html"><![CDATA[
      <p>We are seeking a Python engineer with expertise in FastAPI, PostgreSQL, and Docker. Experience with AWS is a plus.</p>
    ]]></content>
  </entry>
  <entry>
    <title type="text">Machine Learning Intern / Fresher</title>
    <id>https://hasjob.co/aiverse.co/m23k4</id>
    <link href="https://hasjob.co/aiverse.co/m23k4"/>
    <published>2026-09-17T10:00:00Z</published>
    <location>Hyderabad</location>
    <content type="html"><![CDATA[
      <p>Exciting 6-month internship for freshers. You will build NLP pipelines using PyTorch and HuggingFace.</p>
    ]]></content>
  </entry>
</feed>
"""

SAMPLE_LEVER_MEESHO_JSON = [
    {
        "id": "7d9af9b5-c1c7-48ec-bbb5-9b25e49f6596",
        "text": "Software Development Engineer II - Backend",
        "categories": {
            "commitment": "Full Time Employee",
            "department": "Engineering",
            "team": "Tech",
            "location": "Bangalore, Karnataka",
            "allLocations": ["Bangalore, Karnataka"]
        },
        "descriptionPlain": "We are looking for an SDE-2 to design scalable microservices using Java, Spring Boot, Kafka, and Redis.",
        "hostedUrl": "https://jobs.lever.co/meesho/7d9af9b5-c1c7-48ec-bbb5-9b25e49f6596",
        "applyUrl": "https://jobs.lever.co/meesho/7d9af9b5-c1c7-48ec-bbb5-9b25e49f6596/apply",
        "createdAt": 1726000000000
    },
    {
        "id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
        "text": "Graduate Engineer Trainee - Data Science (Fresher)",
        "categories": {
            "commitment": "Full Time Employee",
            "department": "Data",
            "team": "Analytics",
            "location": "Bengaluru, Karnataka",
            "allLocations": ["Bengaluru, Karnataka"]
        },
        "descriptionPlain": "Entry-level campus role for 2026 graduates. Must know Python, Pandas, SQL, and Machine Learning basics.",
        "hostedUrl": "https://jobs.lever.co/meesho/1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
        "applyUrl": "https://jobs.lever.co/meesho/1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d/apply",
        "createdAt": 1726100000000
    }
]

SAMPLE_REMOTIVE_JSON = {
    "jobs": [
        {
            "id": 2091130,
            "url": "https://remotive.com/remote-jobs/software-dev/full-stack-developer-2091130",
            "title": "Senior Full-Stack Engineer",
            "company_name": "Lemon.io",
            "category": "software-dev",
            "tags": ["python", "react", "typescript", "fastapi", "docker"],
            "job_type": "full_time",
            "publication_date": "2026-09-18T10:00:00",
            "candidate_required_location": "Worldwide",
            "salary": "$120,000 - $150,000",
            "description": "Lemon.io is looking for an experienced Senior Full-Stack Engineer skilled in Python and React."
        }
    ]
}
