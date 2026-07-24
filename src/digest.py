"""Combines today's buffered leads into one digest: a short section on
cross-source patterns (recurring conditions/themes showing up in more
than one lead, or two leads that turn out to be the same underlying
story), followed by the individual leads themselves, laid out around
the rubric each one was screened against.

This step uses the stronger model since it's doing real cross-referencing
reasoning over the whole day's leads at once, not just per-item screening.
"""
import json
import os
from datetime import datetime, timezone

import anthropic

MODEL = "claude-sonnet-5"

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

PATTERNS_PROMPT = """Here are today's story leads, each already screened for a
real conflict, a vivid central character, a hidden engine, and a larger
condition it crystallizes.

{leads_json}

In 3-5 bullet points, note anything that connects across leads: a recurring
"condition" or theme showing up in more than one, two leads that might
actually be the same underlying story approached from different angles, or
a pattern worth noticing. If nothing connects across sources, say so plainly
rather than inventing a link. Respond in plain markdown bullets, no preamble.
"""


def build_digest_markdown(buffer, beat, greeting_name=None):
    date_str = datetime.now(timezone.utc).strftime("%A, %B %d, %Y")
    greeting = f"Hey {greeting_name} — " if greeting_name else ""

    if not buffer:
        return (
            f"# Daily Lead Digest — {date_str}\n\n"
            f"{greeting}no leads matched your beat today:\n\n> {beat}\n"
        )

    leads_json = json.dumps(
        [
            {
                "headline": l["headline"],
                "the_condition": l.get("the_condition", ""),
                "central_character": l.get("central_character", ""),
                "source": l["source_name"],
            }
            for l in buffer
        ],
        indent=2,
    )

    patterns = ""
    if len(buffer) > 1:
        response = client.messages.create(
            model=MODEL,
            max_tokens=600,
            messages=[{"role": "user", "content": PATTERNS_PROMPT.format(leads_json=leads_json)}],
        )
        patterns = "".join(b.text for b in response.content if b.type == "text").strip()

    lines = [f"# Daily Lead Digest — {date_str}", ""]
    if greeting:
        lines += [f"{greeting}here's what turned up across your sources today.", ""]
    if patterns:
        lines += ["## Cross-source patterns", "", patterns, ""]

    lines += ["## Today's Leads", ""]
    for i, lead in enumerate(buffer, start=1):
        lines += [
            f"### {i}. {lead['headline']}",
            "",
            f"**The character:** {lead.get('central_character', '')}",
            "",
            f"**The conflict:** {lead.get('the_conflict', '')}",
            "",
            f"**What's hidden:** {lead.get('hidden_engine', '')}",
            "",
            f"**What it's really about:** {lead.get('the_condition', '')}",
            "",
            f"**Could run in:** {lead.get('magazine_fit', '')}",
            "",
            f"**Anchor detail:** {lead.get('key_detail', '')}",
            "",
            f"**Confidence:** {lead.get('confidence', '')}",
            "",
            f"**Source:** [{lead['source_name']}]({lead['link']}) — {lead['kind']}, {lead['published'][:10]}",
            "",
        ]

    lines.append(
        "\n---\n*Generated automatically. \"Nobody's touched this yet\" is a "
        "judgment call based on how obscure the source looks, not a verified "
        "fact — the model has no search access, so always check before you "
        "assume it's clean. Treat every lead as a starting point, not a "
        "finished pitch — go read the original document or listen to the "
        "original episode before running with it.*"
    )
    return "\n".join(lines)
