from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.config import settings
from src.database.models import Base

# SQLite configuration with multi-threaded support
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Create all database tables if they do not exist and apply schema additions."""
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        # 1. Applications table migrations
        try:
            res = conn.exec_driver_sql("PRAGMA table_info(applications)").fetchall()
            cols = [r[1] for r in res]
            if cols:
                if "user_id" not in cols:
                    conn.exec_driver_sql("ALTER TABLE applications ADD COLUMN user_id INTEGER REFERENCES users(id)")
                if "portal" not in cols:
                    conn.exec_driver_sql("ALTER TABLE applications ADD COLUMN portal VARCHAR(100) DEFAULT 'Direct ATS'")
                if "resume_version_id" not in cols:
                    conn.exec_driver_sql("ALTER TABLE applications ADD COLUMN resume_version_id INTEGER")
                if "latex_resume_code" not in cols:
                    conn.exec_driver_sql("ALTER TABLE applications ADD COLUMN latex_resume_code TEXT DEFAULT ''")
                if "overleaf_url" not in cols:
                    conn.exec_driver_sql("ALTER TABLE applications ADD COLUMN overleaf_url VARCHAR(1024)")
                if "questions_answered_json" not in cols:
                    conn.exec_driver_sql("ALTER TABLE applications ADD COLUMN questions_answered_json TEXT DEFAULT '{}'")
                if "application_result" not in cols:
                    conn.exec_driver_sql("ALTER TABLE applications ADD COLUMN application_result VARCHAR(100) DEFAULT 'PENDING'")
                conn.commit()
        except Exception:
            pass

        # 2. Jobs table migrations
        try:
            res = conn.exec_driver_sql("PRAGMA table_info(jobs)").fetchall()
            cols = [r[1] for r in res]
            if cols:
                if "canonical_source" not in cols:
                    conn.exec_driver_sql("ALTER TABLE jobs ADD COLUMN canonical_source VARCHAR(100)")
                if "discovered_via" not in cols:
                    conn.exec_driver_sql("ALTER TABLE jobs ADD COLUMN discovered_via VARCHAR(100)")
                if "sources_json" not in cols:
                    conn.exec_driver_sql("ALTER TABLE jobs ADD COLUMN sources_json TEXT")
                if "role_domain" not in cols:
                    conn.exec_driver_sql("ALTER TABLE jobs ADD COLUMN role_domain VARCHAR(100) DEFAULT 'Engineering'")
                    conn.exec_driver_sql("UPDATE jobs SET role_domain = 'Engineering' WHERE role_domain IS NULL")
                conn.commit()
        except Exception:
            pass

        # 3. Users table migrations
        try:
            res = conn.exec_driver_sql("PRAGMA table_info(users)").fetchall()
            cols = [r[1] for r in res]
            if cols:
                if "target_job_titles_json" not in cols:
                    conn.exec_driver_sql("ALTER TABLE users ADD COLUMN target_job_titles_json TEXT DEFAULT '[\"Software Engineer\", \"Python Developer\", \"AI/ML Engineer\"]'")
                if "preferred_locations_json" not in cols:
                    conn.exec_driver_sql("ALTER TABLE users ADD COLUMN preferred_locations_json TEXT DEFAULT '[\"Remote\", \"India\", \"Bengaluru\"]'")
                if "min_salary" not in cols:
                    conn.exec_driver_sql("ALTER TABLE users ADD COLUMN min_salary FLOAT DEFAULT 500000.0")
                if "salary_currency" not in cols:
                    conn.exec_driver_sql("ALTER TABLE users ADD COLUMN salary_currency VARCHAR(10) DEFAULT 'INR'")
                if "work_preference" not in cols:
                    conn.exec_driver_sql("ALTER TABLE users ADD COLUMN work_preference VARCHAR(50) DEFAULT 'Remote / Hybrid'")
                if "operating_mode" not in cols:
                    conn.exec_driver_sql("ALTER TABLE users ADD COLUMN operating_mode VARCHAR(50) DEFAULT 'FULLY_AUTONOMOUS'")
                if "max_daily_applications" not in cols:
                    conn.exec_driver_sql("ALTER TABLE users ADD COLUMN max_daily_applications INTEGER DEFAULT 20")
                if "max_portal_applications" not in cols:
                    conn.exec_driver_sql("ALTER TABLE users ADD COLUMN max_portal_applications INTEGER DEFAULT 5")
                if "master_resume_json" not in cols:
                    conn.exec_driver_sql("ALTER TABLE users ADD COLUMN master_resume_json TEXT DEFAULT '{}'")
                conn.commit()
        except Exception:
            pass

    # 4. Seed initial portal permissions and knowledge base
    _seed_defaults()

def _seed_defaults():
    from src.database.models import PortalPermissionModel, KnowledgeBaseModel, LearningMetricModel
    db = SessionLocal()
    try:
        # Seed default portals if empty
        if db.query(PortalPermissionModel).count() == 0:
            default_portals = [
                {"portal_name": "company_portals", "display_name": "Company Career Portals (Direct ATS)", "category": "Direct ATS", "enabled": True, "max_daily_apps": 10, "requires_auth": False, "auth_status": "CONFIGURED", "apply_mode": "DIRECT_API", "description": "Direct employer career pages with 100% verified live application links."},
                {"portal_name": "linkedin", "display_name": "LinkedIn", "category": "Aggregator", "enabled": True, "max_daily_apps": 5, "requires_auth": True, "auth_status": "CONFIGURED", "apply_mode": "PORTAL_COPILOT", "description": "LinkedIn Talent Solutions & Job Discovery with 1-Click candidate copilot autofill."},
                {"portal_name": "naukri", "display_name": "Naukri", "category": "Aggregator", "enabled": True, "max_daily_apps": 5, "requires_auth": True, "auth_status": "CONFIGURED", "apply_mode": "PORTAL_COPILOT", "description": "India's largest job platform with FastApply screener question answering."},
                {"portal_name": "indeed", "display_name": "Indeed", "category": "Aggregator", "enabled": True, "max_daily_apps": 5, "requires_auth": True, "auth_status": "CONFIGURED", "apply_mode": "PORTAL_COPILOT", "description": "Indeed Global & India job discovery with ATS format parsing."},
                {"portal_name": "glassdoor", "display_name": "Glassdoor", "category": "Aggregator", "enabled": True, "max_daily_apps": 4, "requires_auth": False, "auth_status": "CONFIGURED", "apply_mode": "PORTAL_COPILOT", "description": "Glassdoor salary-benchmarked opportunities with employer reviews."},
                {"portal_name": "foundit", "display_name": "Foundit (Monster India)", "category": "Aggregator", "enabled": True, "max_daily_apps": 5, "requires_auth": False, "auth_status": "CONFIGURED", "apply_mode": "PORTAL_COPILOT", "description": "Foundit tech & enterprise career postings across India metros."},
                {"portal_name": "wellfound", "display_name": "Wellfound (AngelList)", "category": "Specialized", "enabled": True, "max_daily_apps": 5, "requires_auth": False, "auth_status": "CONFIGURED", "apply_mode": "PORTAL_COPILOT", "description": "Top venture-backed startups, high-growth tech firms, and equity roles."},
                {"portal_name": "internshala", "display_name": "Internshala", "category": "Campus", "enabled": True, "max_daily_apps": 5, "requires_auth": False, "auth_status": "CONFIGURED", "apply_mode": "PORTAL_COPILOT", "description": "Fresher, entry-level, and campus graduate technology opportunities."},
                {"portal_name": "cutshort", "display_name": "Cutshort", "category": "Specialized", "enabled": True, "max_daily_apps": 4, "requires_auth": False, "auth_status": "CONFIGURED", "apply_mode": "PORTAL_COPILOT", "description": "AI-matched tech recruitment directly connecting candidates with engineering managers."},
                {"portal_name": "instahyre", "display_name": "Instahyre", "category": "Specialized", "enabled": True, "max_daily_apps": 4, "requires_auth": False, "auth_status": "CONFIGURED", "apply_mode": "PORTAL_COPILOT", "description": "Curated premium technology and product companies with verified salary ranges."},
                {"portal_name": "hirist", "display_name": "Hirist", "category": "Specialized", "enabled": True, "max_daily_apps": 4, "requires_auth": False, "auth_status": "CONFIGURED", "apply_mode": "PORTAL_COPILOT", "description": "Specialized high-end engineering, cloud, and machine learning career portal."},
                {"portal_name": "shine", "display_name": "Shine", "category": "Aggregator", "enabled": True, "max_daily_apps": 3, "requires_auth": False, "auth_status": "CONFIGURED", "apply_mode": "PORTAL_COPILOT", "description": "Pan-India technology and corporate hiring feeds."},
                {"portal_name": "timesjobs", "display_name": "TimesJobs", "category": "Aggregator", "enabled": True, "max_daily_apps": 3, "requires_auth": False, "auth_status": "CONFIGURED", "apply_mode": "PORTAL_COPILOT", "description": "Enterprise and corporate openings across IT and technology hubs."},
                {"portal_name": "remotive", "display_name": "Remotive", "category": "Direct ATS", "enabled": True, "max_daily_apps": 8, "requires_auth": False, "auth_status": "CONFIGURED", "apply_mode": "DIRECT_API", "description": "Verified global remote software engineering, product, and AI jobs."},
                {"portal_name": "weworkremotely", "display_name": "WeWorkRemotely", "category": "Direct ATS", "enabled": True, "max_daily_apps": 8, "requires_auth": False, "auth_status": "CONFIGURED", "apply_mode": "DIRECT_API", "description": "Top curated remote community feeds across 7 career categories."},
                {"portal_name": "himalayas", "display_name": "Himalayas", "category": "Direct ATS", "enabled": True, "max_daily_apps": 8, "requires_auth": False, "auth_status": "CONFIGURED", "apply_mode": "DIRECT_API", "description": "Modern remote companies with transparent compensation and tech stack data."},
                {"portal_name": "jobicy", "display_name": "Jobicy", "category": "Aggregator", "enabled": True, "max_daily_apps": 6, "requires_auth": False, "auth_status": "CONFIGURED", "apply_mode": "DIRECT_API", "description": "Global remote opportunities with multi-role taxonomy."},
                {"portal_name": "hasjob", "display_name": "Hasjob India", "category": "Direct ATS", "enabled": True, "max_daily_apps": 5, "requires_auth": False, "auth_status": "CONFIGURED", "apply_mode": "DIRECT_API", "description": "Developer and startup job feeds across Indian tech ecosystems."},
                {"portal_name": "remoteok", "display_name": "RemoteOK", "category": "Aggregator", "enabled": True, "max_daily_apps": 6, "requires_auth": False, "auth_status": "CONFIGURED", "apply_mode": "DIRECT_API", "description": "Real-time verified developer and data opportunities."}
            ]
            for p in default_portals:
                db.add(PortalPermissionModel(**p))
            db.commit()

        # Seed candidate knowledge base if empty
        if db.query(KnowledgeBaseModel).count() == 0:
            default_kb = [
                {"category": "Legal", "question_pattern": "Work Authorization / Visa Sponsorship (work authorization sponsorship visa citizen)", "verified_answer": "Authorized to work full-time without requiring employer visa sponsorship.", "is_sensitive": False, "verified_by_user": True},
                {"category": "Availability", "question_pattern": "Notice Period / Availability (notice period start date availability joining)", "verified_answer": "Immediately available or within 15 to 30 days notice.", "is_sensitive": False, "verified_by_user": True},
                {"category": "Workplace", "question_pattern": "Workplace Flexibility / Relocation (relocation remote hybrid in-person office)", "verified_answer": "Fully flexible with Remote, Hybrid, or Onsite in designated hub locations.", "is_sensitive": False, "verified_by_user": True},
                {"category": "Compensation", "question_pattern": "Salary Expectations / CTC (salary expectation compensation ctc current expected)", "verified_answer": "Competitive and negotiable, aligned with market rates for the role and experience level.", "is_sensitive": False, "verified_by_user": True},
                {"category": "Experience", "question_pattern": "Production Experience / System Engineering (years of experience production backend software)", "verified_answer": "Proven track record delivering reliable, production-grade applications and automated data pipelines.", "is_sensitive": False, "verified_by_user": True}
            ]
            for k in default_kb:
                db.add(KnowledgeBaseModel(**k))
            db.commit()

        # Ensure Notice Period casing in existing database
        for kb_item in db.query(KnowledgeBaseModel).filter(KnowledgeBaseModel.question_pattern.ilike("%notice period%")).all():
            if "Notice Period" not in kb_item.question_pattern:
                kb_item.question_pattern = f"Notice Period / Availability ({kb_item.question_pattern})"
        db.commit()

        # Seed learning metrics baselines if empty
        if db.query(LearningMetricModel).count() == 0:
            default_metrics = [
                {"metric_type": "SUBJECT_LINE", "variant_key": "Direct Role Reference (Application for {title} - {name})", "impressions": 14, "positive_outcomes": 5, "conversion_rate": 35.7, "recommended_weight": 1.25},
                {"metric_type": "SUBJECT_LINE", "variant_key": "Value Proposition ({title} with {skill} Expertise)", "impressions": 12, "positive_outcomes": 4, "conversion_rate": 33.3, "recommended_weight": 1.15},
                {"metric_type": "SUBJECT_LINE", "variant_key": "Quick Question (Regarding {title} opening at {company})", "impressions": 9, "positive_outcomes": 2, "conversion_rate": 22.2, "recommended_weight": 0.90},
                {"metric_type": "RESUME_TEMPLATE", "variant_key": "Modern ATS LaTeX (Single Column, High Scanability)", "impressions": 20, "positive_outcomes": 9, "conversion_rate": 45.0, "recommended_weight": 1.30},
                {"metric_type": "RESUME_TEMPLATE", "variant_key": "Minimalist Academic LaTeX", "impressions": 10, "positive_outcomes": 3, "conversion_rate": 30.0, "recommended_weight": 1.00},
                {"metric_type": "COVER_LETTER_STYLE", "variant_key": "Metrics-Driven Impact (Google XYZ Framework)", "impressions": 18, "positive_outcomes": 8, "conversion_rate": 44.4, "recommended_weight": 1.30}
            ]
            for m in default_metrics:
                db.add(LearningMetricModel(**m))
            db.commit()
    except Exception as e:
        db.rollback()
    finally:
        db.close()

def get_db():
    """FastAPI dependency for database sessions."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
