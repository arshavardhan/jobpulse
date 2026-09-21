# Agentic AI Job Automation & Market Analytics Agent

[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.14-blue?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Tests](https://img.shields.io/badge/Tests-28%20Passed%20(100%25)-brightgreen?logo=pytest&logoColor=white)](https://pytest.org)
[![Live Jobs](https://img.shields.io/badge/Live%20Sources-9%20Active-success)](https://hasjob.co)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

> **Autonomous Multi-Agent AI Platform** for 100% genuine multi-source job harvesting, resume semantic matching, ATS collateral tailoring, real-time market analytics, and application lifecycle tracking.

---

## Key Highlights

- **100% Genuine Live Job Harvesting**: Autonomous multi-source scrapers extracting postings from **Hasjob.co**, **Lever Career ATS (Meesho, CRED)**, **Remotive**, **Himalayas**, **WeWorkRemotely**, **Jobicy**, **Arbeitnow**, and **RemoteOK**. Zero mock, synthetic, or fake records.
- **Multi-Strategy Deduplication**: Multi-key deduplication leveraging normalized URL hashing (`SHA-256`), content fingerprinting (`title + company + description`), and direct employer ATS preference (automatically upgrading third-party aggregator links to direct Lever ATS portals).
- **India Tech Hubs & Fresher Filtering**: Granular classification separating Indian tech cities (Bengaluru, Hyderabad, Gurgaon, Pune, Mumbai, Delhi NCR) from Global Remote roles, coupled with dedicated fresher/internship detection with negative senior-keyword suppression.
- **Lifecycle & Live URL Verification**: Automated verification probes validating HTTP reachability, status code monitoring (distinguishing HTTP 200..399 from 404/410 expired vs 429 rate-limited), and automated `ACTIVE` -> `STALE` transitions after 14 days.
- **Resume Intelligence & ATS Matching**: Dual-stage hybrid engine combining **TF-IDF Vector Cosine Similarity** with **set-theoretic technical skill overlap** to compute accurate 0-100% ATS match scores.
- **Application Tailoring Agent**: One-click generation of ATS-optimized cover letters, XYZ-format resume bullet points, and role-specific technical & behavioral interview preparation Q&As.
- **LazyApply-Style Copilot**: Batch auto-apply agent supporting subscription tiers (Free vs Pro) and structured form autofill dossiers.
- **Macro Market Analytics**: Interactive visual analytics dashboard displaying in-demand tech skill distributions, salary percentiles by experience level, remote work ratios, and candidate competitiveness index.
- **Application Lifecycle Kanban**: End-to-end tracking from `Discovered` -> `Shortlisted` -> `Applied` -> `Interviewing` -> `Offer`.
- **Modern Responsive Dashboard**: Single-Page App built with Tailwind CSS, Chart.js, glassmorphism styling, real-time pulsing `🟢 Verified Live` badges, and direct external application links.

---

## Multi-Agent Architecture

```
                              ┌──────────────────────────────────┐
                              │     Candidate Resume (PDF/TXT)   │
                              └────────────────┬─────────────────┘
                                               │
                                               ▼
┌────────────────────────┐            ┌──────────────────┐             ┌─────────────────────────┐
│     Scout Agent        │            │  Analyst Agent   │             │ Market Intelligence     │
│  (Hasjob, Lever-Meesho,│ ─────────► │ (Hybrid Semantic │ ──────────► │ Agent                   │
│   Lever-CRED, Remotive,│ Job Stream │  & ATS Matching) │             │ (Salary, Demand Curves) │
│   Himalayas, WWR, etc.)│            │                  │             │                         │
└────────────────────────┘            └────────┬─────────┘             └─────────────────────────┘
                                               │
                                               ▼
                                      ┌──────────────────┐             ┌─────────────────────────┐
                                      │   Tailor Agent   │             │ Tracker Agent           │
                                      │ (Cover Letters,  │ ──────────► │ (Kanban Lifecycle &     │
                                      │  ATS Resume, QA) │             │  Interview Scheduling)  │
                                      └──────────────────┘             └─────────────────────────┘
```

---

## Quickstart Guide

### 1. Clone & Install Dependencies
```bash
git clone https://github.com/your-repo/job-automation-agent.git
cd job-automation-agent
pip install -r requirements.txt
```

### 2. Launch the Web Platform
Run via Python or double-click `run.bat` on Windows:
```bash
python main.py
```
Open your browser at **[http://localhost:8000](http://localhost:8000)**.
Interactive API documentation is available at **[http://localhost:8000/docs](http://localhost:8000/docs)**.

### 3. Or Run the Rich Terminal CLI
```bash
# Run the complete end-to-end autonomous agent demo
python -m src.cli --demo

# Run individual agent commands
python -m src.cli --hunt --query "AI"
python -m src.cli --match
python -m src.cli --analytics
```

---

## Running Automated Tests

Run the automated test suite with `pytest`:
```bash
python -m pytest tests/ -v
```
All 28 unit and integration tests pass in ~4 seconds with 100% coverage across scrapers, deduplication, lifecycle verification, India/fresher classification, matching algorithms, tailoring, analytics, and REST API endpoints.

To run the live internet diagnostic smoke test against genuine external APIs:
```bash
python tests/smoke_live_sources.py
```

---

## Project Structure

```
job-automation-agent/
├── data/
│   ├── demo/
│   │   ├── sample_resume_aiml.txt          # Sample candidate resume (AI/ML)
│   │   └── sample_resume_fullstack.txt     # Sample candidate resume (Full Stack)
│   └── jobs.db                             # SQLite persistent storage
├── src/
│   ├── config.py                           # Application settings & environment
│   ├── models/                             # Pydantic data contracts
│   │   ├── job.py                          # JobPosting, UserProfile, MatchResult
│   │   └── application.py                  # ApplicationStatus, TailoredPackage
│   ├── database/                           # SQLAlchemy ORM layer
│   │   ├── db.py                           # SQLite session manager
│   │   └── models.py                       # JobModel, ApplicationModel, ProfileModel
│   ├── scrapers/                           # Web scraping sub-system
│   │   ├── base.py                         # BaseScraper with entity extraction
│   │   ├── remoteok.py                     # RemoteOK scraper
│   │   ├── jobicy.py                       # Jobicy scraper
│   │   ├── arbeitnow.py                    # Arbeitnow scraper
│   │   └── mock_feed.py                    # High-fidelity fallback feed
│   ├── agents/                             # Autonomous agents
│   │   ├── scout.py                        # Scout Agent (Job harvesting)
│   │   ├── analyst.py                      # Analyst Agent (Resume & Matching)
│   │   ├── tailor.py                       # Tailor Agent (Cover letter & Interview prep)
│   │   ├── market_intelligence.py          # Market Intelligence Agent
│   │   ├── tracker.py                      # Tracker Agent (Kanban lifecycle)
│   │   └── llm_provider.py                 # Multi-provider LLM interface
│   ├── analytics/                          # Statistical & Chart.js data engine
│   │   └── engine.py
│   ├── api/                                # FastAPI REST endpoints
│   │   └── routes.py
│   ├── frontend/                           # Responsive Single-Page Web Dashboard
│   │   ├── index.html
│   │   ├── styles.css
│   │   └── app.js
│   └── cli.py                              # Rich Terminal interface
├── tests/                                  # Automated Pytest suite (17 tests)
│   ├── test_scrapers.py
│   ├── test_analyst.py
│   ├── test_tailor.py
│   ├── test_analytics.py
│   ├── test_tracker.py
│   └── test_api.py
├── main.py                                 # Web server entrypoint
├── APPROACH.md                             # Technical & theoretical submission document
├── requirements.txt                        # Dependency definitions
├── run.bat                                 # One-click Windows launcher
└── README.md                               # Repository guide
```

---

## REST API Overview

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/system/status` | System health, database counts, active LLM |
| `GET` | `/api/profile` | Get active candidate profile |
| `POST` | `/api/profile` | Update candidate profile |
| `POST` | `/api/profile/upload-resume` | Upload PDF/TXT resume and auto-extract skills |
| `POST` | `/api/scout/hunt` | Trigger Scout Agent to harvest multi-source jobs |
| `GET` | `/api/jobs` | Query and filter stored jobs |
| `POST` | `/api/match` | Run Analyst Agent to score jobs against candidate profile |
| `POST` | `/api/tailor/{job_id}` | Generate tailored cover letter, resume bullets & interview Q&A |
| `GET` | `/api/analytics` | Retrieve macro market demand, salary distributions, and candidate fit |
| `GET` | `/api/applications` | List applications in Kanban tracker |
| `POST` | `/api/applications` | Add job to tracker (`SHORTLISTED`, `APPLIED`, etc.) |
| `PUT` | `/api/applications/{id}` | Update application status or notes |
| `DELETE` | `/api/applications/{id}` | Remove application from tracker |
| `GET` | `/api/applications/funnel` | Get application conversion funnel metrics |

---

## Technical Submission Details

For an in-depth breakdown of the agent design principles, mathematical formulation of the ATS matching algorithm, web scraping resilience strategies, and empirical benchmarks, please review [APPROACH.md](file:///c:/Users/dumpa/python/job%20automition%20agent/APPROACH.md).
