"""Small Vertex AI client (service-account key): Gemini text/vision generation and text embeddings.

Credentials are looked up like MultimodalClassifier does: GOOGLE_APPLICATION_CREDENTIALS, VERTEX_SA_KEY, ./sa-key.json.
"""

import json
import os
import re
import time
from pathlib import Path

import requests

LOCATION = os.getenv("VERTEX_LOCATION", "asia-southeast1")
GEN_MODEL = os.getenv("VERTEX_GEN_MODEL", "gemini-2.5-flash")
EMBED_MODEL = os.getenv("VERTEX_EMBED_MODEL", "text-multilingual-embedding-002")
EMBED_DIM = 768
_creds = None


def key_path() -> Path | None:
    for c in (os.getenv("GOOGLE_APPLICATION_CREDENTIALS"), os.getenv("VERTEX_SA_KEY"), "sa-key.json"):
        if c and Path(c).exists():
            return Path(c)
    return None


def available() -> bool:
    return key_path() is not None


def _auth():
    global _creds
    import google.auth.transport.requests
    from google.oauth2 import service_account

    if _creds is None:
        _creds = service_account.Credentials.from_service_account_file(
            str(key_path()), scopes=["https://www.googleapis.com/auth/cloud-platform"])
    if not _creds.valid:
        _creds.refresh(google.auth.transport.requests.Request())
    return _creds


def _post(model: str, method: str, body: dict, timeout: int = 120, location: str = None) -> dict:
    c = _auth()
    loc = location or LOCATION
    url = (f"https://{loc}-aiplatform.googleapis.com/v1/projects/{c.project_id}/locations/{loc}"
           f"/publishers/google/models/{model}:{method}")
    for attempt in range(1, 4):
        try:
            r = requests.post(url, headers={"Authorization": f"Bearer {c.token}"}, json=body, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except Exception:
            if attempt == 3:
                raise
            time.sleep(attempt * 3)


def parse_json(text: str):
    return json.loads(re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip()))


def generate(parts: list, temperature: float = 0.2, as_json: bool = True):
    """parts: Gemini content parts ({"text":...} / {"inline_data":...}). -> (reply, usageMetadata)."""
    cfg = {"temperature": temperature}
    if as_json:
        cfg["response_mime_type"] = "application/json"
    data = _post(GEN_MODEL, "generateContent",
                 {"contents": [{"role": "user", "parts": parts}], "generationConfig": cfg})
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return (parse_json(text) if as_json else text), data.get("usageMetadata", {})


def embed(texts: list[str], task: str) -> list[list[float]]:
    """task: RETRIEVAL_DOCUMENT for stored text, RETRIEVAL_QUERY for the customer's question."""
    out = []
    for i in range(0, len(texts), 16):  # the API limits instances per request
        body = {"instances": [{"content": t, "task_type": task} for t in texts[i:i + 16]],
                "parameters": {"outputDimensionality": EMBED_DIM}}
        out += [p["embeddings"]["values"] for p in _post(EMBED_MODEL, "predict", body)["predictions"]]
    return out
