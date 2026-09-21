import re
import io
import zipfile
import unicodedata
import logging
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
import pymupdf as fitz
from src.scrapers.base import COMMON_TECH_SKILLS

logger = logging.getLogger(__name__)

# Bullet character normalizations
BULLET_CHARS = [
    '\uf0b7', '\uf0a7', '\uf0d8', '\uf076', '\u2022', '\u25aa', '\u25cf',
    '\u25cb', '\u25e6', '\u2043', '\u2219', '\u25b8', '\u25ba', '\u2023',
    '■', '●', '◆', '►', '▪', '▫', '–', '—'
]

# Common ligature replacements
LIGATURE_MAP = {
    '\ufb00': 'ff',
    '\ufb01': 'fi',
    '\ufb02': 'fl',
    '\ufb03': 'ffi',
    '\ufb04': 'ffl',
    '\ufb05': 'ft',
    '\ufb06': 'st',
}

def clean_extracted_text(raw_text: str) -> str:
    """
    Intelligent denoising pipeline for resume text across all formats:
    - Normalizes Unicode and ligatures
    - Strips non-printable and null byte garbage
    - Unifies bullet points into standard markdown bullets
    - Fixes hyphenated line-breaks (e.g. 'multi-\\nthreaded' -> 'multithreaded')
    - Collapses messy internal whitespace while preserving structural paragraph breaks
    - Removes common repeating page numbers and header junk
    """
    if not raw_text:
        return ""

    text = raw_text

    # 1. Replace ligatures
    for lig, rep in LIGATURE_MAP.items():
        text = text.replace(lig, rep)

    # 2. Normalize Unicode compatibility
    text = unicodedata.normalize('NFKD', text)

    # 3. Strip null bytes and non-printable control characters (except \n, \t, \r)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)

    # 4. Standardize bullet characters to clean markdown bullet "* "
    for bullet in BULLET_CHARS:
        text = text.replace(bullet, '\n* ')

    # 5. Fix hyphenated line breaks (e.g., "imple-\\nmented" -> "implemented")
    text = re.sub(r'(\b[a-zA-Z]{2,})-\s*\n\s*([a-zA-Z]{2,}\b)', r'\1\2', text)

    # 6. Remove standalone page number lines ("Page 1 of 2", "1 / 3", "Page 2")
    text = re.sub(r'(?im)^\s*(?:page\s*\d+(?:\s*(?:of|/)\s*\d+)?|\d+\s*(?:of|/)\s*\d+)\s*$', '', text)

    # 7. Clean up spaces around newlines
    lines = text.split('\n')
    cleaned_lines: List[str] = []
    for line in lines:
        cleaned_line = re.sub(r'[ \t]+', ' ', line).strip()
        cleaned_lines.append(cleaned_line)

    text = '\n'.join(cleaned_lines)

    # 8. Collapse 3+ newlines to double newline
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


def _extract_pdf(file_bytes: bytes) -> str:
    """Extract clean text from PDF with layout-aware block extraction to avoid interleaving columns."""
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        extracted_blocks = []
        for page in doc:
            blocks = page.get_text("blocks")
            # Filter text blocks (block_type == 0)
            text_blocks = [b for b in blocks if len(b) >= 7 and b[6] == 0 and b[4].strip()]
            if text_blocks:
                x0s = [b[0] for b in text_blocks]
                min_x = min(x0s)
                max_x = max(x0s)
                is_two_col = (max_x - min_x) > 200 and any(b[0] > min_x + 180 for b in text_blocks)

                if is_two_col:
                    mid_x = (min_x + max_x) / 2
                    col1 = sorted([b for b in text_blocks if b[0] < mid_x], key=lambda b: b[1])
                    col2 = sorted([b for b in text_blocks if b[0] >= mid_x], key=lambda b: b[1])
                    page_blocks = col1 + col2
                else:
                    page_blocks = sorted(text_blocks, key=lambda b: b[1])

                for b in page_blocks:
                    extracted_blocks.append(b[4])

        if extracted_blocks:
            return "\n\n".join(extracted_blocks)
        return "\n\n".join(page.get_text("text") for page in doc)
    except Exception as e:
        logger.error(f"Error extracting PDF: {e}")
        return ""


def _extract_docx(file_bytes: bytes) -> str:
    """Extract text from Microsoft Word .docx files via standard zipfile and XML parsing."""
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            if "word/document.xml" not in z.namelist():
                return ""
            xml_content = z.read("word/document.xml")
            root = ET.fromstring(xml_content)

            paragraphs = []
            # OpenXML namespace
            ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

            for p in root.iterfind(".//w:p", ns):
                p_text_parts = []
                # Check if paragraph is a bullet list item
                is_bullet = p.find(".//w:numPr", ns) is not None

                for elem in p.iter():
                    if elem.tag.endswith("}t") and elem.text:
                        p_text_parts.append(elem.text)
                    elif elem.tag.endswith("}br"):
                        p_text_parts.append("\n")

                p_str = "".join(p_text_parts).strip()
                if p_str:
                    if is_bullet and not p_str.startswith("* ") and not p_str.startswith("- "):
                        p_str = f"* {p_str}"
                    paragraphs.append(p_str)

            return "\n\n".join(paragraphs)
    except Exception as e:
        logger.error(f"Error extracting DOCX: {e}")
        return ""


def _extract_odt(file_bytes: bytes) -> str:
    """Extract text from OpenDocument .odt files."""
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
            if "content.xml" not in z.namelist():
                return ""
            xml_content = z.read("content.xml")
            root = ET.fromstring(xml_content)

            paragraphs = []
            for elem in root.iter():
                if elem.tag.endswith("}p") or elem.tag.endswith("}h"):
                    text = "".join(elem.itertext()).strip()
                    if text:
                        paragraphs.append(text)

            return "\n\n".join(paragraphs)
    except Exception as e:
        logger.error(f"Error extracting ODT: {e}")
        return ""


def _extract_rtf(file_bytes: bytes) -> str:
    """Extract text from Rich Text Format (.rtf) files."""
    try:
        rtf_str = file_bytes.decode("latin-1", errors="ignore")
        # Remove RTF header groups: font table, color table, etc.
        rtf_str = re.sub(r"{\\fonttbl[^}]+}", "", rtf_str)
        rtf_str = re.sub(r"{\\colortbl[^}]+}", "", rtf_str)
        rtf_str = re.sub(r"{\\stylesheet[^}]+}", "", rtf_str)
        rtf_str = re.sub(r"{\\info[^}]+}", "", rtf_str)

        # Replace line breaks and paragraphs
        rtf_str = re.sub(r"\\par\b", "\n", rtf_str)
        rtf_str = re.sub(r"\\line\b", "\n", rtf_str)
        rtf_str = re.sub(r"\\tab\b", " ", rtf_str)

        # Decode hex characters (\'e9 etc.)
        def replace_hex(match):
            hex_val = match.group(1)
            try:
                return bytes.fromhex(hex_val).decode("latin-1")
            except Exception:
                return ""

        rtf_str = re.sub(r"\\'([0-9a-fA-F]{2})", replace_hex, rtf_str)

        # Remove remaining control words and braces
        rtf_str = re.sub(r"\\[a-zA-Z0-9]+[ ]?", "", rtf_str)
        rtf_str = re.sub(r"[{}]", "", rtf_str)

        return rtf_str
    except Exception as e:
        logger.error(f"Error extracting RTF: {e}")
        return ""


def _extract_html(file_bytes: bytes) -> str:
    """Extract text from HTML (.html, .htm) files."""
    try:
        html_str = file_bytes.decode("utf-8", errors="ignore")
        soup = BeautifulSoup(html_str, "html.parser")
        for tag in soup(["script", "style", "head", "meta", "link"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)
    except Exception as e:
        logger.error(f"Error extracting HTML: {e}")
        return ""


def _extract_doc_legacy(file_bytes: bytes) -> str:
    """Extract text from legacy binary Word .doc files."""
    # 1. Check if it's actually an RTF file named .doc
    if file_bytes.startswith(b"{\\rtf"):
        return _extract_rtf(file_bytes)
    # 2. Check if it's HTML saved as .doc
    if b"<html" in file_bytes[:500].lower() or b"<!doctype" in file_bytes[:500].lower():
        return _extract_html(file_bytes)

    # 3. Binary string extraction: extract readable ASCII and UTF-16 strings
    try:
        # Extract ASCII strings >= 4 chars
        ascii_matches = re.findall(b"[\x20-\x7e\n\r\t]{4,}", file_bytes)
        ascii_text = "\n".join(m.decode("latin-1", errors="ignore") for m in ascii_matches if len(m.strip()) > 3)

        # Extract UTF-16LE strings >= 4 chars
        utf16_matches = re.findall(b"(?:[\x20-\x7e]\x00){4,}", file_bytes)
        utf16_text = "\n".join(m.decode("utf-16le", errors="ignore") for m in utf16_matches if len(m.strip()) > 3)

        combined = f"{utf16_text}\n\n{ascii_text}".strip()
        if len(combined) > 50:
            return combined
    except Exception as e:
        logger.error(f"Error extracting binary DOC: {e}")

    # Fallback decode
    return file_bytes.decode("latin-1", errors="ignore")


def _extract_plain_text(file_bytes: bytes, filename: str) -> str:
    """Extract text from plain text, markdown, or LaTeX files with multi-encoding fallback."""
    text = ""
    for enc in ("utf-8", "utf-8-sig", "utf-16", "latin-1", "cp1252"):
        try:
            text = file_bytes.decode(enc)
            break
        except Exception:
            continue

    if not text:
        text = file_bytes.decode("utf-8", errors="replace")

    # If LaTeX (.tex), clean common LaTeX commands
    if filename.lower().endswith(".tex"):
        text = re.sub(r"%.*$", "", text, flags=re.MULTILINE)
        text = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{([^{}]*)\})?", r"\1", text)

    return text


def parse_resume_bytes(file_bytes: bytes, filename: str = "resume.pdf") -> Dict[str, Any]:
    """
    Universal multi-format resume parser.
    Supports PDF (.pdf), Word (.docx, .doc), OpenDocument (.odt), Rich Text (.rtf),
    HTML (.html, .htm), Markdown (.md), LaTeX (.tex), and Plain Text (.txt)
    with zero need for user file conversions.
    """
    fn_lower = filename.lower()
    raw_text = ""

    # Route based on detected file type
    if fn_lower.endswith(".pdf") or file_bytes.startswith(b"%PDF"):
        raw_text = _extract_pdf(file_bytes)
    elif fn_lower.endswith(".docx") or (file_bytes.startswith(b"PK") and b"word/document.xml" in file_bytes[:2000]):
        raw_text = _extract_docx(file_bytes)
    elif fn_lower.endswith(".odt") or (file_bytes.startswith(b"PK") and b"mimetypeapplication/vnd.oasis.opendocument.text" in file_bytes[:150]):
        raw_text = _extract_odt(file_bytes)
    elif fn_lower.endswith(".rtf") or file_bytes.startswith(b"{\\rtf"):
        raw_text = _extract_rtf(file_bytes)
    elif fn_lower.endswith(".html") or fn_lower.endswith(".htm") or b"<html" in file_bytes[:500].lower():
        raw_text = _extract_html(file_bytes)
    elif fn_lower.endswith(".doc"):
        raw_text = _extract_doc_legacy(file_bytes)
    else:
        # Default text / markdown / LaTeX
        raw_text = _extract_plain_text(file_bytes, filename)

    clean_text = clean_extracted_text(raw_text)

    # If clean_text is still empty, try standard fallback decode
    if not clean_text:
        try:
            fallback = file_bytes.decode("utf-8", errors="ignore")
            clean_text = clean_extracted_text(fallback)
        except Exception:
            pass

    # Extract metadata from clean text
    lowered = clean_text.lower()

    # Detect skills
    detected_skills = []
    for skill in COMMON_TECH_SKILLS:
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, lowered):
            detected_skills.append(skill)
    detected_skills = sorted(list(set(detected_skills)))

    # Estimate experience
    years_exp = 2.0
    match_years = re.search(r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)(?:\s+of)?\s+experience", lowered)
    if match_years:
        try:
            years_exp = float(match_years.group(1))
        except Exception:
            pass

    # Detect email
    email = None
    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", clean_text)
    if email_match:
        email = email_match.group(0).lower()

    # Detect phone
    phone = None
    phone_match = re.search(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}", clean_text)
    if phone_match:
        phone = phone_match.group(0)

    # Detect candidate name
    candidate_name = "Candidate"
    lines = [l.strip() for l in clean_text.split("\n") if l.strip()]
    for line in lines[:5]:
        line_clean = re.sub(r'[^a-zA-Z\s]', '', line).strip()
        words = line_clean.split()
        if 2 <= len(words) <= 4 and not any(kw in line_clean.lower() for kw in ["resume", "curriculum", "vitae", "summary", "engineer", "developer", "experience", "education"]):
            candidate_name = line_clean
            break

    # Determine file format label
    format_label = fn_lower.split(".")[-1].upper() if "." in fn_lower else "DOCUMENT"

    return {
        "success": bool(clean_text),
        "format": format_label,
        "clean_text": clean_text,
        "name": candidate_name,
        "email": email,
        "phone": phone,
        "skills": detected_skills,
        "years_of_experience": years_exp,
        "char_count": len(clean_text)
    }
