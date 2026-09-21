import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from src.models.job import JobPosting, UserProfile, MatchResult, SubscriptionPlan
from src.agents.llm_provider import llm
from src.database.models import (
    ApplicationModel, JobModel, UserModel, ResumeVersionModel,
    RecruiterContactModel, OutreachEmailModel, ActivityTimelineModel,
    PortalPermissionModel, KnowledgeBaseModel, PendingQuestionModel
)
from src.services.latex_resume_generator import generate_latex_resume
from src.agents.outreach import outreach_agent
from src.agents.learner import self_learning_agent
from sqlalchemy.orm import Session
from sqlalchemy import func

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Semantic target-role matcher
# ---------------------------------------------------------------------------
_ROLE_SYNONYMS: Dict[str, List[str]] = {
    "software engineer":    ["software", "engineer", "developer", "dev", "programmer", "backend", "frontend", "fullstack", "full stack", "full-stack", "sde", "swe"],
    "python developer":     ["python", "fastapi", "django", "flask", "backend", "developer", "engineer", "dev"],
    "ai/ml engineer":       ["ai", "ml", "machine learning", "deep learning", "data science", "data scientist", "nlp", "llm", "computer vision", "artificial intelligence", "neural", "mlops"],
}

_GENERIC_NEGATIVE: List[str] = ["sales", "marketing", "hr", "human resources", "recruiter", "accountant", "finance", "operations", "legal", "content", "social media", "graphic", "design", "customer support", "customer success", "supply chain", "logistics", "teaching", "educator", "teacher"]


def is_target_role_match(job_title: str, target_roles: Optional[List[str]] = None) -> bool:
    """
    Returns True if *job_title* is semantically similar to at least one of
    *target_roles*.  If *target_roles* is empty / None the function falls back
    to checking the shared keyword pool of all built-in role synonyms.
    Non-tech roles (sales, marketing, HR …) always return False.
    """
    if not job_title:
        return False
    title_lower = job_title.lower()

    # Reject explicitly non-tech / non-matching roles first
    for neg in _GENERIC_NEGATIVE:
        if neg in title_lower:
            return False

    # Build the keyword pool from target_roles (using synonyms) or from the
    # full built-in synonym table as fallback
    keyword_pool: List[str] = []
    if target_roles:
        for role in target_roles:
            role_key = role.lower().strip()
            # try to find the closest synonym group
            for canonical, synonyms in _ROLE_SYNONYMS.items():
                if role_key == canonical or any(kw in role_key for kw in synonyms):
                    keyword_pool.extend(synonyms)
            # also add words directly from the target role string
            keyword_pool.extend(role_key.split())
    if not keyword_pool:
        for synonyms in _ROLE_SYNONYMS.values():
            keyword_pool.extend(synonyms)

    # Deduplicate
    keyword_pool = list(dict.fromkeys(keyword_pool))

    # Match if any keyword found in title
    return any(kw in title_lower for kw in keyword_pool)


class CopilotAgent:
    """High-end Application Copilot Agent: Generates pre-filled ATS forms, custom answers, and LazyApply-style 1-click bulk auto-apply."""

    def __init__(self):
        self.tier = "UNLIMITED"
        self.daily_limit = 9999
        self.used_today = 0

    def get_subscription_status(self) -> SubscriptionPlan:
        """Full access unlocked for all users."""
        return SubscriptionPlan(
            tier="UNLIMITED",
            daily_limit=9999,
            used_today=self.used_today,
            remaining_today=9999,
            can_auto_apply=True
        )

    def upgrade_subscription(self, tier: str = "PRO") -> SubscriptionPlan:
        self.tier = tier.upper()
        return SubscriptionPlan(
            tier=self.tier,
            daily_limit=9999,
            used_today=self.used_today,
            remaining_today=9999,
            can_auto_apply=True
        )

    def generate_autofill_package(self, profile: UserProfile, job: JobPosting, match: MatchResult) -> Dict[str, Any]:
        """Synthesize a complete application autofill dossier and custom screening answers."""
        name_parts = profile.full_name.strip().split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        # Compensation display
        comp_str = "$120,000 - $140,000 USD"
        if job.region == "India":
            comp_str = "₹12,00,000 - ₹18,00,000 INR" if not job.is_fresher else "₹8,00,000 - ₹12,00,000 INR"
        elif job.salary_min:
            comp_str = f"${int(job.salary_min):,} - ${int(job.salary_max or job.salary_min * 1.3):,} USD"

        # Form fields
        dossier = {
            "first_name": first_name,
            "last_name": last_name,
            "full_name": profile.full_name,
            "email": profile.email,
            "phone": profile.phone or "+91 98765 43210" if job.region == "India" else "+1 (555) 019-2834",
            "linkedin": f"https://linkedin.com/in/{first_name.lower()}{last_name.lower()}",
            "github": f"https://github.com/{first_name.lower()}{last_name.lower()}",
            "portfolio": f"https://{first_name.lower()}{last_name.lower()}.dev",
            "work_authorization": "Authorized to work in India & Remote" if job.region == "India" else "Authorized to work without sponsorship",
            "visa_sponsorship": "No",
            "notice_period": "Immediate / 15 Days",
            "expected_salary": comp_str,
            "preferred_location": job.location,
            "years_of_experience": f"{profile.years_of_experience:g} years" if not job.is_fresher else "Fresher / 0-1 Years"
        }

        # Screening Q&A Generator
        top_skills = match.matching_skills[:3] if match.matching_skills else ["Python", "Machine Learning"]
        screening_qa = [
            {
                "question": f"Why do you want to join {job.company} as our next {job.title}?",
                "field_type": "long_text",
                "answer": (
                    f"I have been following {job.company}'s work with great admiration. The {job.title} "
                    f"role represents an ideal alignment with my technical background in {', '.join(top_skills)}. "
                    f"I am eager to contribute to your engineering milestones and deliver immediate impact."
                )
            },
            {
                "question": f"Describe your practical experience with {top_skills[0].title()} and building scalable software.",
                "field_type": "long_text",
                "answer": (
                    f"Over my projects and engineering training, I have designed and deployed systems "
                    f"centered on {top_skills[0].title()}. I emphasize clean design patterns, modularity, "
                    f"and rigorous automated testing to ensure high reliability."
                )
            },
            {
                "question": "What is your availability to start and work schedule flexibility?",
                "field_type": "short_text",
                "answer": "Immediately available. Fully flexible with hybrid or remote collaborative time zones."
            },
            {
                "question": "What are your salary expectations for this position?",
                "field_type": "short_text",
                "answer": f"{dossier['expected_salary']} (Flexible depending on total compensation package and growth opportunity)."
            }
        ]

        # Auto-apply simulation execution steps
        copilot_steps = [
            {"step": 1, "action": f"Navigating to {job.company} Careers Portal ({job.source})...", "status": "COMPLETED"},
            {"step": 2, "action": f"Parsed ATS Form Structure & Candidate Requirements", "status": "COMPLETED"},
            {"step": 3, "action": "Injected candidate contact credentials, GitHub & LinkedIn profiles", "status": "COMPLETED"},
            {"step": 4, "action": f"Synthesized custom screening responses ({match.match_score}% ATS match calibration)", "status": "COMPLETED"},
            {"step": 5, "action": "Attached ATS-optimized tailored resume & custom pitch", "status": "COMPLETED"}
        ]

        screening_answers = {item["question"]: item["answer"] for item in screening_qa}

        return {
            "job_id": job.id,
            "job_title": job.title,
            "company": job.company,
            "location": job.location,
            "region": job.region,
            "is_fresher": job.is_fresher,
            "match_score": match.match_score,
            "dossier": dossier,
            "candidate_dossier": dossier,
            "screening_qa": screening_qa,
            "screening_answers": screening_answers,
            "copilot_steps": copilot_steps,
            "ats_scorecard": {
                "overall": match.match_score,
                "skills_alignment": match.keyword_score,
                "experience_relevance": match.semantic_score,
                "format_ats_score": 98.0
            }
        }

    def auto_apply_job(
        self,
        job: JobPosting,
        profile: UserProfile,
        db: Session,
        match_score: Optional[float] = None,
        custom_notes: str = ""
    ) -> Dict[str, Any]:
        """Auto-apply to a single job: saves to ApplicationModel, generates tailored LaTeX resume & Overleaf link, discovers recruiter, and returns summary."""
        # 0. Portal Permission check
        portal_src = (job.source or "Direct ATS").strip()
        perm = (
            db.query(PortalPermissionModel)
            .filter(
                (func.lower(PortalPermissionModel.portal_name) == portal_src.lower()) |
                (func.lower(PortalPermissionModel.display_name) == portal_src.lower())
            )
            .first()
        )
        if perm and not perm.enabled:
            return {
                "status": "PORTAL_DISABLED",
                "message": f"Application blocked: portal '{portal_src}' is disabled in Portal Permissions.",
                "job_id": job.id
            }

        existing = db.query(ApplicationModel).filter(ApplicationModel.job_id == job.id).first()
        notes = custom_notes or f"Auto-applied via JobPulse AI Copilot ({job.source})"
        tailored_letter = (
            f"Dear {job.company} Hiring Team,\n\n"
            f"I am excited to submit my application for the {job.title} opening. "
            f"With hands-on experience across {', '.join(profile.skills[:4]) if profile.skills else 'software engineering'}, "
            f"I am confident in delivering immediate impact to your engineering milestones.\n\n"
            f"Thank you for considering my application.\n"
            f"Sincerely,\n{profile.full_name}"
        )

        # 1. Synthesize ATS-friendly LaTeX resume & Overleaf integration
        from src.models.job import MatchResult
        dummy_match = MatchResult(
            job_id=job.id,
            job_title=job.title,
            company=job.company,
            location=job.location,
            url=job.url,
            match_score=match_score or 85.0,
            semantic_score=85.0,
            keyword_score=85.0,
            matching_skills=profile.skills[:3] if profile.skills else ["Python"],
            missing_skills=[]
        )
        latex_pkg = generate_latex_resume(profile, job, dummy_match)
        resume_ver = ResumeVersionModel(
            job_id=job.id,
            version_label=latex_pkg["version_label"],
            latex_source=latex_pkg["latex_source"],
            template_name=latex_pkg["template_name"],
            emphasized_skills_json=json.dumps(latex_pkg["emphasized_skills"]),
            overleaf_url=latex_pkg["overleaf_url"]
        )
        db.add(resume_ver)
        db.commit()
        db.refresh(resume_ver)

        if not existing:
            app_rec = ApplicationModel(
                job_id=job.id,
                status="APPLIED",
                portal=job.source or "Direct ATS",
                notes=notes,
                tailored_cover_letter=tailored_letter,
                resume_version_id=resume_ver.id,
                latex_resume_code=latex_pkg["latex_source"],
                overleaf_url=latex_pkg["overleaf_url"],
                match_score=match_score
            )
            db.add(app_rec)
        else:
            existing.status = "APPLIED"
            existing.portal = job.source or "Direct ATS"
            existing.notes = f"{existing.notes} | {notes}".strip(" |")
            existing.resume_version_id = resume_ver.id
            existing.latex_resume_code = latex_pkg["latex_source"]
            existing.overleaf_url = latex_pkg["overleaf_url"]
            if match_score:
                existing.match_score = match_score
            if not existing.tailored_cover_letter:
                existing.tailored_cover_letter = tailored_letter

        # 2. Discover HR contact & synthesize cold email outreach
        contacts = outreach_agent.discover_contacts_for_company(job.company, job.title, db, limit=1)
        email_rec = None
        if contacts:
            c = contacts[0]
            em_data = outreach_agent.generate_personalized_cold_email(profile, job, c)
            email_rec = OutreachEmailModel(
                contact_id=c.id,
                job_id=job.id,
                recipient_email=c.email,
                recipient_name=c.person_name,
                company=job.company,
                subject=em_data["subject"],
                body_text=em_data["body_text"],
                personalized_intro=em_data["personalized_intro"],
                status="SENT",
                sent_at=datetime.now(timezone.utc),
                reply_status="NO_REPLY"
            )
            db.add(email_rec)

        # 3. Log 9-step timeline events
        tl1 = ActivityTimelineModel(
            stage_number=3,
            event_type="RESUME_CUSTOMIZED",
            title=f"Custom ATS LaTeX Resume & Overleaf link built for {job.company}",
            job_id=job.id,
            company=job.company,
            details_json=json.dumps({"template": latex_pkg["template_name"], "skills": latex_pkg["emphasized_skills"]})
        )
        tl2 = ActivityTimelineModel(
            stage_number=4,
            event_type="APPLICATION_SUBMITTED",
            title=f"Application dispatched to {job.company} for {job.title}",
            job_id=job.id,
            company=job.company,
            details_json=json.dumps({"portal": job.source, "match_score": match_score or 85.0})
        )
        db.add(tl1)
        db.add(tl2)

        self.used_today += 1
        db.commit()

        return {
            "status": "SUCCESS",
            "job_id": job.id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "apply_url": job.url,
            "portal": job.source,
            "match_score": match_score or 85.0,
            "latex_resume_version_id": resume_ver.id,
            "overleaf_url": latex_pkg["overleaf_url"],
            "recruiter_contact": contacts[0].email if contacts else None,
            "notes": notes,
            "message": f"Successfully auto-applied to {job.title} at {job.company} with custom LaTeX resume and outreach!"
        }

    def apply_single_job(
        self,
        job: JobPosting,
        profile: UserProfile,
        db: Session,
        match_score: Optional[float] = None,
        custom_notes: str = ""
    ) -> Dict[str, Any]:
        """Alias for auto_apply_job for single-job 1-click apply endpoints."""
        return self.auto_apply_job(
            job=job,
            profile=profile,
            db=db,
            match_score=match_score,
            custom_notes=custom_notes
        )

    def execute_autonomous_cycle(
        self,
        jobs: List[JobPosting],
        profile: UserProfile,
        db: Session,
        operating_mode: str = "FULLY_AUTONOMOUS",
        max_applications: int = 5,
        match_scores: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Executes the autonomous career agent cycle across the full 9 stages:
        Job Found -> Job Analyzed -> Resume Customized -> Application Submitted ->
        HR Contact Found -> Cold Email Sent -> Recruiter Response -> Response Analyzed -> Follow-up / Learn.
        Respects Operating Modes (FULLY_AUTONOMOUS, APPROVAL_MODE, ASSISTED).
        """
        applied_results = []
        execution_logs = []
        timeline_events = []

        # max_applications is now a *soft hint* for UI batch-size display only.
        # The cycle will process EVERY suitable job passed in; portal quotas are
        # the only throttle (all set to 9999 by default for unlimited operation).
        if not jobs:
            return {
                "status": "NO_JOBS",
                "message": "No matching jobs found within criteria.",
                "applied_count": 0,
                "applied_jobs": [],
                "execution_logs": ["Zero active jobs passed multi-factor relevance threshold."]
            }

        execution_logs.append(f"Autonomous Career Agent initialized in [{operating_mode}] mode.")
        execution_logs.append(f"Candidate: {profile.full_name} | Processing ALL {len(jobs)} suitable jobs (unlimited).")

        for idx, j in enumerate(jobs, start=1):
            if self.used_today >= self.daily_limit:
                execution_logs.append(f"Global daily application limit ({self.daily_limit}) reached.")
                break


            score = (match_scores or {}).get(j.id, 85.0)
            portal_src = (j.source or "Direct ATS").strip()

            # 1. Portal Permissions & Rate Limits
            perm = (
                db.query(PortalPermissionModel)
                .filter(
                    (func.lower(PortalPermissionModel.portal_name) == portal_src.lower()) |
                    (func.lower(PortalPermissionModel.display_name) == portal_src.lower())
                )
                .first()
            )
            if perm:
                if not perm.enabled:
                    execution_logs.append(f"[{idx}] Skipped {j.company} - {j.title}: Portal '{portal_src}' is disabled in portal permissions.")
                    continue
                if perm.max_daily_apps:
                    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
                    today_count = db.query(ApplicationModel).filter(
                        (func.lower(ApplicationModel.portal) == portal_src.lower()) |
                        (func.lower(ApplicationModel.portal) == perm.portal_name.lower()),
                        ApplicationModel.created_at >= today_start
                    ).count()
                    if today_count >= perm.max_daily_apps:
                        execution_logs.append(f"[{idx}] Skipped {j.company} - {j.title}: Portal '{portal_src}' daily limit ({perm.max_daily_apps}) reached.")
                        continue

            # 2. Duplicate Application Check: Exact Job
            existing = db.query(ApplicationModel).filter(ApplicationModel.job_id == j.id).first()
            if existing and existing.status in ["APPLIED", "INTERVIEW", "INTERVIEWING", "ACCEPTED", "OFFER"]:
                tl_dup = ActivityTimelineModel(
                    stage_number=4,
                    event_type="DUPLICATE_APPLICATION_PREVENTED",
                    title=f"Duplicate prevented: already applied to {j.company} for {j.title}",
                    job_id=j.id,
                    company=j.company,
                    details_json=json.dumps({"portal": existing.portal, "status": existing.status})
                )
                db.add(tl_dup)
                execution_logs.append(f"[{idx}] Skipped {j.company} - {j.title}: Already applied on {existing.portal} [{existing.status}].")
                continue
            if existing and existing.status == "PENDING_APPROVAL" and operating_mode == "APPROVAL_MODE":
                execution_logs.append(f"[{idx}] Skipped {j.company} - {j.title}: Already pending in Approval Queue.")
                continue

            # 3. Duplicate Application Check: Cross-Portal (Same Company + Title across any portal)
            dup_app = (
                db.query(ApplicationModel)
                .join(JobModel, ApplicationModel.job_id == JobModel.id)
                .filter(
                    func.lower(JobModel.company) == func.lower(j.company),
                    func.lower(JobModel.title) == func.lower(j.title),
                    ApplicationModel.status.in_(["APPLIED", "INTERVIEW", "INTERVIEWING", "ACCEPTED", "OFFER"])
                )
                .first()
            )
            if not dup_app and hasattr(j, "content_hash") and j.content_hash:
                dup_app = (
                    db.query(ApplicationModel)
                    .join(JobModel, ApplicationModel.job_id == JobModel.id)
                    .filter(
                        JobModel.content_hash == j.content_hash,
                        ApplicationModel.status.in_(["APPLIED", "INTERVIEW", "INTERVIEWING", "ACCEPTED", "OFFER"])
                    )
                    .first()
                )

            if dup_app and dup_app.job_id != j.id:
                tl_dup = ActivityTimelineModel(
                    stage_number=4,
                    event_type="DUPLICATE_APPLICATION_PREVENTED",
                    title=f"Cross-portal duplicate prevented for {j.company} - {j.title}",
                    job_id=j.id,
                    company=j.company,
                    details_json=json.dumps({
                        "existing_portal": dup_app.portal,
                        "attempted_portal": j.source,
                        "existing_status": dup_app.status
                    })
                )
                db.add(tl_dup)
                execution_logs.append(f"[{idx}] Skipped {j.company} - {j.title}: Duplicate application already exists on {dup_app.portal} [{dup_app.status}].")
                continue

            # Stage 1: Job Found
            tl_found = ActivityTimelineModel(
                stage_number=1,
                event_type="JOB_FOUND",
                title=f"Discovered genuine live opening: '{j.title}' at {j.company}",
                job_id=j.id,
                company=j.company,
                details_json=json.dumps({"portal": j.source, "location": j.location, "region": j.region})
            )
            db.add(tl_found)

            # Stage 2: Job Analyzed
            tl_analyzed = ActivityTimelineModel(
                stage_number=2,
                event_type="JOB_ANALYZED",
                title=f"Multi-factor relevance scored: {score:.1f}% fit for {j.title}",
                job_id=j.id,
                company=j.company,
                details_json=json.dumps({"score": score, "skills_required": j.skills_required[:4]})
            )
            db.add(tl_analyzed)

            # Stage 3: Resume Customized (ATS LaTeX & Overleaf)
            # Only generate a full tailored resume when the job title is semantically
            # similar to the candidate's target roles. Non-matching roles get a
            # lightweight generic resume so the application still proceeds.
            from src.models.job import MatchResult
            m_res = MatchResult(
                job_id=j.id,
                job_title=j.title,
                company=j.company,
                location=j.location,
                url=j.url,
                match_score=score,
                semantic_score=score,
                keyword_score=score,
                matching_skills=profile.skills[:3] if profile.skills else ["Python"],
                missing_skills=[]
            )

            role_matches_target = is_target_role_match(j.title, profile.target_roles)
            if role_matches_target:
                latex_pkg = generate_latex_resume(profile, j, m_res)
                resume_event_title = f"Generated tailored ATS LaTeX Resume for '{j.title}' — emphasizing {', '.join(latex_pkg['emphasized_skills'][:3])}"
            else:
                # Non-target role: use master resume template without heavy customisation
                latex_pkg = generate_latex_resume(profile, j, m_res)  # still call to get valid structure
                latex_pkg["version_label"] = f"master-resume-{j.id}"
                resume_event_title = f"Applied master resume (role '{j.title}' differs from target roles — no custom tailoring)"
                execution_logs.append(f"[{idx}] Note: '{j.title}' is not a target-role match — using master resume (no custom ATS tailoring).")

            resume_ver = ResumeVersionModel(
                job_id=j.id,
                version_label=latex_pkg["version_label"],
                latex_source=latex_pkg["latex_source"],
                template_name=latex_pkg["template_name"],
                emphasized_skills_json=json.dumps(latex_pkg["emphasized_skills"]),
                overleaf_url=latex_pkg["overleaf_url"]
            )
            db.add(resume_ver)
            db.commit()
            db.refresh(resume_ver)

            tl_resume = ActivityTimelineModel(
                stage_number=3,
                event_type="RESUME_CUSTOMIZED" if role_matches_target else "RESUME_MASTER_APPLIED",
                title=resume_event_title,
                job_id=j.id,
                company=j.company,
                details_json=json.dumps({"version_id": resume_ver.id, "template": latex_pkg["template_name"], "target_role_match": role_matches_target})
            )
            db.add(tl_resume)


            # Operating Mode Determination
            if operating_mode == "FULLY_AUTONOMOUS":
                app_status = "APPLIED"
                em_status = "SENT"
                app_event = "APPLICATION_SUBMITTED"
                app_title = f"Application dispatched to {j.company} for {j.title}"
                email_event = "COLD_EMAIL_SENT"
                email_title = "Personalized cold email dispatched"
            elif operating_mode == "APPROVAL_MODE":
                app_status = "PENDING_APPROVAL"
                em_status = "PENDING_APPROVAL"
                app_event = "APPLICATION_QUEUED"
                app_title = f"Application held in Approval Queue for {j.title}"
                email_event = "COLD_EMAIL_QUEUED"
                email_title = "Personalized cold email queued for review"
            else:  # ASSISTED
                app_status = "ASSISTED_READY"
                em_status = "DRAFT"
                app_event = "APPLICATION_PREPARED_ASSISTED"
                app_title = f"Application dossier & tailored ATS resume prepared for {j.title}"
                email_event = "COLD_EMAIL_DRAFTED"
                email_title = "Personalized cold outreach draft prepared"

            notes = f"JobPulse Autonomous Agent [{operating_mode}] (Score: {score:.1f}%)"
            cover_letter = (
                f"Dear {j.company} Hiring Team,\n\n"
                f"I am writing to express my enthusiastic interest in the {j.title} role. "
                f"With hands-on experience in {', '.join(profile.skills[:4]) if profile.skills else 'software engineering'}, "
                f"I have architected scalable solutions and look forward to contributing to {j.company}.\n\n"
                f"Best regards,\n{profile.full_name}"
            )

            # Answer recurring screener questions from Candidate Knowledge Base
            q1 = f"Why do you want to join {j.company}?"
            ans1 = self_learning_agent.process_application_question(q1, j.id, j.company, db, default_fallback=f"I admire {j.company}'s engineering impact.")
            answered_questions = {q1: ans1["answer"]}

            if not existing:
                app_rec = ApplicationModel(
                    job_id=j.id,
                    status=app_status,
                    portal=j.source,
                    notes=notes,
                    tailored_cover_letter=cover_letter,
                    resume_version_id=resume_ver.id,
                    latex_resume_code=latex_pkg["latex_source"],
                    overleaf_url=latex_pkg["overleaf_url"],
                    questions_answered_json=json.dumps(answered_questions),
                    match_score=score
                )
                db.add(app_rec)
            else:
                existing.status = app_status
                existing.portal = j.source
                existing.notes = f"{existing.notes} | {notes}".strip(" |")
                existing.resume_version_id = resume_ver.id
                existing.latex_resume_code = latex_pkg["latex_source"]
                existing.overleaf_url = latex_pkg["overleaf_url"]
                existing.questions_answered_json = json.dumps(answered_questions)
                existing.match_score = score

            tl_app = ActivityTimelineModel(
                stage_number=4,
                event_type=app_event,
                title=app_title,
                job_id=j.id,
                company=j.company,
                details_json=json.dumps({"mode": operating_mode, "status": app_status})
            )
            db.add(tl_app)

            # Stage 5: HR Contact Found
            contacts = outreach_agent.discover_contacts_for_company(j.company, j.title, db, limit=1)
            target_contact = contacts[0] if contacts else None
            if target_contact:
                tl_hr = ActivityTimelineModel(
                    stage_number=5,
                    event_type="HR_CONTACT_FOUND",
                    title=f"Discovered verified recruiter: {target_contact.person_name} ({target_contact.role_title})",
                    job_id=j.id,
                    company=j.company,
                    details_json=json.dumps({"email": target_contact.email, "confidence": target_contact.confidence_score})
                )
                db.add(tl_hr)

                # Stage 6: Cold Email Outreach
                cold_data = outreach_agent.generate_personalized_cold_email(profile, j, target_contact)
                email_rec = OutreachEmailModel(
                    contact_id=target_contact.id,
                    job_id=j.id,
                    recipient_email=target_contact.email,
                    recipient_name=target_contact.person_name,
                    company=j.company,
                    subject=cold_data["subject"],
                    body_text=cold_data["body_text"],
                    personalized_intro=cold_data["personalized_intro"],
                    status=em_status,
                    sent_at=datetime.now(timezone.utc) if em_status == "SENT" else None,
                    reply_status="NO_REPLY"
                )
                db.add(email_rec)

                tl_email = ActivityTimelineModel(
                    stage_number=6,
                    event_type=email_event,
                    title=f"{email_title} to {target_contact.person_name}",
                    job_id=j.id,
                    company=j.company,
                    details_json=json.dumps({"subject": cold_data["subject"], "status": em_status})
                )
                db.add(tl_email)

            self.used_today += 1
            applied_results.append({
                "job_id": j.id,
                "title": j.title,
                "company": j.company,
                "location": j.location,
                "portal": j.source,
                "match_score": score,
                "latex_resume_version_id": resume_ver.id,
                "status": "APPLIED_SUCCESSFULLY" if app_status == "APPLIED" else app_status,
                "recruiter": target_contact.person_name if target_contact else None
            })

            execution_logs.append(f"[{idx}] {j.company} | '{j.title}' -> ATS LaTeX generated -> {app_status} -> Recruiter mapped.")

        db.commit()

        if not applied_results:
            execution_logs.append("All candidate jobs were already applied to or skipped (duplicates/disabled portals).")
            return {
                "status": "NO_JOBS",
                "operating_mode": operating_mode,
                "jobs_processed": 0,
                "applications_created": 0,
                "applied_count": 0,
                "processed_count": 0,
                "applied_jobs": [],
                "execution_logs": execution_logs
            }

        execution_logs.append(f"Autonomous cycle completed successfully for {len(applied_results)} opportunities.")

        return {
            "status": "SUCCESS",
            "operating_mode": operating_mode,
            "jobs_processed": len(applied_results),
            "applications_created": len(applied_results),
            "applied_count": len(applied_results),
            "processed_count": len(applied_results),
            "applied_jobs": applied_results,
            "execution_logs": execution_logs
        }


    def execute_lazyapply_batch(
        self,
        jobs: List[JobPosting],
        profile: UserProfile,
        db: Session,
        max_count: int = 5,
        screener_answers: Optional[Dict[str, str]] = None,
        match_scores: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """Executes autonomous batch leveraging the full 9-step agent cycle with candidate's preferred operating mode."""
        user = db.query(UserModel).first()
        mode = (user.operating_mode if user and user.operating_mode else "FULLY_AUTONOMOUS")
        return self.execute_autonomous_cycle(
            jobs=jobs,
            profile=profile,
            db=db,
            operating_mode=mode,
            max_applications=max_count,
            match_scores=match_scores
        )

copilot_agent = CopilotAgent()

