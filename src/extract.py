"""Gets full article text for a text item.

Tries the RSS feed's own summary/content first (fast, no network call).
Falls back to fetching the article page and running readability on it
if the feed only gave us a teaser.
"""
import requests
from readability import Document
from bs4 import BeautifulSoup

MIN_USABLE_LENGTH = 500  # chars; below this we assume it's just a teaser
TIMEOUT = 20
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def get_article_text(item):
    feed_text = _strip_html(item.get("feed_summary", ""))
    if len(feed_text) >= MIN_USABLE_LENGTH:
        return feed_text

    if not item.get("link"):
        return feed_text

    try:
        resp = requests.get(item["link"], headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        doc = Document(resp.text)
        cleaned = _strip_html(doc.summary())
        if len(cleaned) > len(feed_text):
            return cleaned
    except Exception as e:
        print(
            f"  [warn] failed to fetch article {item['link']}: {e} "
            f"(falling back to {len(feed_text)}-char feed snippet)"
        )

    return feed_text


def _strip_html(html):
    if not html:
        return ""
    soup = BeautifulSoup(html, "lxml")
    return soup.get_text(separator="\n").strip()
