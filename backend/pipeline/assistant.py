"""RAG assistant (seq-3): parse the request, retrieve from the knowledge base, answer only from it.

python -m pipeline.assistant kb/sample.json    # (re)load the knowledge base
"""

import json
import re
import sys
import unicodedata

import numpy as np
import psycopg
from pgvector.psycopg import register_vector
from psycopg.types.json import Jsonb

from pipeline.schemas import SpaceClassificationResult
from pipeline.search import _embedder, by_text
from pipeline.store import DSN

# Below this cosine the knowledge base is treated as not knowing; calibrated by eval_assistant.py.
MIN_SCORE = 0.88
STYLES = SpaceClassificationResult.model_fields["design_style"].annotation.__args__
FALLBACK = ("Mình chưa có thông tin chính xác về câu hỏi này. Mình đã chuyển cho kiến trúc sư của D3 Studio, "
            "họ sẽ phản hồi bạn sớm.")


def _fold(s: str) -> str:  # lower-case, no diacritics: "Phòng ngủ" == "phong ngu"
    s = unicodedata.normalize("NFD", s.lower().replace("đ", "d"))
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")


# keyword -> value, matched on folded text. Order matters: first hit wins.
PROJECT_TYPES = {"can ho": "can_ho", "chung cu": "can_ho", "biet thu": "biet_thu", "nha pho": "nha_pho",
                 "van phong": "van_phong", "showroom": "thuong_mai", "cua hang": "thuong_mai"}
SPACE_TYPES = {"phong khach": "phong_khach", "phong ngu": "phong_ngu_master", "bep": "bep_va_an", "phong an": "bep_va_an",
               "phong lam viec": "phong_lam_viec", "ban cong": "ban_cong", "phong tam": "phong_tam"}
STYLE_ALIASES = {"hien dai": "Hien_dai", "tan co dien": "Tan_co_dien", "toi gian": "Toi_gian", "wabi sabi": "Wabi_sabi"}
PRICE_WORDS = ("gia", "bao gia", "chi phi", "phi", "bao nhieu", "tien")
APPOINTMENT_WORDS = ("hen", "dat lich", "tu van truc tiep", "gap kien truc su", "khao sat", "lien he")


def _has(text: str, words) -> bool:
    return any(re.search(rf"\b{re.escape(w)}\b", text) for w in words)


def parse_request(message: str) -> dict:
    t = _fold(message)
    area = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:m2|m²|met vuong)", t)
    style = next((v for k, v in STYLE_ALIASES.items() if k in t), None) or next(
        (s for s in STYLES if _fold(s.replace("_", " ")) in t and s != "Khac"), None)
    return {
        "project_type": next((v for k, v in PROJECT_TYPES.items() if k in t), None),
        "space_type": next((v for k, v in SPACE_TYPES.items() if k in t), None),
        "area_m2": float(area.group(1).replace(",", ".")) if area else None,
        "design_style": style,
        "price_intent": _has(t, PRICE_WORDS),
        "appointment_intent": _has(t, APPOINTMENT_WORDS),
    }


def load_kb(path: str) -> int:
    chunks = json.load(open(path, encoding="utf-8"))
    emb = _embedder()
    with psycopg.connect(DSN) as conn:
        register_vector(conn)
        for ch in chunks:
            vec = np.asarray(emb.embed_text(f"{ch['title']}. {ch['match']}"), dtype=np.float32)
            conn.execute(
                "INSERT INTO kb_chunk (kind, title, content, embedding) VALUES (%s,%s,%s,%s) "
                "ON CONFLICT (title) DO UPDATE SET kind=EXCLUDED.kind, content=EXCLUDED.content, embedding=EXCLUDED.embedding",
                (ch["kind"], ch["title"], ch["content"], vec))
    return len(chunks)


def retrieve(question: str, k: int = 3):
    vec = np.asarray(_embedder().embed_text(question), dtype=np.float32)
    with psycopg.connect(DSN) as conn:
        register_vector(conn)
        return conn.execute(
            "SELECT id, kind, title, content, 1 - (embedding <=> %s) AS score FROM kb_chunk ORDER BY embedding <=> %s LIMIT %s",
            (vec, vec, k)).fetchall()


def _create_lead(intent, request, conversation, contact):
    with psycopg.connect(DSN) as conn:
        return conn.execute(
            "INSERT INTO lead (intent, request, conversation, contact) VALUES (%s,%s,%s,%s) RETURNING id",
            (intent, Jsonb(request), Jsonb(conversation), contact)).fetchone()[0]


def respond(message: str, history: list | None = None, contact: str | None = None) -> dict:
    req = parse_request(message)
    hits = retrieve(message)
    known = bool(hits) and hits[0][4] >= MIN_SCORE
    conversation = (history or []) + [{"role": "user", "content": message}]

    out = {"request": req, "answered": known, "sources": [], "images": [], "lead_id": None}
    if known:
        top = hits[0]
        out["answer"] = top[3]
        out["sources"] = [{"id": h[0], "kind": h[1], "title": h[2], "score": round(float(h[4]), 3)} for h in hits if h[4] >= MIN_SCORE]
        if req["price_intent"] or req["appointment_intent"]:
            out["answer"] += "\n\nĐể kiến trúc sư báo giá/xác nhận lịch chính xác, bạn vui lòng để lại số điện thoại hoặc email."
    else:
        out["answer"] = FALLBACK

    # Three published projects matching the request (never drafts: this endpoint is public)
    if known and (req["space_type"] or req["design_style"] or req["project_type"]):
        q = " ".join(filter(None, [req["space_type"] and message, req["design_style"] and req["design_style"].replace("_", " ")])) or message
        out["images"] = [{"id": r[4], "relative_path": r[0], "space_type": r[1], "design_style": r[2]}
                         for r in by_text(q, req["space_type"], 3, published_only=True)]

    intent = "handoff" if not known else "appointment" if req["appointment_intent"] else "price" if req["price_intent"] else None
    if intent:
        out["lead_id"] = _create_lead(intent, req, conversation, contact)
    return out


# Hotspot item -> service (M7): COCO labels from furniture detection; anything not listed gets no link.
SERVICE_BY_LABEL = {
    "couch": "Dịch vụ thiết kế phòng khách", "tv": "Dịch vụ thiết kế phòng khách",
    "bed": "Dịch vụ thiết kế phòng ngủ",
    "dining table": "Dịch vụ thiết kế bếp và phòng ăn", "chair": "Dịch vụ thiết kế bếp và phòng ăn",
    "refrigerator": "Dịch vụ thiết kế bếp và phòng ăn", "oven": "Dịch vụ thiết kế bếp và phòng ăn",
    "microwave": "Dịch vụ thiết kế bếp và phòng ăn", "sink": "Dịch vụ thiết kế bếp và phòng ăn",
}


def with_services(hotspots):
    """Add `service` (a kb_chunk title) to each detected object; non-furniture detections get None."""
    if not hotspots:
        return hotspots
    for o in hotspots.get("objects", []):
        o["service"] = SERVICE_BY_LABEL.get(o.get("label"))
    return hotspots


if __name__ == "__main__":
    print(f"loaded {load_kb(sys.argv[1])} chunks")
