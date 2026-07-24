"""Transcribes podcast audio using AssemblyAI.

AssemblyAI accepts a public audio URL directly, so we can hand it the
podcast's own enclosure URL without downloading the file ourselves.
Needs ASSEMBLYAI_API_KEY in the environment.
"""
import os
import time
import requests

API_BASE = "https://api.assemblyai.com/v2"
POLL_INTERVAL_SECONDS = 15
MAX_WAIT_SECONDS = 20 * 60  # long episodes can take a while to transcribe


def _headers():
    api_key = os.environ.get("ASSEMBLYAI_API_KEY")
    if not api_key:
        raise RuntimeError("ASSEMBLYAI_API_KEY is not set")
    return {"authorization": api_key}


def transcribe_audio(audio_url):
    submit = requests.post(
        f"{API_BASE}/transcript",
        json={"audio_url": audio_url},
        headers=_headers(),
        timeout=30,
    )
    submit.raise_for_status()
    transcript_id = submit.json()["id"]

    waited = 0
    while waited < MAX_WAIT_SECONDS:
        poll = requests.get(
            f"{API_BASE}/transcript/{transcript_id}", headers=_headers(), timeout=30
        )
        poll.raise_for_status()
        data = poll.json()

        if data["status"] == "completed":
            return data["text"] or ""
        if data["status"] == "error":
            raise RuntimeError(f"AssemblyAI transcription failed: {data.get('error')}")

        time.sleep(POLL_INTERVAL_SECONDS)
        waited += POLL_INTERVAL_SECONDS

    raise TimeoutError("Transcription did not finish in time")
