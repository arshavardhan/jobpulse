import logging
from typing import Dict, Any, List
from src.models.job import JobPosting, UserProfile, MatchResult
from src.models.application import TailoredPackage
from src.agents.llm_provider import llm

logger = logging.getLogger(__name__)

class TailorAgent:
    """Autonomous Tailor Agent: Generates tailored ATS cover letters, resume bullet points, and interview prep guides."""

    def generate_tailored_package(self, profile: UserProfile, job: JobPosting, match: MatchResult) -> TailoredPackage:
        """Create a complete customized application package for a target job."""
        cover_letter = self._create_cover_letter(profile, job, match)
        resume_bullets = self._create_resume_bullets(profile, job, match)
        interview_qa = self._create_interview_qa(profile, job, match)

        return TailoredPackage(
            job_id=job.id,
            job_title=job.title,
            company=job.company,
            cover_letter=cover_letter,
            resume_bullet_recommendations=resume_bullets,
            interview_prep_qa=interview_qa,
            custom_pitch=match.suggested_pitch
        )

    def _create_cover_letter(self, profile: UserProfile, job: JobPosting, match: MatchResult) -> str:
        """Generate high-impact tailored cover letter."""
        matched_skills_str = ", ".join(match.matching_skills[:5]) if match.matching_skills else "Python and modern software engineering"
        
        prompt = (
            f"Write a compelling, professional cover letter for {profile.full_name} applying for the {job.title} "
            f"role at {job.company}.\n"
            f"Candidate Skills: {', '.join(profile.skills)}\n"
            f"Key Matching Skills: {matched_skills_str}\n"
            f"Years of Experience: {profile.years_of_experience}\n"
            f"Job Description Excerpt: {job.description[:600]}\n"
            f"Make the tone enthusiastic, confident, and metrics-driven. Avoid clichés."
        )

        if llm.provider != "heuristic":
            try:
                res = llm.generate(prompt)
                if res and len(res) > 100:
                    return res
            except Exception as e:
                logger.warning(f"LLM generation failed in cover letter, falling back to template: {e}")

        # Intelligent Dynamic Template Fallback
        letter = f"""Dear Hiring Team at {job.company},

I am writing to express my enthusiastic interest in the {job.title} position. With over {profile.years_of_experience:g} years of engineering experience and a strong background in {matched_skills_str}, I have built scalable, data-driven systems that align directly with {job.company}'s mission.

In reviewing the requirements for {job.title}, I noted your focus on {', '.join(job.skills_required[:3]) if job.skills_required else 'high-performance execution'}. Throughout my work, I have consistently applied {', '.join(match.matching_skills[:3]) if match.matching_skills else 'core engineering practices'} to solve complex challenges, improve throughput, and deliver clean, maintainable code.

Key highlights of my background include:
• Designed and orchestrated end-to-end automated pipelines leveraging {matched_skills_str}, reducing latency and improving data quality.
• Architected robust backend and analytics workflows with a continuous focus on testability, reliability, and modularity.
• Demonstrated rapid learning agility, swiftly adopting complementary technologies like {', '.join(match.missing_skills[:2]) if match.missing_skills else 'emerging frameworks'} to deliver cross-functional value.

I am particularly inspired by {job.company}'s work and would welcome the opportunity to discuss how my technical skills and proactive problem-solving mindset can contribute to your team's upcoming milestones.

Thank you for your time and consideration.

Sincerely,
{profile.full_name}
{profile.email}
"""
        return letter.strip()

    def _create_resume_bullets(self, profile: UserProfile, job: JobPosting, match: MatchResult) -> List[str]:
        """Generate ATS-optimized resume bullet points tailored to the target job."""
        top_skill = match.matching_skills[0] if match.matching_skills else "Python"
        second_skill = match.matching_skills[1] if len(match.matching_skills) > 1 else "data engineering"
        
        bullets = [
            f"Architected and deployed production pipelines using {top_skill} and {second_skill}, driving a 35% improvement in processing efficiency and operational reliability.",
            f"Streamlined automated data ingestion workflows and API integrations, processing over 100,000+ records daily with 99.8% uptime.",
            f"Collaborated with cross-functional teams to integrate modern {job.title} best practices, reducing cycle time and enhancing ATS compliance."
        ]
        return bullets

    def _create_interview_qa(self, profile: UserProfile, job: JobPosting, match: MatchResult) -> List[Dict[str, str]]:
        """Generate tailored interview preparation questions and strategic response outlines."""
        primary_skill = match.matching_skills[0] if match.matching_skills else "Python"
        
        return [
            {
                "question": f"How have you utilized {primary_skill.title()} in past production environments, and what trade-offs did you face?",
                "talking_points": (
                    f"Highlight architecture decisions, memory/runtime optimizations, error handling, "
                    f"and how you ensured test coverage when deploying {primary_skill.title()} solutions."
                ),
                "category": "Technical Architecture"
            },
            {
                "question": f"In the context of the {job.title} position at {job.company}, how do you approach unblocking ambiguity in data or requirements?",
                "talking_points": (
                    "Discuss breaking down tasks, communicating with stakeholders, setting up rapid prototyping cycles, "
                    "and using logging/analytics to validate assumptions."
                ),
                "category": "Problem Solving & Execution"
            },
            {
                "question": f"What experience do you have with {', '.join(match.missing_skills[:2]) if match.missing_skills else 'system design scaling'}?",
                "talking_points": (
                    "Acknowledge where your expertise bridges the gap, mention related conceptual foundations, "
                    "and cite an example of how rapidly you mastered a new technology in your past roles."
                ),
                "category": "Skill Gap Mitigation"
            }
        ]
