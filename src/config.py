"""Loads config.yaml and validates the pieces we need."""
import os
import sys
import yaml

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")


def load_config():
    if not os.path.exists(CONFIG_PATH):
        sys.exit(
            f"Missing {CONFIG_PATH}. Copy config.example.yaml to config.yaml "
            "and fill in your beat + sources first."
        )
    with open(CONFIG_PATH, "r") as f:
        cfg = yaml.safe_load(f)

    if not cfg.get("beat"):
        sys.exit("config.yaml is missing a 'beat' description.")

    sources = cfg.get("sources", {})
    all_sources = []
    for kind in ("podcasts", "newsletters", "local_papers"):
        for src in sources.get(kind, []) or []:
            all_sources.append(
                {
                    "name": src["name"],
                    "rss": src["rss"],
                    "kind": kind,
                    "mine_document_links": src.get("mine_document_links", False),
                    "link_domains": src.get("link_domains"),
                }
            )
    cfg["_all_sources"] = all_sources
    return cfg
