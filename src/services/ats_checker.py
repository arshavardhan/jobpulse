import re
import logging
from typing import Dict, Any, List, Optional
from src.models.user import ATSCheckResponse, ATSErrorItem
from src.models.job import JobPosting, UserProfile
from src.scrapers.base import COMMON_TECH_SKILLS

logger = logging.getLogger(__name__)

# Expanded Tech Skills Dictionary for comprehensive ATS auditing
EXTENDED_TECH_SKILLS = list(set(COMMON_TECH_SKILLS + [
    # Python & Backend Ecosystem
    "python", "fastapi", "django", "flask", "sqlalchemy", "celery", "pydantic", "alembic",
    "pytest", "unittest", "asyncio", "aiohttp", "gunicorn", "uvicorn", "tornado",
    "rest api", "restful api", "rest", "graphql", "grpc", "microservices", "webhooks",
    "postgresql", "postgres", "mysql", "sqlite", "mongodb", "redis", "elasticsearch",
    "cassandra", "dynamodb", "rabbitmq", "kafka", "sqs", "sns",
    "docker", "docker compose", "kubernetes", "k8s", "helm", "terraform",
    "aws", "gcp", "azure", "linux", "bash", "shell scripting", "git", "github", "gitlab",
    "ci/cd", "github actions", "jenkins", "nginx", "load balancing",
    "oop", "design patterns", "system design", "distributed systems", "database optimization",
    "sql", "nosql", "jwt", "oauth2", "orm",
    # Frontend & Full Stack
    "javascript", "typescript", "react", "next.js", "vue", "angular", "node.js", "express",
    "html", "css", "tailwind", "redux", "webpack", "vite",
    # Data & AI/ML
    "pandas", "numpy", "scikit-learn", "pytorch", "tensorflow", "keras", "huggingface",
    "langchain", "langgraph", "llm", "rag", "vector database", "qdrant", "chroma", "pinecone",
    "spark", "airflow", "dbt", "snowflake", "bigquery", "data engineering", "machine learning",
    "deep learning", "nlp", "computer vision", "data analysis", "tableau", "power bi"
]))

ROLE_SKILL_PRESETS: Dict[str, List[str]] = {
    "python_backend": [
        "python", "fastapi", "django", "rest api", "postgresql", "sql", "redis",
        "docker", "celery", "sqlalchemy", "git", "ci/cd", "microservices", "pytest", "linux"
    ],
    "ai_ml": [
        "python", "machine learning", "pytorch", "tensorflow", "scikit-learn", "pandas",
        "numpy", "deep learning", "llm", "rag", "langchain", "sql", "docker", "git"
    ],
    "full_stack": [
        "javascript", "typescript", "react", "node.js", "python", "rest api",
        "postgresql", "html", "css", "tailwind", "docker", "git"
    ],
    "data_engineer": [
        "python", "sql", "spark", "kafka", "airflow", "snowflake", "dbt",
        "postgresql", "aws", "docker", "data engineering", "git"
    ],
    "cloud_devops": [
        "aws", "docker", "kubernetes", "ci/cd", "linux", "terraform",
        "python", "git", "jenkins", "microservices"
    ],
    "fresher_dev": [
        "python", "sql", "git", "data structures", "algorithms",
        "oop", "rest api", "linux", "problem solving"
    ]
}

WEAK_PHRASES = [
    "responsible for", "duties included", "helped with", "worked on",
    "assisted with", "participated in", "familiar with", "worked closely with",
    "handled day to day", "involved in"
]

STRONG_ACTION_VERBS = [
    "architected", "engineered", "optimized", "spearheaded", "deployed",
    "automated", "designed", "scaled", "orchestrated", "streamlined",
    "implemented", "refactored", "built", "accelerated", "pioneered"
]

def extract_tech_skills(text: str) -> List[str]:
    """Extract recognized tech skills from any raw text using regex word boundaries."""
    if not text:
        return []
    text_lower = text.lower()
    found = set()
    for sk in EXTENDED_TECH_SKILLS:
        pattern = r"(?<!\w)" + re.escape(sk) + r"(?!\w)"
        if re.search(pattern, text_lower):
            found.add(sk)
    return sorted(list(found))

def infer_skills_from_role(role_title: str) -> List[str]:
    """Infer baseline target skills based on role title keywords."""
    role_lower = (role_title or "").lower()
    if any(k in role_lower for k in ["python", "backend", "django", "fastapi", "flask"]):
        return ROLE_SKILL_PRESETS["python_backend"]
    elif any(k in role_lower for k in ["ai", "machine learning", "ml", "deep learning", "nlp", "llm", "data scientist"]):
        return ROLE_SKILL_PRESETS["ai_ml"]
    elif any(k in role_lower for k in ["full stack", "fullstack", "web developer"]):
        return ROLE_SKILL_PRESETS["full_stack"]
    elif any(k in role_lower for k in ["data engineer", "etl", "analytics engineer", "big data"]):
        return ROLE_SKILL_PRESETS["data_engineer"]
    elif any(k in role_lower for k in ["devops", "cloud", "sre", "infrastructure", "platform engineer"]):
        return ROLE_SKILL_PRESETS["cloud_devops"]
    elif any(k in role_lower for k in ["fresher", "intern", "junior", "graduate", "trainee"]):
        return ROLE_SKILL_PRESETS["fresher_dev"]
    return ["python", "sql", "rest api", "git", "docker", "microservices"]

def analyze_ats_compliance(
    candidate_skills: List[str],
    resume_text: str,
    years_exp: float,
    job_title: str,
    job_company: str,
    job_description: str,
    job_skills: List[str]
) -> ATSCheckResponse:
    """
    Analyzes resume against target job description.
    Detects ATS errors, missing keywords, formatting weaknesses,
    and produces actionable suggestions and tailored XYZ-format bullet rewrites.
    """
    resume_lower = (resume_text or "").lower()
    job_desc_lower = (job_description or "").lower()
    title_lower = (job_title or "").lower()

    # 1. Candidate Skills Extraction
    # Combine explicitly passed skills with any skills extracted directly from resume_text
    extracted_cand_skills = extract_tech_skills(resume_text or "")
    combined_cand_skills = set(s.lower() for s in (candidate_skills or []) if s)
    combined_cand_skills.update(extracted_cand_skills)
    combined_cand_text = f"{' '.join(combined_cand_skills)} {resume_lower}".lower()

    # 2. Target Skills Assembly
    target_skills_set = set(s.lower() for s in (job_skills or []) if s)
    
    # Extract tech skills from job description
    desc_skills = extract_tech_skills(job_description or "")
    target_skills_set.update(desc_skills)

    # If target skills is still sparse (< 4), infer baseline from role title
    if len(target_skills_set) < 4:
        inferred = infer_skills_from_role(job_title)
        target_skills_set.update(inferred)

    target_skills = sorted(list(target_skills_set))

    # 3. Match & Missing Calculation
    matched_skills = []
    missing_skills = []

    for sk in target_skills:
        pattern = r"(?<!\w)" + re.escape(sk) + r"(?!\w)"
        if sk in combined_cand_skills or re.search(pattern, combined_cand_text):
            matched_skills.append(sk)
        else:
            missing_skills.append(sk)

    matched_skills.sort()
    missing_skills.sort()

    # Keyword match score (clamped between 15% and 96%)
    if target_skills:
        raw_keyword_score = (len(matched_skills) / len(target_skills)) * 100.0
        keyword_score = round(max(15.0, min(96.0, raw_keyword_score)), 1)
    else:
        keyword_score = 75.0

    # 4. Semantic & Role Title Relevance
    title_words = set(re.findall(r"\b[a-zA-Z]{3,}\b", title_lower))
    # Exclude trivial stop words
    stop_words = {"and", "for", "the", "with", "all", "our", "are"}
    title_words = {w for w in title_words if w not in stop_words}
    
    title_matches = [w for w in title_words if w in combined_cand_text]
    title_ratio = len(title_matches) / max(1, len(title_words))
    semantic_score = round(max(20.0, min(96.0, (title_ratio * 70.0) + (keyword_score * 0.30))), 1)

    # 5. Experience Alignment
    is_senior_role = any(s in title_lower for s in ["senior", "lead", "principal", "architect", "manager", "staff", "head"])
    is_fresher_role = any(f in title_lower for f in ["intern", "fresher", "junior", "entry", "associate", "trainee", "graduate"])

    if is_senior_role and years_exp < 3.0:
        exp_score = 55.0
    elif is_senior_role and years_exp >= 5.0:
        exp_score = 94.0
    elif is_fresher_role:
        exp_score = 92.0 if years_exp <= 2.0 else 85.0
    elif years_exp >= 2.0:
        exp_score = 88.0
    else:
        exp_score = 72.0

    # 6. Overall Weighted Score (0-100 scale, realistic range 25-96%)
    overall_score = round((keyword_score * 0.45) + (semantic_score * 0.35) + (exp_score * 0.20), 1)
    overall_score = max(20.0, min(96.0, overall_score))

    # 7. Detected Errors & ATS Gaps
    errors: List[ATSErrorItem] = []

    # Error: Missing high-impact technical keywords
    if missing_skills:
        top_missing = missing_skills[:4]
        errors.append(ATSErrorItem(
            category="Keyword Gap",
            severity="CRITICAL",
            message=f"Missing {len(missing_skills)} key technical prerequisites: {', '.join(top_missing)}.",
            fix=f"Integrate '{top_missing[0]}' and '{top_missing[1] if len(top_missing) > 1 else top_missing[0]}' into your project descriptions, tech stack bullets, or skills section."
        ))

    # Error: Weak passive verbs
    found_weak = [p for p in WEAK_PHRASES if p in resume_lower]
    if found_weak:
        errors.append(ATSErrorItem(
            category="Impact Phrasing",
            severity="WARNING",
            message=f"Detected passive phrasing ('{found_weak[0]}') which lowers automated ATS ranking scores.",
            fix=f"Replace '{found_weak[0]}' with strong action verbs like 'Architected', 'Spearheaded', 'Engineered', or 'Optimized'."
        ))

    # Error: Lack of quantifiable metrics
    metrics_pattern = r"\b\d+([.,]\d+)?%|\b\d+[kKmMbB]?\b|\b\$\d+|\b[1-9]\d*x\b"
    has_metrics = bool(re.search(metrics_pattern, resume_text or ""))
    if not has_metrics:
        errors.append(ATSErrorItem(
            category="Metrics & Results",
            severity="WARNING",
            message="Resume lacks quantifiable metrics (percentages, throughput, latency reduction, user volume).",
            fix="Format achievements in Google XYZ format: 'Accomplished [X] as measured by [Y] by doing [Z]'."
        ))

    # Error: Seniority / Experience calibration
    if is_senior_role and years_exp < 3.0:
        errors.append(ATSErrorItem(
            category="Seniority Alignment",
            severity="SUGGESTION",
            message=f"Target role '{job_title}' typically requires 3-5+ years. Current profile indicates {years_exp} years.",
            fix="Emphasize production architectural leadership, system scale, and high-impact end-to-end deliverables."
        ))

    # Error: Resume content length check
    word_count = len((resume_text or "").split())
    if word_count < 60:
        errors.append(ATSErrorItem(
            category="Content Depth",
            severity="WARNING",
            message="Resume text is brief (less than 60 words). ATS parsers may struggle to extract sufficient context.",
            fix="Include 3-4 detailed project bullet points explaining tech stack, system architecture, and measurable outcomes."
        ))

    # 8. Actionable Suggestions
    first_missing = missing_skills[0] if missing_skills else "distributed architecture"
    recommendations = [
        f"Target keyword density: Add '{first_missing}' explicitly to your summary and recent experience.",
        f"Mirror job title: Incorporate terms related to '{job_title}' into your profile headline.",
        "Ensure bullet points start with strong action verbs and include metrics (e.g. 'reduced latency by 40%').",
        "Keep resume layout clean with single-column ATS-parseable formatting without complex tables or images."
    ]

    # 9. Tailored XYZ-format Bullet Rewrites
    top_matched = matched_skills[0] if matched_skills else ("Python" if "python" in title_lower else "Core Stack")
    second_missing = missing_skills[1] if len(missing_skills) > 1 else ("PostgreSQL" if "python" in title_lower else "cloud infrastructure")

    if "python" in title_lower or "backend" in title_lower:
        bullet_fixes = [
            f"Architected high-throughput RESTful microservices using {top_matched} and FastAPI, cutting API latency by 38% across 450k+ daily requests.",
            f"Engineered asynchronous background task queues utilizing {second_missing} and Redis, optimizing data processing throughput and improving pipeline reliability to 99.8%.",
            f"Containerized backend services with Docker and streamlined CI/CD pipelines, reducing staging deployment cycle times by 40%."
        ]
    elif "ai" in title_lower or "machine learning" in title_lower or "data" in title_lower:
        bullet_fixes = [
            f"Engineered end-to-end ML inference pipelines using {top_matched} and PyTorch, accelerating model throughput by 45% on production GPU clusters.",
            f"Architected Retrieval-Augmented Generation (RAG) workflows utilizing vector databases and {second_missing}, improving answer accuracy by 32%.",
            f"Automated feature extraction and data preprocessing pipelines with Pandas and SQL, reducing ETL turnaround time by 50%."
        ]
    else:
        bullet_fixes = [
            f"Architected scalable services with {top_matched} and {first_missing}, cutting processing latency by 35% across 200k+ daily transactions.",
            f"Engineered resilient automated pipelines utilizing {top_matched}, improving test coverage to 94% and streamlining release cycles.",
            f"Spearheaded adoption of {second_missing} and containerized microservices, reducing infrastructure overhead by 28% while meeting SLA requirements."
        ]

    return ATSCheckResponse(
        overall_score=overall_score,
        keyword_match_score=keyword_score,
        semantic_relevance_score=semantic_score,
        experience_alignment_score=exp_score,
        matched_skills=matched_skills,
        missing_critical_skills=missing_skills,
        detected_errors=errors,
        tailored_resume_bullet_fixes=bullet_fixes,
        actionable_recommendations=recommendations
    )
