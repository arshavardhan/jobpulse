import argparse
import sys
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from src.database.db import init_db, SessionLocal
from src.database.models import JobModel
from src.models.job import JobPosting, UserProfile
from src.agents import (
    ScoutAgent, AnalystAgent, TailorAgent, MarketIntelligenceAgent, TrackerAgent
)
from src.analytics import AnalyticsEngine

console = Console()

def run_hunt(query: str = None, limit: int = 15):
    console.print(Panel.fit("[bold cyan]Agentic AI Scout Agent — Autonomous Job Hunter[/bold cyan]"))
    init_db()
    db = SessionLocal()
    scout = ScoutAgent(log_callback=lambda msg: console.print(f"[dim]{msg}[/dim]"))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Scraping multi-source job networks...", total=None)
        jobs = scout.execute_hunt(query=query, limit_per_source=limit, db=db)

    table = Table(title=f"Discovered Opportunities ({len(jobs)})", show_lines=True)
    table.add_column("Title", style="bold white")
    table.add_column("Company", style="cyan")
    table.add_column("Location", style="magenta")
    table.add_column("Source", style="green")
    table.add_column("Key Skills", style="yellow")

    for j in jobs[:15]:
        table.add_row(
            j.title[:35],
            j.company[:20],
            j.location[:20],
            j.source,
            ", ".join(j.skills_required[:4])
        )

    console.print(table)
    db.close()

def run_match(resume_path: str = "data/demo/sample_resume_aiml.txt", limit: int = 10):
    console.print(Panel.fit("[bold green]Analyst Agent — Hybrid ATS & Semantic Matchmaker[/bold green]"))
    init_db()
    db = SessionLocal()
    analyst = AnalystAgent()

    with console.status("[cyan]Parsing candidate resume...[/cyan]"):
        profile = analyst.parse_resume_file(resume_path)

    console.print(f"[bold]Candidate:[/bold] {profile.full_name} | [bold]Experience:[/bold] {profile.years_of_experience} yrs")
    console.print(f"[bold]Skills ({len(profile.skills)}):[/bold] [dim]{', '.join(profile.skills[:10])}...[/dim]\n")

    records = db.query(JobModel).all()
    if not records:
        console.print("[yellow]Database empty. Bootstrapping with quick hunt...[/yellow]")
        ScoutAgent().execute_hunt(limit_per_source=5, db=db)
        records = db.query(JobModel).all()

    jobs = [
        JobPosting(
            id=r.id,
            title=r.title,
            company=r.company,
            location=r.location,
            is_remote=r.is_remote,
            remote_type=r.remote_type,
            salary_min=r.salary_min,
            salary_max=r.salary_max,
            currency=r.currency,
            description=r.description,
            skills_required=r.skills_required,
            experience_level=r.experience_level,
            url=r.url,
            source=r.source,
            posted_date=r.posted_date
        ) for r in records
    ]

    with console.status("[cyan]Computing vector cosine similarity and skill overlaps...[/cyan]"):
        matches = analyst.rank_jobs(profile, jobs)

    table = Table(title="Top Candidate Matches", show_lines=True)
    table.add_column("Match %", style="bold green", justify="center")
    table.add_column("Title", style="bold white")
    table.add_column("Company", style="cyan")
    table.add_column("Matching Skills", style="green")
    table.add_column("Missing Skills", style="red")

    for m in matches[:limit]:
        table.add_row(
            f"{m.match_score}%",
            m.job_title[:30],
            m.company[:18],
            ", ".join(m.matching_skills[:3]),
            ", ".join(m.missing_skills[:3])
        )

    console.print(table)
    db.close()

def run_analytics():
    console.print(Panel.fit("[bold magenta]Market Intelligence Agent — Macro Trends & Analytics[/bold magenta]"))
    init_db()
    db = SessionLocal()
    records = db.query(JobModel).all()
    if not records:
        console.print("[yellow]Database empty. Populating jobs...[/yellow]")
        ScoutAgent().execute_hunt(limit_per_source=5, db=db)
        records = db.query(JobModel).all()

    jobs = [
        JobPosting(
            id=r.id,
            title=r.title,
            company=r.company,
            location=r.location,
            is_remote=r.is_remote,
            remote_type=r.remote_type,
            salary_min=r.salary_min,
            salary_max=r.salary_max,
            currency=r.currency,
            description=r.description,
            skills_required=r.skills_required,
            experience_level=r.experience_level,
            url=r.url,
            source=r.source,
            posted_date=r.posted_date
        ) for r in records
    ]

    analyst = AnalystAgent()
    profile = analyst.parse_resume_file("data/demo/sample_resume_aiml.txt")

    agent = MarketIntelligenceAgent()
    data = agent.analyze_market(jobs, profile)

    console.print(f"[bold]Total Opportunities Ingested:[/bold] {data['total_jobs']}")
    console.print(f"[bold]Salary Median:[/bold] ${data['salary_metrics']['median']:,.0f} | [bold]Avg:[/bold] ${data['salary_metrics']['avg']:,.0f}\n")

    skills_table = Table(title="Top Demanded Tech Skills", show_lines=False)
    skills_table.add_column("Skill", style="cyan")
    skills_table.add_column("Posting Count", justify="right")
    skills_table.add_column("Market Demand %", justify="right", style="green")

    for s in data["top_skills"][:8]:
        skills_table.add_row(s["skill"].title(), str(s["count"]), f"{s['percentage']}%")

    console.print(skills_table)

    fit = data["candidate_market_fit"]
    if fit:
        console.print(Panel(
            f"[bold]Competitiveness Tier:[/bold] {fit['competitiveness_tier']}\n"
            f"[bold]Market Coverage:[/bold] {fit['market_coverage_pct']}%\n"
            f"[bold]Possessed Top Skills:[/bold] {', '.join(fit['possessed_top_skills'])}\n"
            f"[bold]Highest-ROI Skill to Learn:[/bold] [bold green]{fit['highest_roi_skill_recommendation'].upper()}[/bold green]",
            title="Candidate Market Fit Assessment",
            border_style="cyan"
        ))

    db.close()

def main():
    parser = argparse.ArgumentParser(description="Agentic AI Job Automation CLI")
    parser.add_argument("--hunt", action="store_true", help="Launch autonomous job scraper")
    parser.add_argument("--match", action="store_true", help="Match candidate resume against opportunities")
    parser.add_argument("--analytics", action="store_true", help="Compute market intelligence metrics")
    parser.add_argument("--demo", action="store_true", help="Run end-to-end demo pipeline")
    parser.add_argument("--query", type=str, default=None, help="Filter query for hunt")

    args = parser.parse_args()

    if args.demo or len(sys.argv) == 1:
        console.print("[bold cyan]>>> RUNNING END-TO-END AGENTIC PIPELINE DEMO <<<[/bold cyan]\n")
        run_hunt(query="AI", limit=5)
        console.print("\n")
        run_match(limit=5)
        console.print("\n")
        run_analytics()
    elif args.hunt:
        run_hunt(query=args.query)
    elif args.match:
        run_match()
    elif args.analytics:
        run_analytics()

if __name__ == "__main__":
    main()
