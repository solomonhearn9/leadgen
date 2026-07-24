"""Polls every configured RSS feed and returns items we haven't seen yet.

Podcasts, newsletters, and local papers are treated uniformly: they're
all just RSS feeds. Podcast entries additionally carry an audio
enclosure URL, which is what tells the rest of the pipeline to
transcribe instead of scrape.
"""
import time
from datetime import datetime, timezone, timedelta

import feedparser


def _entry_id(entry):
    return entry.get("id") or entry.get("link")


def _published_dt(entry):
    for key in ("published_parsed", "updated_parsed"):
        t = entry.get(key)
        if t:
            return datetime.fromtimestamp(time.mktime(t), tz=timezone.utc)
    return datetime.now(timezone.utc)


def _audio_url(entry):
    for link in entry.get("links", []) or []:
        if str(link.get("type", "")).startswith("audio"):
            return link.get("href")
    # Some feeds put the enclosure under 'enclosures' instead of 'links'
    for enc in entry.get("enclosures", []) or []:
        if str(enc.get("type", "")).startswith("audio"):
            return enc.get("href")
    return None


def fetch_new_items_for_source(src, seen_ids, lookback_hours):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    new_items = []

    parsed = feedparser.parse(src["rss"])
    if parsed.bozo and not parsed.entries:
        print(f"  [warn] could not parse feed for {src['name']}: {parsed.bozo_exception}")
        return new_items

    for entry in parsed.entries:
        eid = _entry_id(entry)
        if not eid or eid in seen_ids:
            continue

        published = _published_dt(entry)
        if published < cutoff:
            continue

        item = {
            "id": eid,
            "source_name": src["name"],
            "kind": src["kind"],
            "title": entry.get("title", "(untitled)"),
            "link": entry.get("link", ""),
            "published": published.isoformat(),
            "feed_summary": entry.get("summary", ""),
            "audio_url": _audio_url(entry) if src["kind"] == "podcasts" else None,
            "is_document_link": False,
        }
        new_items.append(item)

    return new_items
