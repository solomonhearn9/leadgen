"""Runs one ingestion pass: check every source for new items, process
each one, and append any resulting leads to the buffer for the next
daily digest. Meant to be run every couple of hours by GitHub Actions
(or directly, for local testing -- see README).
"""
from dotenv import load_dotenv

load_dotenv()  # no-op if there's no .env file (e.g. in GitHub Actions)

from src.config import load_config
from src.state import load_state, save_state
from src.sources import fetch_new_items_for_source
from src.link_mining import fetch_link_mined_items
from src.extract import get_article_text
from src.pdf_extract import get_document_text
from src.transcribe import transcribe_audio
from src.summarize import summarize_item


def get_content_for_item(item):
    if item.get("is_document_link"):
        doc_text = get_document_text(item["link"])
        context = item.get("feed_summary", "")
        return f"Newsletter blurb: {context}\n\nLinked document text:\n{doc_text}"
    if item["kind"] == "podcasts" and item.get("audio_url"):
        return transcribe_audio(item["audio_url"])
    return get_article_text(item)


def main():
    config = load_config()
    state = load_state()
    seen = set(state["seen_ids"])
    lookback = config.get("lookback_hours_first_run", 48) if not state["seen_ids"] else 6

    new_items = []
    for src in config["_all_sources"]:
        if src.get("mine_document_links"):
            new_items += fetch_link_mined_items(src, seen, lookback_hours=lookback)
        else:
            new_items += fetch_new_items_for_source(src, seen, lookback_hours=lookback)

    print(f"Found {len(new_items)} new item(s) across {len(config['_all_sources'])} source(s).")

    for item in new_items:
        print(f"- Processing: [{item['source_name']}] {item['title']}")
        state["seen_ids"].append(item["id"])

        try:
            content = get_content_for_item(item)
        except Exception as e:
            print(f"  [error] failed to get content: {e}")
            continue

        try:
            result = summarize_item(item, content, config["beat"])
        except Exception as e:
            print(f"  [error] summarization failed: {e}")
            continue

        if result.get("is_lead"):
            print(f"  -> LEAD: {result['headline']}")
            state["buffer"].append(
                {
                    "source_name": item["source_name"],
                    "kind": item["kind"],
                    "link": item["link"],
                    "published": item["published"],
                    "headline": result["headline"],
                    "central_character": result.get("central_character", ""),
                    "the_conflict": result.get("the_conflict", ""),
                    "hidden_engine": result.get("hidden_engine", ""),
                    "the_condition": result.get("the_condition", ""),
                    "magazine_fit": result.get("magazine_fit", ""),
                    "key_detail": result.get("key_detail", ""),
                    "confidence": result.get("confidence", ""),
                }
            )

    save_state(state)


if __name__ == "__main__":
    main()
