"""Turns one transcript/article/court-filing into a structured lead (or
a 'not a lead' verdict), using Claude.

This is deliberately a demanding, narrow filter, not a generic
"anything interesting" check -- it's built around a specific rubric a
narrative journalist gave for what actually clears his bar: a real
two-sided conflict, a vivid/obsessive character, something hidden or
disputed, a larger condition the story crystallizes, and a plausible
ceiling at a magazine like The New Yorker or The Atlantic. Most items
should NOT pass this filter -- that's correct behavior, not a bug.
"""
import json
import os

import anthropic

MODEL = "claude-sonnet-5"  # this rubric needs real editorial judgment,
# not just keyword/topic matching, so it's worth the extra cost over a
# cheaper model given the modest volume this pipeline runs at.
MAX_CHARS = 100_000  # keep well within context; long podcasts get truncated

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

PROMPT_TEMPLATE = """You are helping a narrative/magazine journalist find story leads.
Here is the exact rubric he uses, in his own words -- both what he's chasing
and what makes him flag something:

\"\"\"{beat}\"\"\"

Below is the transcript, article, or court filing text from a source he follows.

Source: {source_name} ({kind})
Title: {title}
Published: {published}

--- CONTENT START ---
{content}
--- CONTENT END ---

Apply his rubric literally and specifically -- don't loosen it into a generic
"is this interesting" check. Most items will NOT clear this bar, and that's
correct -- be honest and demanding rather than generous. A mildly interesting
story with no real character, no real conflict, and no hidden engine is not
a lead, even if it's well-written or locally notable. You don't have web
search, so you can't confirm whether a national outlet has already covered
this -- instead, judge whether it plausibly feels still-obscure given its
venue (a single court filing, a small local outlet, a niche newsletter), and
say so as a judgment call, not a verified fact.

Keep every JSON string field to ONE sentence. Do not elaborate.

Respond with ONLY a JSON object, no other text, no markdown fences:
{{
  "is_lead": true or false,
  "headline": "one line, in the style 'X did/said Y, which changes how we should think about Z' -- empty string if not a lead",
  "central_character": "who's the vivid, obsessive, or extreme person at the center -- empty string if not a lead",
  "the_conflict": "who's fighting whom, and why both sides have a real case -- empty string if not a lead",
  "hidden_engine": "what's hidden, disputed, or not what it first appears to be -- empty string if not a lead",
  "the_condition": "one line naming the larger condition or theme this crystallizes -- empty string if not a lead",
  "magazine_fit": "which named outlet(s) this could plausibly run in, and why, in one line -- empty string if not a lead",
  "key_detail": "the specific quote, fact, or document detail this is anchored on -- empty string if not a lead",
  "confidence": "low, medium, or high"
}}
"""

RETRY_FOLLOWUP = (
    "Your previous response was not valid JSON and could not be parsed. "
    "Respond again with ONLY a valid JSON object matching the schema above, "
    "no other text, no markdown fences. Keep every JSON string field to "
    "ONE sentence."
)


def _strip_fences(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
    return text.strip()


def _parse_json(raw):
    return json.loads(_strip_fences(raw))


def summarize_item(item, content, beat):
    if not content or not content.strip():
        return {"is_lead": False}

    prompt = PROMPT_TEMPLATE.format(
        beat=beat,
        source_name=item["source_name"],
        kind=item["kind"],
        title=item["title"],
        published=item["published"],
        content=content[:MAX_CHARS],
    )

    response = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = "".join(block.text for block in response.content if block.type == "text")

    try:
        return _parse_json(raw)
    except json.JSONDecodeError:
        print(f"  [warn] retrying unparseable summary for '{item['title']}': {raw[:200]}")

    retry_response = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        messages=[
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": raw},
            {"role": "user", "content": RETRY_FOLLOWUP},
        ],
    )
    retry_raw = "".join(
        block.text for block in retry_response.content if block.type == "text"
    )

    try:
        return _parse_json(retry_raw)
    except json.JSONDecodeError:
        print(
            f"  [warn] gave up parsing summary for '{item['title']}' "
            f"after retry: {retry_raw[:200]}"
        )
        return {"is_lead": False}
