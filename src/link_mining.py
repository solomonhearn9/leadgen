"""For 'roundup' newsletters that pack dozens of links to primary source
documents into one issue -- Court Watch is the motivating example, with
~30-40 one-line blurbs a week, each linking to a federal court filing --
this pulls out each linked document as its own item instead of treating
the whole issue as one blob of text. Otherwise the actual stories (the
documents) get flattened into a single low-signal newsletter summary
and effectively ignored, which is exactly the "takes forever to mine"
problem this is meant to solve.

A source opts into this by setting `mine_document_links: true` in
config.yaml. `link_domains` can override which link destinations count
as "documents worth mining" -- default covers the most common federal
court document hosts.
"""
import re
import time
from datetime import datetime, timezone, timedelta

import feedparser
from bs4 import BeautifulSoup

DEFAULT_DOCUMENT_DOMAINS = [
    "storage.courtlistener.com",
    "courtlistener.com",
    ".uscourts.gov",
    "justice.gov",
]


def _published_dt(entry):
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            return datetime.fromtimestamp(time.mktime(t), tz=timezone.utc)
    return datetime.now(timezone.utc)


def _entry_html(entry):
    if entry.get("content"):
        return entry["content"][0].get("value", "")
    return entry.get("summary", "")


def _is_document_link(href, domains):
    if not href:
        return False
    if href.lower().split("?")[0].endswith(".pdf"):
        return True
    return any(domain in href for domain in domains)


def _extract_linked_documents(html, domains):
    """Returns [(blurb_text, url), ...] for each qualifying link in the
    post, deduped by url (Court Watch sometimes links the same doc twice
    in one blurb)."""
    soup = BeautifulSoup(html, "lxml")
    seen_urls = set()
    results = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href in seen_urls or not _is_document_link(href, domains):
            continue
        seen_urls.add(href)

        container = a.find_parent(["li", "p"]) or a
        blurb = re.sub(r"\s+", " ", container.get_text(separator=" ", strip=True))
        results.append((blurb[:600] or a.get_text(strip=True), href))

    return results


def fetch_link_mined_items(source, seen_ids, lookback_hours):
    """source: dict with name, rss, kind, and optional link_domains."""
    domains = source.get("link_domains") or DEFAULT_DOCUMENT_DOMAINS
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

    parsed = feedparser.parse(source["rss"])
    if parsed.bozo and not parsed.entries:
        print(f"  [warn] could not parse feed for {source['name']}: {parsed.bozo_exception}")
        return []

    new_items = []
    for entry in parsed.entries:
        post_id = entry.get("id") or entry.get("link")
        published = _published_dt(entry)
        if published < cutoff:
            continue

        html = _entry_html(entry)
        for blurb, doc_url in _extract_linked_documents(html, domains):
            item_id = f"{post_id}::{doc_url}"
            if item_id in seen_ids:
                continue
            new_items.append(
                {
                    "id": item_id,
                    "source_name": source["name"],
                    "kind": source["kind"],
                    "title": blurb[:120],
                    "link": doc_url,
                    "published": published.isoformat(),
                    "feed_summary": blurb,
                    "audio_url": None,
                    "is_document_link": True,
                }
            )

    return new_items
