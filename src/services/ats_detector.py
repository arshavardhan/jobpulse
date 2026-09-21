import re
import logging
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

CAREER_PATHS = [
    "/careers",
    "/jobs",
    "/join-us",
    "/work-with-us",
    "/opportunities",
    "/openings",
    "/about/careers"
]

ATS_DOMAINS = {
    "lever": [
        r"jobs\.lever\.co/([a-zA-Z0-9_-]+)",
        r"api\.lever\.co/v0/postings/([a-zA-Z0-9_-]+)"
    ],
    "greenhouse": [
        r"boards\.greenhouse\.io/([a-zA-Z0-9_-]+)",
        r"boards\.greenhouse\.io/embed/job_board\?for=([a-zA-Z0-9_-]+)",
        r"boards-api\.greenhouse\.io/v1/boards/([a-zA-Z0-9_-]+)"
    ],
    "ashby": [
        r"jobs\.ashbyhq\.com/([a-zA-Z0-9_-]+)",
        r"api\.ashbyhq\.com/posting-api/job-board/([a-zA-Z0-9_-]+)"
    ],
    "workable": [
        r"apply\.workable\.com/([a-zA-Z0-9_-]+)",
        r"([a-zA-Z0-9_-]+)\.workable\.com"
    ],
    "smartrecruiters": [
        r"jobs\.smartrecruiters\.com/([a-zA-Z0-9_-]+)",
        r"careers\.smartrecruiters\.com/([a-zA-Z0-9_-]+)"
    ],
    "workday": [
        r"([a-zA-Z0-9_-]+)\.myworkdayjobs\.com"
    ],
    "bamboohr": [
        r"([a-zA-Z0-9_-]+)\.bamboohr\.com/jobs"
    ]
}

def detect_ats(url: str, html: str = "") -> Dict[str, Any]:
    """
    Detect ATS provider and company slug from a given URL and/or page HTML.
    Returns:
    {
        "ats_type": "lever" | "greenhouse" | "ashby" | "workable" | "smartrecruiters" | "workday" | "unknown",
        "ats_url": str,
        "slug": str,
        "confidence": float
    }
    """
    url_str = (url or "").strip()
    html_str = (html or "").strip()

    # 1. Match against URL directly
    for ats, patterns in ATS_DOMAINS.items():
        for pat in patterns:
            m = re.search(pat, url_str, re.IGNORECASE)
            if m:
                slug = m.group(1).lower()
                return {
                    "ats_type": ats,
                    "ats_url": url_str,
                    "slug": slug,
                    "confidence": 0.95
                }

    # 2. Inspect HTML if provided
    if html_str:
        # Check links, iframes, script src in HTML
        for ats, patterns in ATS_DOMAINS.items():
            for pat in patterns:
                m = re.search(pat, html_str, re.IGNORECASE)
                if m:
                    slug = m.group(1).lower()
                    ats_url = m.group(0)
                    if not ats_url.startswith("http"):
                        ats_url = f"https://{ats_url}"
                    return {
                        "ats_type": ats,
                        "ats_url": ats_url,
                        "slug": slug,
                        "confidence": 0.85
                    }

        # Check script signatures
        if "greenhouse.io" in html_str:
            slug_match = re.search(r"['\"](?:for|boardToken)['\"]\s*:\s*['\"]([a-zA-Z0-9_-]+)['\"]", html_str)
            slug = slug_match.group(1).lower() if slug_match else ""
            return {"ats_type": "greenhouse", "ats_url": url_str, "slug": slug, "confidence": 0.80}

        if "lever.co" in html_str:
            slug_match = re.search(r"lever\.co/([a-zA-Z0-9_-]+)", html_str)
            slug = slug_match.group(1).lower() if slug_match else ""
            return {"ats_type": "lever", "ats_url": url_str, "slug": slug, "confidence": 0.80}

        if "ashbyhq.com" in html_str:
            slug_match = re.search(r"ashbyhq\.com/([a-zA-Z0-9_-]+)", html_str)
            slug = slug_match.group(1).lower() if slug_match else ""
            return {"ats_type": "ashby", "ats_url": url_str, "slug": slug, "confidence": 0.80}

    return {
        "ats_type": "unknown",
        "ats_url": url_str,
        "slug": "",
        "confidence": 0.0
    }

def discover_company_career_page(
    website: str,
    session: Optional[requests.Session] = None,
    timeout: int = 5
) -> Dict[str, Any]:
    """
    Given a company's main website (e.g. 'https://meesho.com'), discovers:
    1. The actual public careers page URL.
    2. The underlying ATS detected (Lever, Greenhouse, Ashby, etc.).
    3. The detected company slug/token.
    """
    if not website:
        return {"careers_url": "", "detected_ats": "unknown", "slug": ""}

    if not website.startswith("http"):
        website = f"https://{website}"

    client = session or requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    # First check homepage
    homepage_html = ""
    try:
        r = client.get(website, headers=headers, timeout=timeout, allow_redirects=True)
        if r.status_code == 200:
            homepage_html = r.text
            # Look for direct ATS links on homepage
            ats_check = detect_ats(r.url, homepage_html)
            if ats_check["ats_type"] != "unknown" and ats_check["slug"]:
                return {
                    "careers_url": ats_check["ats_url"],
                    "detected_ats": ats_check["ats_type"],
                    "slug": ats_check["slug"]
                }
    except Exception as e:
        logger.debug(f"Homepage fetch failed for {website}: {e}")

    # Inspect candidate career paths
    base_domain = f"{urlparse(website).scheme}://{urlparse(website).netloc}"
    for path in CAREER_PATHS:
        candidate_url = urljoin(base_domain, path)
        try:
            res = client.get(candidate_url, headers=headers, timeout=timeout, allow_redirects=True)
            if res.status_code == 200:
                final_url = res.url
                ats_info = detect_ats(final_url, res.text)
                if ats_info["ats_type"] != "unknown":
                    return {
                        "careers_url": final_url,
                        "detected_ats": ats_info["ats_type"],
                        "slug": ats_info["slug"]
                    }
                else:
                    # Found a valid company career page even if ATS not directly recognized
                    return {
                        "careers_url": final_url,
                        "detected_ats": "custom_career_page",
                        "slug": ""
                    }
        except Exception:
            continue

    return {
        "careers_url": "",
        "detected_ats": "unknown",
        "slug": ""
    }
