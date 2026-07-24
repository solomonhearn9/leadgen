"""Fetches whatever a link-mined item points to and gets text out of it.

For Court Watch-style sources this is almost always a PDF -- a federal
court filing hosted on CourtListener/RECAP, a DOJ press release, an
opinion from a circuit court's own site. RECAP PDFs are built from PACER
documents, which are nearly always text-native (typed filings), so plain
extraction works for the large majority. A minority are scanned images
with no text layer and will come back empty -- see the README for how
to add OCR if that turns out to matter for your sources.
"""
import io

import requests
import pdfplumber
from readability import Document
from bs4 import BeautifulSoup

TIMEOUT = 30
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
MAX_PDF_BYTES = 25 * 1024 * 1024  # skip absurdly large filings
MAX_PDF_PAGES = 40  # cap very long documents (e.g. huge exhibit dumps)


def get_document_text(url):
    """Downloads `url` and returns extracted text. Handles PDFs directly;
    falls back to basic readability-based HTML extraction for anything
    else (e.g. a DOJ press release page instead of a filing)."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
    except Exception as e:
        print(f"    [warn] failed to fetch document {url}: {e}")
        return ""

    content_type = resp.headers.get("content-type", "")
    is_pdf = "pdf" in content_type.lower() or url.lower().split("?")[0].endswith(".pdf")

    if is_pdf:
        if len(resp.content) > MAX_PDF_BYTES:
            print(f"    [warn] skipping oversized PDF ({len(resp.content)} bytes): {url}")
            return ""
        return _extract_pdf_text(resp.content)

    try:
        doc = Document(resp.text)
        return BeautifulSoup(doc.summary(), "lxml").get_text(separator="\n").strip()
    except Exception as e:
        print(f"    [warn] failed to parse HTML for {url}: {e}")
        return ""


def _extract_pdf_text(pdf_bytes):
    text_parts = []
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages[:MAX_PDF_PAGES]:
                text_parts.append(page.extract_text() or "")
    except Exception as e:
        print(f"    [warn] failed to extract PDF text: {e}")
        return ""

    text = "\n".join(text_parts).strip()
    if not text:
        print("    [warn] PDF had no extractable text (likely a scanned image, no OCR layer)")
    return text
