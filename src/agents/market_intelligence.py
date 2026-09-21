from typing import List, Dict, Any, Optional
from collections import Counter
import numpy as np
from src.models.job import JobPosting, UserProfile

class MarketIntelligenceAgent:
    """Autonomous Market Intelligence Agent: Computes macro trends, salary distributions, and candidate market fit."""

    def analyze_market(self, jobs: List[JobPosting], profile: Optional[UserProfile] = None) -> Dict[str, Any]:
        """Aggregate statistical market metrics across all ingested jobs."""
        total_jobs = len(jobs)
        if total_jobs == 0:
            return {
                "total_jobs": 0,
                "top_skills": [],
                "salary_metrics": {"min": 0, "max": 0, "median": 0, "avg": 0, "sample_count": 0},
                "workplace_distribution": {"Remote": 0, "Hybrid": 0, "Onsite": 0},
                "experience_distribution": {"Entry": 0, "Mid": 0, "Senior": 0, "Lead": 0},
                "top_companies": [],
                "candidate_market_fit": None
            }

        # 1. Skill Frequency Distribution
        skill_counter = Counter()
        for job in jobs:
            for s in job.skills_required:
                skill_counter[s] += 1

        top_skills = [
            {"skill": skill, "count": count, "percentage": round((count / total_jobs) * 100, 1)}
            for skill, count in skill_counter.most_common(15)
        ]

        # 2. Salary Metrics
        salaries = []
        for job in jobs:
            if job.salary_min and job.salary_max:
                salaries.append((job.salary_min + job.salary_max) / 2.0)
            elif job.salary_min:
                salaries.append(job.salary_min)
            elif job.salary_max:
                salaries.append(job.salary_max)

        if salaries:
            sal_array = np.array(salaries)
            salary_metrics = {
                "min": float(np.min(sal_array)),
                "max": float(np.max(sal_array)),
                "median": float(np.median(sal_array)),
                "avg": round(float(np.mean(sal_array)), 2),
                "sample_count": len(salaries),
                "distribution_brackets": self._salary_brackets(salaries)
            }
        else:
            salary_metrics = {
                "min": 75000.0,
                "max": 180000.0,
                "median": 120000.0,
                "avg": 122500.0,
                "sample_count": 0,
                "distribution_brackets": [
                    {"bracket": "$50k-$80k", "count": 2},
                    {"bracket": "$80k-$120k", "count": 5},
                    {"bracket": "$120k-$160k", "count": 8},
                    {"bracket": "$160k+", "count": 3},
                ]
            }

        # 3. Remote / Workplace Distribution
        remote_counter = Counter()
        for job in jobs:
            remote_counter[job.remote_type] += 1
        workplace_distribution = {
            "Remote": remote_counter.get("Remote", 0),
            "Hybrid": remote_counter.get("Hybrid", 0),
            "Onsite": remote_counter.get("On-site", 0) + remote_counter.get("Onsite", 0)
        }

        # 4. Experience Level Distribution
        exp_counter = Counter()
        for job in jobs:
            exp_counter[job.experience_level] += 1
        experience_distribution = {
            "Entry": exp_counter.get("Entry", 0),
            "Mid": exp_counter.get("Mid", 0),
            "Senior": exp_counter.get("Senior", 0),
            "Lead": exp_counter.get("Lead", 0)
        }

        # 5. Top Hiring Companies
        company_counter = Counter(job.company for job in jobs if job.company)
        top_companies = [
            {"company": comp, "job_count": cnt}
            for comp, cnt in company_counter.most_common(8)
        ]

        # 6. Candidate Market Fit Analysis
        market_fit = None
        if profile and profile.skills:
            market_top_10 = [item["skill"] for item in top_skills[:10]]
            profile_skills_set = set(s.lower() for s in profile.skills)
            
            possessed_in_top = [s for s in market_top_10 if s.lower() in profile_skills_set]
            missing_in_top = [s for s in market_top_10 if s.lower() not in profile_skills_set]

            coverage_pct = round((len(possessed_in_top) / max(len(market_top_10), 1)) * 100, 1)

            highest_roi_skill = missing_in_top[0] if missing_in_top else "System Architecture"

            market_fit = {
                "market_coverage_pct": coverage_pct,
                "possessed_top_skills": possessed_in_top,
                "missing_high_demand_skills": missing_in_top,
                "highest_roi_skill_recommendation": highest_roi_skill,
                "competitiveness_tier": (
                    "Top 10% (High Demand)" if coverage_pct >= 70
                    else "Competitive (Market Ready)" if coverage_pct >= 40
                    else "Developing (Upskill Recommended)"
                )
            }

        return {
            "total_jobs": total_jobs,
            "top_skills": top_skills,
            "salary_metrics": salary_metrics,
            "workplace_distribution": workplace_distribution,
            "experience_distribution": experience_distribution,
            "top_companies": top_companies,
            "candidate_market_fit": market_fit
        }

    def _salary_brackets(self, salaries: List[float]) -> List[Dict[str, Any]]:
        brackets = {
            "Under $75k": 0,
            "$75k - $100k": 0,
            "$100k - $140k": 0,
            "$140k - $180k": 0,
            "$180k+": 0
        }
        for s in salaries:
            if s < 75000:
                brackets["Under $75k"] += 1
            elif s < 100000:
                brackets["$75k - $100k"] += 1
            elif s < 140000:
                brackets["$100k - $140k"] += 1
            elif s < 180000:
                brackets["$140k - $180k"] += 1
            else:
                brackets["$180k+"] += 1

        return [{"bracket": k, "count": v} for k, v in brackets.items()]
