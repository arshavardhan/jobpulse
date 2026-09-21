import re
import urllib.parse
from typing import Dict, Any, List, Optional
from datetime import datetime
from src.models.job import JobPosting, UserProfile, MatchResult

def escape_latex(text: str) -> str:
    """Escapes special LaTeX characters to guarantee syntax validity."""
    if not text:
        return ""
    # Ordering matters: backslash first
    s = str(text)
    replacements = [
        ('\\', r'\textbackslash{}'),
        ('&', r'\&'),
        ('%', r'\%'),
        ('$', r'\$'),
        ('#', r'\#'),
        ('_', r'\_'),
        ('{', r'\{'),
        ('}', r'\}'),
        ('~', r'\textasciitilde{}'),
        ('^', r'\textasciicircum{}')
    ]
    for orig, rep in replacements:
        s = s.replace(orig, rep)
    return s

def generate_latex_resume(
    profile: UserProfile,
    job: JobPosting,
    match: Optional[MatchResult] = None,
    template_name: str = "Modern ATS LaTeX"
) -> Dict[str, Any]:
    """
    Generates compile-ready, ATS-compliant LaTeX resume source code emphasizing
    the target job's matching skills, relevant projects, and keywords.
    """
    # 1. Candidate Info
    full_name = escape_latex(profile.full_name or "Candidate Name")
    email = escape_latex(profile.email or "candidate@example.com")
    phone = escape_latex(profile.phone or "+91 98765 43210")
    location = escape_latex(profile.preferred_locations[0] if profile.preferred_locations else "Bengaluru, India")
    target_role = escape_latex(job.title or "Software Engineer")
    target_company = escape_latex(job.company or "Target Company")

    name_slug = re.sub(r'[^a-zA-Z0-9]', '', profile.full_name.lower()) or "candidate"
    linkedin_link = f"https://linkedin.com/in/{name_slug}"
    github_link = f"https://github.com/{name_slug}"
    portfolio_link = f"https://{name_slug}.dev"

    # 2. Emphasized Skills (Match vs Profile)
    matching_skills = [s.title() for s in match.matching_skills] if match and match.matching_skills else []
    all_profile_skills = [s.title() for s in profile.skills] if profile.skills else ["Python", "FastAPI", "SQL", "Docker", "Git"]
    
    # Priority order: matching skills first, then rest of profile skills
    seen = set()
    prioritized_skills = []
    for s in matching_skills + all_profile_skills:
        if s.lower() not in seen:
            seen.add(s.lower())
            prioritized_skills.append(s)

    primary_skills_str = escape_latex(", ".join(prioritized_skills[:7]))
    secondary_skills_str = escape_latex(", ".join(prioritized_skills[7:14])) if len(prioritized_skills) > 7 else "Git, Docker, Linux, CI/CD, Microservices, Agile"

    # 3. Dynamic Tailored Summary
    summary_text = (
        f"Results-driven {target_role} with {profile.years_of_experience:g}+ years of experience designing and deploying "
        f"scalable systems. Proficient across {primary_skills_str}. Proven track record delivering "
        f"high-reliability solutions, optimizing performance, and aligning engineering milestones with business objectives at {target_company}."
    )
    summary_latex = escape_latex(summary_text)

    # 4. Tailored Experience Bullets (Google XYZ format: Accomplished [X] as measured by [Y] by doing [Z])
    top_skill = matching_skills[0] if matching_skills else "Python"
    second_skill = matching_skills[1] if len(matching_skills) > 1 else "FastAPI"
    third_skill = matching_skills[2] if len(matching_skills) > 2 else "SQL"

    bullets = [
        f"Architected and deployed high-throughput data processing workflows leveraging {top_skill} and {second_skill}, improving query efficiency by 38% and reducing memory footprints.",
        f"Spearheaded the design of modular RESTful and asynchronous microservices using {second_skill}, maintaining 99.9% operational uptime across peak production loads.",
        f"Integrated automated testing and CI/CD validation pipelines, increasing code coverage to 92% and cutting release regression bugs by 45%.",
        f"Collaborated with cross-functional product and engineering teams to accelerate feature delivery cycles, incorporating {third_skill} and modern cloud best practices."
    ]
    bullets_latex = "\n".join([f"    \\item {escape_latex(b)}" for b in bullets])

    # 5. Tailored Projects
    projects = [
        {
            "name": f"Autonomous Job Discovery & Application Engine",
            "tech": f"{top_skill}, {second_skill}, SQLite, REST API",
            "bullets": [
                f"Built an autonomous multi-source job ingestion engine crawling 1,000+ live verified career postings.",
                f"Implemented hybrid TF-IDF semantic relevance ranking and 1-click ATS application workflow."
            ]
        },
        {
            "name": f"High-Performance {second_skill} Microservice Architecture",
            "tech": f"{second_skill}, {third_skill}, Docker, Redis",
            "bullets": [
                f"Designed distributed caching and rate-limiting middleware capable of handling 5,000+ concurrent requests.",
                f"Reduced p99 latency from 320ms to 85ms while cutting infrastructure resource utilization by 25%."
            ]
        }
    ]

    projects_latex_blocks = []
    for p in projects:
        p_name = escape_latex(p["name"])
        p_tech = escape_latex(p["tech"])
        p_bullets = "\n".join([f"    \\item {escape_latex(b)}" for b in p["bullets"]])
        projects_latex_blocks.append(f"""\\textbf{{{p_name}}} $|$ \\emph{{{p_tech}}}
\\begin{{itemize}}[leftmargin=0.15in, label=\\textbullet, noitemsep, topsep=1pt]
{p_bullets}
\\end{{itemize}}
\\vspace{{4pt}}""")

    all_projects_latex = "\n".join(projects_latex_blocks)

    # 6. Education
    edu_degree = "Bachelor of Technology in Computer Science & Engineering"
    edu_inst = "Institute of Technology"
    edu_year = "2020 -- 2024"

    # Assemble complete standard LaTeX document
    latex_source = f"""%------------------------------------------------------------------------------
% JobPulse ATS-Friendly LaTeX Resume
% Generated for: {target_role} at {target_company}
% Date: {datetime.now().strftime('%B %d, %Y')}
%------------------------------------------------------------------------------

\\documentclass[letterpaper,10.5pt]{{article}}
\\usepackage[empty]{{fullpage}}
\\usepackage{{titlesec}}
\\usepackage{{marvosym}}
\\usepackage[usenames,dvipsnames]{{color}}
\\usepackage{{verbatim}}
\\usepackage{{enumitem}}
\\usepackage[hidelinks]{{hyperref}}
\\usepackage{{fancyhdr}}
\\usepackage[english]{{babel}}
\\usepackage{{tabularx}}
\\usepackage{{geometry}}

\\geometry{{left=0.6in,top=0.5in,right=0.6in,bottom=0.5in}}

\\pagestyle{{fancy}}
\\fancyhf{{}}
\\renewcommand{{\\headrulewidth}}{{0pt}}
\\renewcommand{{\\footrulewidth}}{{0pt}}

% Section formatting
\\titleformat{{\\section}}{{
  \\vspace{{-4pt}}\\scshape\\raggedright\\large
}}{{}}{{0em}}{{}}[\\color{{black}}\\titlerule \\vspace{{-4pt}}]

\\begin{{document}}

%----------HEADING----------
\\begin{{center}}
    \\textbf{{\\Huge \\scshape {full_name}}} \\\\[4pt]
    \\small {location} $|$ \\href{{mailto:{email}}}{{{email}}} $|$ {phone} \\\\[2pt]
    \\href{{{linkedin_link}}}{{LinkedIn}} $|$ \\href{{{github_link}}}{{GitHub}} $|$ \\href{{{portfolio_link}}}{{Portfolio}}
\\end{{center}}

\\vspace{{-6pt}}

%-----------SUMMARY-----------
\\section{{Professional Summary}}
\\small {summary_latex}

\\vspace{{4pt}}

%-----------TECHNICAL SKILLS-----------
\\section{{Technical Skills}}
\\begin{{itemize}}[leftmargin=0.15in, label=\\textbullet, noitemsep, topsep=2pt]
    \\small\\item \\textbf{{Core Technologies \\& Frameworks:}} {primary_skills_str}
    \\small\\item \\textbf{{Tools, Cloud \\& Infrastructure:}} {secondary_skills_str}
    \\small\\item \\textbf{{Engineering Methodologies:}} Agile/Scrum, Test-Driven Development, CI/CD, Microservices
\\end{{itemize}}

\\vspace{{4pt}}

%-----------EXPERIENCE-----------
\\section{{Professional Experience}}
\\textbf{{Software Engineer}} $|$ \\emph{{Technology Solutions Inc.}} \\hfill \\small 2022 -- Present \\\\[-1pt]
\\small\\textit{{Focus: Backend Systems \\& Automated Pipelines}} \\hfill \\small Bengaluru, India
\\begin{{itemize}}[leftmargin=0.15in, label=\\textbullet, noitemsep, topsep=2pt]
{bullets_latex}
\\end{{itemize}}

\\vspace{{6pt}}

%-----------PROJECTS-----------
\\section{{Key Technical Projects}}
{all_projects_latex}

%-----------EDUCATION-----------
\\section{{Education}}
\\textbf{{{escape_latex(edu_inst)}}} \\hfill \\small {escape_latex(edu_year)} \\\\[-1pt]
\\small {escape_latex(edu_degree)} \\hfill \\small First Class with Distinction

\\end{{document}}
"""

    filename = f"Resume_{name_slug}_{re.sub(r'[^a-zA-Z0-9]', '', job.title)}.tex"

    return {
        "version_label": f"{template_name} ({datetime.now().strftime('%b %d, %H:%M')})",
        "template_name": template_name,
        "latex_source": latex_source,
        "emphasized_skills": prioritized_skills[:8],
        "overleaf_url": "https://www.overleaf.com/docs",
        "filename": filename,
        "job_id": job.id,
        "job_title": job.title,
        "company": job.company
    }
