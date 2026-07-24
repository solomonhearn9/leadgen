"""Tiny JSON-file state store.

Persisted as state.json at the repo root. The GitHub Actions workflows
commit this file back after every run so state survives between runs
(Actions runners are otherwise stateless/ephemeral).
"""
import json
import os

STATE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "state.json")

DEFAULT_STATE = {"seen_ids": [], "buffer": []}


def load_state():
    if not os.path.exists(STATE_PATH):
        return dict(DEFAULT_STATE)
    with open(STATE_PATH, "r") as f:
        data = json.load(f)
    data.setdefault("seen_ids", [])
    data.setdefault("buffer", [])
    return data


def save_state(state):
    # Cap seen_ids so this file doesn't grow forever.
    state["seen_ids"] = state["seen_ids"][-5000:]
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)
