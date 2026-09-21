import re
import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import fitz  # PyMuPDF
from src.models.job import JobPosting, UserProfile, MatchResult
from src.scrapers.base import COMMON_TECH_SKILLS
from src.agents.llm_provider import llm

logger = logging.getLogger(__name__)

class AnalystAgent:
    """Autonomous Analyst Agent: Parses resumes, conducts hybrid semantic matching, and detects skill gaps."""

    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words="english", max_features=1000)

    def parse_resume_file(self, file_path: str) -> UserProfile:
        """Extract text from PDF or text file and extract profile attributes."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Resume file not found at: {file_path}")

        extracted_text = ""
        if path.suffix.lower() == ".pdf":
            try:
                doc = fitz.open(str(path))
                for page in doc:
                    extracted_text += page.get_text() + "\n"
            except Exception as e:
                logger.error(f"Error reading PDF with PyMuPDF: {e}")
        else:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                extracted_text = f.read()

        return self.extract_profile_from_text(extracted_text)

    def extract_profile_from_text(self, text: str) -> UserProfile:
        """Extract candidate information, skills, and target roles from raw text."""
        lowered = text.lower()

        # Extract skills using the tech skills catalog
        found_skills = set()
        for skill in COMMON_TECH_SKILLS:
            pattern = r"\b" + re.escape(skill) + r"\b"
            if re.search(pattern, lowered):
                found_skills.add(skill)

        # Estimate years of experience
        years = 2.0
        match_years = re.search(r"(\d+)\+?\s*(?:years?|yrs?)(?:\s+of)?\s+experience", lowered)
        if match_years:
            try:
                years = float(match_years.group(1))
            except Exception:
                pass

        # Detect candidate name (heuristic: first non-empty line or common pattern)
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        full_name = lines[0][:50] if lines else "Candidate"
        if any(w in full_name.lower() for w in ["resume", "curriculum", "cv"]):
            full_name = lines[1][:50] if len(lines) > 1 else "Candidate"

        # Email detection
        email = None
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
        if email_match:
            email = email_match.group(0)

        # Target roles detection
        target_roles = []
        if any(s in found_skills for s in ["pytorch", "tensorflow", "machine learning", "nlp", "llm"]):
            target_roles.append("AI/ML Engineer")
        if any(s in found_skills for s in ["pandas", "numpy", "sql", "tableau"]):
            target_roles.append("Data Scientist / Analytics Specialist")
        if any(s in found_skills for s in ["fastapi", "django", "react", "typescript", "rest api"]):
            target_roles.append("Full Stack Python Developer")
        if any(s in found_skills for s in ["beautifulsoup", "selenium", "playwright", "web scraping"]):
            target_roles.append("Web Scraping & Automation Specialist")

        if not target_roles:
            target_roles = ["Software Engineer", "Python Developer"]

        profile = UserProfile(
            full_name=full_name,
            email=email or "candidate@example.com",
            skills=sorted(list(found_skills)),
            years_of_experience=years,
            summary=text[:600].strip(),
            target_roles=target_roles
        )
        return profile

    def calculate_match(self, profile: UserProfile, job: JobPosting) -> MatchResult:
        """Compute hybrid ATS & Semantic Match score between user profile and job posting."""
        # 1. Exact & Fuzzy Skill Match
        profile_skills_set = set(s.lower() for s in profile.skills)
        job_skills = [s.lower() for s in job.skills_required]

        matching_skills = [s for s in job_skills if s in profile_skills_set]
        missing_skills = [s for s in job_skills if s not in profile_skills_set]

        if job_skills:
            keyword_score = (len(matching_skills) / len(job_skills)) * 100.0
        else:
            keyword_score = 70.0  # Baseline if no explicit skills tagged

        # 2. Vector Semantic Similarity via TF-IDF
        profile_corpus = f"{' '.join(profile.skills)} {profile.summary} {' '.join(profile.target_roles)}"
        job_corpus = f"{job.title} {' '.join(job.skills_required)} {job.description[:1000]}"

        try:
            tfidf_matrix = self.vectorizer.fit_transform([profile_corpus, job_corpus])
            cosine_sim = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            # TF-IDF cosine similarity on asymmetric corpora is typically 0.15 - 0.40.
            # Scale cosine similarity and blend with keyword coverage to model modern ATS parsing:
            scaled_sim = min(float(cosine_sim) * 220.0, 100.0)
            semantic_score = min(max((scaled_sim * 0.4) + (keyword_score * 0.6), 0.0), 100.0)
        except Exception:
            semantic_score = keyword_score

        # 3. Multi-Factor Relevance Modifiers
        # A. Job Title Alignment
        title_boost = 0.0
        target_roles_lower = [r.lower() for r in profile.target_roles]
        job_title_lower = job.title.lower()
        if any(tr in job_title_lower or job_title_lower in tr for tr in target_roles_lower):
            title_boost += 6.0
        elif any(word in job_title_lower for tr in target_roles_lower for word in tr.split() if len(word) > 3):
            title_boost += 3.0

        # B. Experience Level Alignment
        exp_boost = 0.0
        job_exp = (job.experience_level or "").lower()
        if profile.years_of_experience < 1.5 and ("fresher" in job_exp or "entry" in job_exp or job.is_fresher):
            exp_boost += 5.0
        elif 1.5 <= profile.years_of_experience <= 5.0 and ("mid" in job_exp or "associate" in job_exp):
            exp_boost += 5.0
        elif profile.years_of_experience > 5.0 and ("senior" in job_exp or "lead" in job_exp or "principal" in job_exp):
            exp_boost += 5.0

        # C. Location & Work Mode Alignment
        loc_boost = 0.0
        job_loc = (job.location or "").lower()
        pref_locs = [l.lower() for l in (profile.preferred_locations or ["remote"])]
        if job.is_remote or any(pl in job_loc for pl in pref_locs):
            loc_boost += 4.0

        # D. High-Match Synergy Bonus (produces 90%+ ATS match for highly qualified candidates)
        synergy_boost = 0.0
        if keyword_score >= 75.0:
            synergy_boost += 8.0
        if keyword_score >= 90.0:
            synergy_boost += 7.0

        # 4. Weighted Final ATS Score
        base_score = (keyword_score * 0.45) + (semantic_score * 0.35)
        final_score = round(min(base_score + title_boost + exp_boost + loc_boost + synergy_boost, 100.0), 1)

        # Salary display string
        salary_str = "Competitive / Undisclosed"
        if job.salary_min and job.salary_max:
            salary_str = f"${job.salary_min:,.0f} - ${job.salary_max:,.0f} {job.currency}"
        elif job.salary_min:
            salary_str = f"From ${job.salary_min:,.0f} {job.currency}"
        elif job.salary_max:
            salary_str = f"Up to ${job.salary_max:,.0f} {job.currency}"

        # Strategic Rationale & Pitch
        rationale = (
            f"Strong multi-factor alignment ({final_score}%) with {len(matching_skills)} overlapping skills "
            f"({', '.join(matching_skills[:4]) if matching_skills else 'general technical stack'}) "
            f"matching preferred roles and experience level."
        )
        if missing_skills:
            rationale += f" Growth areas: {', '.join(missing_skills[:3])}."

        suggested_pitch = (
            f"I have extensive hands-on experience in {', '.join(matching_skills[:3]) if matching_skills else 'software engineering'}, "
            f"and I am eager to apply this expertise to drive impactful results for {job.company}'s {job.title} role."
        )

        return MatchResult(
            job_id=job.id,
            job_title=job.title,
            company=job.company,
            location=job.location,
            city=job.city,
            country=job.country,
            region=job.region,
            is_fresher=job.is_fresher,
            experience_level=job.experience_level,
            url=job.url,
            apply_url=job.apply_url or job.url,
            source=job.source,
            source_name=job.source_name,
            verification_status=job.verification_status,
            salary_display=salary_str,
            match_score=min(final_score, 100.0),
            semantic_score=round(semantic_score, 1),
            keyword_score=round(keyword_score, 1),
            matching_skills=matching_skills,
            missing_skills=missing_skills,
            rationale=rationale,
            suggested_pitch=suggested_pitch
        )


    def rank_jobs(self, profile: UserProfile, jobs: List[JobPosting]) -> List[MatchResult]:
        """Rank all provided jobs against the profile sorted by descending match score."""
        results = [self.calculate_match(profile, j) for j in jobs]
        results.sort(key=lambda x: x.match_score, reverse=True)
        return results
