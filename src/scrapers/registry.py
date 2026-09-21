import os
import json
import logging
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path

from src.scrapers.base import BaseScraper
from src.scrapers.hasjob import HasjobScraper
from src.scrapers.lever import LeverCareerScraper
from src.scrapers.greenhouse import GreenhouseScraper
from src.scrapers.ashby import AshbyScraper
from src.scrapers.remotive import RemotiveScraper
from src.scrapers.himalayas import HimalayasScraper
from src.scrapers.weworkremotely import WeWorkRemotelyScraper
from src.scrapers.jobicy import JobicyScraper
from src.scrapers.arbeitnow import ArbeitnowScraper
from src.scrapers.remoteok import RemoteOKScraper
from src.scrapers.authorized_sources import (
    LinkedInJobSource, IndeedJobSource, NaukriJobSource,
    GlassdoorJobSource, FounditJobSource, WellfoundJobSource,
    InternshalaJobSource, CutshortJobSource, InstahyreJobSource,
    HiristJobSource, ShineJobSource, TimesJobsJobSource
)

logger = logging.getLogger(__name__)

class SourceDefinition:
    def __init__(
        self,
        name: str,
        display_name: str,
        source_type: str,  # rss, api, ats, company_career, partner_api
        enabled: bool = True,
        factory: Optional[Callable[[], BaseScraper]] = None,
        requires_auth: bool = False,
        auth_status: str = "CONFIGURED",  # CONFIGURED, AUTHORIZATION_REQUIRED, UNCONFIGURED
        description: str = ""
    ):
        self.name = name
        self.display_name = display_name
        self.source_type = source_type
        self.enabled = enabled
        self.factory = factory
        self.requires_auth = requires_auth
        self.auth_status = auth_status
        self.description = description

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "type": self.source_type,
            "enabled": self.enabled,
            "requires_auth": self.requires_auth,
            "auth_status": self.auth_status,
            "description": self.description
        }


class SourceRegistry:
    """
    Centralized Source Registry.
    Decouples ScoutAgent from hardcoded scraper classes and enables dynamic discovery
    across company career pages, ATS platforms, public feeds, and authorized APIs.
    """

    def __init__(self):
        self._sources: Dict[str, SourceDefinition] = {}
        self._register_default_sources()

    def _register_default_sources(self):
        # 1. Legit Public Feeds & Verified Job APIs
        self.register(SourceDefinition(
            name="hasjob",
            display_name="Hasjob India",
            source_type="rss",
            enabled=True,
            factory=lambda: HasjobScraper(),
            description="Hasjob developer RSS feed for genuine India tech roles."
        ))

        self.register(SourceDefinition(
            name="remotive",
            display_name="Remotive",
            source_type="api",
            enabled=True,
            factory=lambda: RemotiveScraper(),
            description="Remotive public API for verified global remote software engineering roles."
        ))

        self.register(SourceDefinition(
            name="himalayas",
            display_name="Himalayas",
            source_type="api",
            enabled=True,
            factory=lambda: HimalayasScraper(),
            description="Himalayas public API for remote tech and engineering positions."
        ))

        self.register(SourceDefinition(
            name="weworkremotely",
            display_name="WeWorkRemotely",
            source_type="rss",
            enabled=True,
            factory=lambda: WeWorkRemotelyScraper(),
            description="WeWorkRemotely curated programming and DevOps RSS feeds."
        ))

        self.register(SourceDefinition(
            name="jobicy",
            display_name="Jobicy",
            source_type="api",
            enabled=True,
            factory=lambda: JobicyScraper(),
            description="Jobicy public engineering and AI job feeds."
        ))

        self.register(SourceDefinition(
            name="arbeitnow",
            display_name="Arbeitnow",
            source_type="api",
            enabled=True,
            factory=lambda: ArbeitnowScraper(),
            description="Arbeitnow public API with visa-sponsored and remote tech roles."
        ))

        self.register(SourceDefinition(
            name="remoteok",
            display_name="RemoteOK",
            source_type="api",
            enabled=True,
            factory=lambda: RemoteOKScraper(),
            description="RemoteOK verified live developer and data opportunities."
        ))

        # 2. Company Career ATS Adapters (Configured by default from top public boards)
        self.register(SourceDefinition(
            name="lever-meesho",
            display_name="Lever (Meesho)",
            source_type="ats",
            enabled=True,
            factory=lambda: LeverCareerScraper("meesho", "Meesho"),
            description="Direct company career page on Lever for Meesho."
        ))

        self.register(SourceDefinition(
            name="lever-cred",
            display_name="Lever (CRED)",
            source_type="ats",
            enabled=True,
            factory=lambda: LeverCareerScraper("cred", "CRED"),
            description="Direct company career page on Lever for CRED."
        ))

        self.register(SourceDefinition(
            name="lever-postman",
            display_name="Lever (Postman)",
            source_type="ats",
            enabled=True,
            factory=lambda: LeverCareerScraper("postman", "Postman"),
            description="Direct company career page on Lever for Postman."
        ))

        self.register(SourceDefinition(
            name="greenhouse-figma",
            display_name="Greenhouse (Figma)",
            source_type="ats",
            enabled=True,
            factory=lambda: GreenhouseScraper("figma", "Figma"),
            description="Direct public Greenhouse job board for Figma."
        ))

        self.register(SourceDefinition(
            name="greenhouse-gitlab",
            display_name="Greenhouse (GitLab)",
            source_type="ats",
            enabled=True,
            factory=lambda: GreenhouseScraper("gitlab", "GitLab"),
            description="Direct public Greenhouse job board for GitLab."
        ))

        self.register(SourceDefinition(
            name="ashby-linear",
            display_name="Ashby (Linear)",
            source_type="ats",
            enabled=True,
            factory=lambda: AshbyScraper("linear", "Linear"),
            description="Direct public Ashby job board for Linear."
        ))

        self.register(SourceDefinition(
            name="ashby-ramp",
            display_name="Ashby (Ramp)",
            source_type="ats",
            enabled=True,
            factory=lambda: AshbyScraper("ramp", "Ramp"),
            description="Direct public Ashby job board for Ramp."
        ))

        # 3. Live Syndicated Job Portals & Authorized Boundaries
        self.register(SourceDefinition(
            name="linkedin",
            display_name="LinkedIn",
            source_type="partner_api",
            enabled=False,
            factory=lambda: LinkedInJobSource(),
            requires_auth=True,
            auth_status="AUTHORIZATION_REQUIRED",
            description="Live public tech syndication & guest discovery feed for LinkedIn."
        ))

        self.register(SourceDefinition(
            name="indeed",
            display_name="Indeed",
            source_type="partner_api",
            enabled=False,
            factory=lambda: IndeedJobSource(),
            requires_auth=True,
            auth_status="AUTHORIZATION_REQUIRED",
            description="Live publisher tech syndication & developer feed for Indeed."
        ))

        self.register(SourceDefinition(
            name="naukri",
            display_name="Naukri",
            source_type="partner_api",
            enabled=False,
            factory=lambda: NaukriJobSource(),
            requires_auth=True,
            auth_status="AUTHORIZATION_REQUIRED",
            description="Live Indian tech hub & developer syndication feed for Naukri."
        ))

        # Additional Major Portals
        glassdoor_source = GlassdoorJobSource()
        self.register(SourceDefinition(
            name="glassdoor",
            display_name="Glassdoor",
            source_type="partner_api",
            enabled=True,
            factory=lambda: GlassdoorJobSource(),
            requires_auth=False,
            auth_status=glassdoor_source.auth_status,
            description="Live salary-transparent tech syndication feed for Glassdoor."
        ))

        foundit_source = FounditJobSource()
        self.register(SourceDefinition(
            name="foundit",
            display_name="Foundit",
            source_type="partner_api",
            enabled=True,
            factory=lambda: FounditJobSource(),
            requires_auth=False,
            auth_status=foundit_source.auth_status,
            description="Live mid-to-senior enterprise engineering feed for Foundit (Monster India)."
        ))

        wellfound_source = WellfoundJobSource()
        self.register(SourceDefinition(
            name="wellfound",
            display_name="Wellfound",
            source_type="partner_api",
            enabled=True,
            factory=lambda: WellfoundJobSource(),
            requires_auth=False,
            auth_status=wellfound_source.auth_status,
            description="Live startup & AI engineering discovery feed for Wellfound (AngelList)."
        ))

        internshala_source = InternshalaJobSource()
        self.register(SourceDefinition(
            name="internshala",
            display_name="Internshala",
            source_type="partner_api",
            enabled=True,
            factory=lambda: InternshalaJobSource(),
            requires_auth=False,
            auth_status=internshala_source.auth_status,
            description="Live graduate, fresher, and junior engineer discovery feed for Internshala."
        ))

        cutshort_source = CutshortJobSource()
        self.register(SourceDefinition(
            name="cutshort",
            display_name="Cutshort",
            source_type="partner_api",
            enabled=True,
            factory=lambda: CutshortJobSource(),
            requires_auth=False,
            auth_status=cutshort_source.auth_status,
            description="Live curated AI & tech talent matching feed for Cutshort."
        ))

        instahyre_source = InstahyreJobSource()
        self.register(SourceDefinition(
            name="instahyre",
            display_name="Instahyre",
            source_type="partner_api",
            enabled=True,
            factory=lambda: InstahyreJobSource(),
            requires_auth=False,
            auth_status=instahyre_source.auth_status,
            description="Live curated product and backend career discovery feed for Instahyre."
        ))

        hirist_source = HiristJobSource()
        self.register(SourceDefinition(
            name="hirist",
            display_name="Hirist",
            source_type="partner_api",
            enabled=True,
            factory=lambda: HiristJobSource(),
            requires_auth=False,
            auth_status=hirist_source.auth_status,
            description="Live specialized fintech & cloud engineering feed for Hirist."
        ))

        shine_source = ShineJobSource()
        self.register(SourceDefinition(
            name="shine",
            display_name="Shine",
            source_type="partner_api",
            enabled=True,
            factory=lambda: ShineJobSource(),
            requires_auth=False,
            auth_status=shine_source.auth_status,
            description="Live enterprise recruitment tech feed for Shine."
        ))

        timesjobs_source = TimesJobsJobSource()
        self.register(SourceDefinition(
            name="timesjobs",
            display_name="TimesJobs",
            source_type="partner_api",
            enabled=True,
            factory=lambda: TimesJobsJobSource(),
            requires_auth=False,
            auth_status=timesjobs_source.auth_status,
            description="Live enterprise systems & IoT engineering feed for TimesJobs."
        ))

    def register(self, source_def: SourceDefinition):
        self._sources[source_def.name.lower()] = source_def

    def get_source(self, name: str) -> Optional[SourceDefinition]:
        return self._sources.get(name.lower())

    def get_all_definitions(self) -> List[SourceDefinition]:
        return list(self._sources.values())

    def get_active_scrapers(self, db: Any = None) -> List[BaseScraper]:
        """
        Instantiate and return all enabled scrapers.
        Includes default registered scrapers plus any dynamically discovered
        company sources from data/companies.json or the database,
        filtered strictly by candidate portal permissions when db session is supplied.
        """
        # Check Candidate Portal Permissions
        enabled_portals = set()
        disabled_portals = set()
        company_portals_enabled = True
        if db:
            try:
                from src.database.models import PortalPermissionModel
                perms = db.query(PortalPermissionModel).all()
                for p in perms:
                    if p.enabled:
                        enabled_portals.add(p.portal_name.lower())
                    else:
                        disabled_portals.add(p.portal_name.lower())
                        if p.portal_name.lower() == "company_portals":
                            company_portals_enabled = False
            except Exception as e:
                logger.warning(f"Could not load candidate portal permissions: {e}")

        active: List[BaseScraper] = []

        # 1. Registered scrapers that are enabled or granted permission by candidate
        for s_def in self._sources.values():
            if s_def.name.lower() in disabled_portals:
                continue  # Candidate disabled this portal
            is_active = s_def.enabled or (s_def.name.lower() in enabled_portals)
            if is_active and s_def.factory:
                try:
                    scraper = s_def.factory()
                    if scraper:
                        active.append(scraper)
                except Exception as e:
                    logger.warning(f"Failed to instantiate scraper for {s_def.name}: {e}")

        # 2. Check for configured company sources in companies.json (if candidate permits direct company career pages)
        if company_portals_enabled:
            companies_path = Path(__file__).parent.parent / "data" / "companies.json"
            if companies_path.exists():
                try:
                    with open(companies_path, "r", encoding="utf-8") as f:
                        companies = json.load(f)
                    registered_names = set(self._sources.keys())
                    for comp in companies:
                        if not comp.get("enabled", True):
                            continue
                        slug = comp.get("slug")
                        ats = (comp.get("detected_ats") or "").lower()
                        name = comp.get("company_name")
                        if not slug or not ats:
                            continue

                        key = f"{ats}-{slug}"
                        if key in registered_names:
                            continue  # Already registered

                        if ats == "lever":
                            active.append(LeverCareerScraper(slug, name))
                        elif ats == "greenhouse":
                            active.append(GreenhouseScraper(slug, name))
                        elif ats == "ashby":
                            active.append(AshbyScraper(slug, name))
                except Exception as e:
                    logger.warning(f"Error loading company sources: {e}")

        return active

# Global singleton
registry = SourceRegistry()
