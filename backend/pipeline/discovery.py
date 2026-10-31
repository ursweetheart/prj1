"""Discover candidate taxonomy DIMENSIONS with Gemini (no training), score them, stage for review.

Change: discover-taxonomy-dimensions. Batch, credit-aware: one Gemini call per run, capped sample.
    python -m pipeline.discovery --dry-run        # print proposals, write nothing
    python -m pipeline.discovery --limit 40       # analyse 40 spaces, store proposals for review

Only the IMAGE source is wired for now (each space's transcript/caption). The conversation and
behaviour sources raise the `demand` term of the score once those logs exist (design D4).
"""

import argparse
import json
import logging
import sys

import psycopg
from psycopg.types.json import Jsonb

from pipeline import taxonomy, vertex
from pipeline.store import DSN

SAMPLE_CAP = 60  # ponytail: cap the sample so one run stays cheap; raise if recall matters
WEIGHTS = {"coverage": 0.6, "distinct": 0.4, "demand": 0.0}  # demand enabled when behaviour/chat exist (D4)
_log = logging.getLogger(__name__)

PROMPT = """Bạn là chuyên gia phân loại nội thất của D3 Studio.
Taxonomy HIỆN CÓ (chiều: các giá trị):
{taxonomy}

Một số không gian trong thư viện (id — mô tả):
{samples}

Hãy đề xuất các CHIỀU PHÂN LOẠI MỚI (dimension) mà taxonomy hiện có CHƯA bao quát, dùng để lọc portfolio.
Quy tắc:
- Chiều mới phải TRỰC GIAO với các chiều hiện có: giá trị của nó trải được trên nhiều phong cách/không gian khác nhau.
- BỎ QUA thuộc tính chụp ảnh (góc máy, ánh sáng, render hay ảnh thật, tác giả/bộ ảnh).
- Mỗi chiều kèm 2-4 giá trị rời rạc, đặt tên được bằng cụm từ tiếng Việt ngắn.
- Chỉ dựa vào mô tả trên; liệt kê id các không gian minh hoạ.
Chỉ trả JSON: {{"candidates": [
  {{"ten": "...", "mo_ta": "...", "gia_tri": ["..."], "vi_du_space_ids": [1,2],
    "trung_voi_chieu_hien_co": false, "do_tin_cay": 0.0}}
]}}"""


def _taxonomy_text() -> str:
    return "\n".join(f"- {dim}: " + ", ".join(taxonomy.values(dim)) for dim in taxonomy.dimensions())


def fetch_samples(limit: int = SAMPLE_CAP) -> list[tuple[int, str]]:
    """(space id, text) using the photo transcript if present, else the caption/alt text."""
    with psycopg.connect(DSN) as c:
        return c.execute(
            "SELECT s.id, COALESCE(t.transcript, s.caption, s.alt_text, '') "
            "FROM space s LEFT JOIN space_text t ON t.space_id = s.id "
            "WHERE COALESCE(t.transcript, s.caption, s.alt_text) IS NOT NULL ORDER BY s.id LIMIT %s",
            (min(limit, SAMPLE_CAP),)).fetchall()


def build_prompt(samples: list[tuple[int, str]]) -> str:
    sample_text = "\n".join(f"{sid}: {text[:300]}" for sid, text in samples)
    return PROMPT.format(taxonomy=_taxonomy_text(), samples=sample_text)


def _covered_ids(ex) -> set:
    """Gemini returns vi_du_space_ids either as a flat list or as {value: [ids]}; union both."""
    if isinstance(ex, dict):
        return {i for v in ex.values() for i in (v or [])}
    return set(ex or [])


def _score(c: dict, n: int) -> float:
    coverage = min(len(_covered_ids(c.get("vi_du_space_ids"))) / n, 1.0) if n else 0.0
    conf = float(c.get("do_tin_cay", 0.0) or 0.0)
    distinct = 0.0 if c.get("trung_voi_chieu_hien_co") else conf  # not distinct -> no credit
    return round(WEIGHTS["coverage"] * coverage + WEIGHTS["distinct"] * distinct, 3)  # demand term is 0 for now


def parse_and_score(reply: dict, n: int) -> list[dict]:
    scored = [{**c, "score": _score(c, n)} for c in reply.get("candidates", [])]
    return sorted(scored, key=lambda c: c["score"], reverse=True)


def _store(candidates: list[dict]):
    with psycopg.connect(DSN) as conn:
        for c in candidates:
            conn.execute(
                "INSERT INTO ung_vien_phan_loai (loai, ten_de_xuat, bang_chung) VALUES ('chieu', %s, %s)",
                (f"[AI SINH - CHƯA DUYỆT] {c.get('ten', '?')}", Jsonb({**c, "nguon": ["image"]})))


def run(limit: int = SAMPLE_CAP, dry_run: bool = False) -> list[dict]:
    samples = fetch_samples(limit)
    if not samples:
        _log.warning("no spaces with text to analyse")
        return []
    reply, _ = vertex.generate([{"text": build_prompt(samples)}])
    scored = parse_and_score(reply, len(samples))
    if dry_run:
        print(json.dumps(scored, ensure_ascii=False, indent=2))
    else:
        _store(scored)
    return scored


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Vietnamese output on a cp1252 Windows console
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=SAMPLE_CAP)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    results = run(args.limit, args.dry_run)
    print(f"{len(results)} candidate dimension(s); top score {results[0]['score'] if results else 0}")
