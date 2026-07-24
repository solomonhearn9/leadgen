"""Runs the daily digest pass: build a markdown digest from whatever's
in the buffer, email it, then clear the buffer. Meant to be run once a
day by GitHub Actions, timed for your morning.
"""
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

from src.config import load_config
from src.state import load_state, save_state
from src.digest import build_digest_markdown
from src.emailer import send_digest_email


def main():
    config = load_config()
    state = load_state()
    email_cfg = config["email"]

    markdown_body = build_digest_markdown(
        state["buffer"], config["beat"], greeting_name=email_cfg.get("greeting_name")
    )
    lead_count = len(state["buffer"])
    date_str = datetime.now(timezone.utc).strftime("%b %d")
    subject = f"Lead Digest — {date_str} ({lead_count} lead{'s' if lead_count != 1 else ''})"

    send_digest_email(
        subject=subject,
        markdown_body=markdown_body,
        to_address=email_cfg["to"],
        from_name=email_cfg.get("from_name", "Daily Lead Digest"),
        bcc=email_cfg.get("bcc") or [],
        reply_to=email_cfg.get("reply_to"),
    )
    print(f"Sent digest with {lead_count} lead(s) to {email_cfg['to']}.")

    state["buffer"] = []
    save_state(state)


if __name__ == "__main__":
    main()
