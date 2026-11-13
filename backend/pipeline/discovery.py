"""Discover candidate taxonomy DIMENSIONS with Gemini (no training), score them, stage them for human review.

Change: discover-taxonomy-dimensions. Batch and credit-aware (D7): at most MAX_CALLS Gemini calls per run.
    python -m pipeline.discovery --dry-run        # print scored proposals, write nothing
    python -m pipeline.discovery --limit 40       # analyse 40 spaces, merge into ung_vien_phan_loai

Sources (D4): images (each space's transcript/caption) propose; recurring unanswered chat questions
(khoang_trong_tri_thuc) and consented views (su_kien) add demand. A proposal is promoted to 'cho_duyet'
(shown to the lead architect) only above THRESHOLD and after Gemini's distinctness/nameability check;
everything else waits in 'cho_bang_chung'. Nothing here ever creates a dimension: that is api.accept_candidate.
"""

import argparse
import json
import logging
import os
import re
import sys

import psycopg
from psycopg.types.json import Jsonb

from pipeline import taxonomy, vertex
from pipeline.assistant import _fold
from pipeline.store import DSN

_log = logging.getLogger(__name__)
MARK = "[AI SINH - CHƯA DUYỆT] "


def _env(name, default, cast=float):
    return cast(os.getenv(name, default))


# Configuration (2.4). Calibrated 2026-11-02 on the 152-space library (image source only, no chat/view demand yet):
# two dry runs scored 0.80 / 0.78 (space connectivity, passed the check), 0.65 / 0.64 (passed), and 0.40 / 0.34
# (failed the check, halved). 0.55 keeps the checked ones and drops the halved; revisit with 4.1's labels.
THRESHOLD = _env("D3_DISCOVERY_THRESHOLD", "0.55")   # promotion bar for the final score
SAMPLE_CAP = _env("D3_DISCOVERY_SAMPLE_CAP", "60", int)
GAP_CAP = _env("D3_DISCOVERY_GAP_CAP", "40", int)
MAX_CALLS = _env("D3_DISCOVERY_MAX_CALLS", "2", int)  # 1 = propose only; nothing is promoted without the check
WEIGHTS = {"coverage": 0.45, "distinct": 0.35, "demand": 0.20}
MULTI_SOURCE_BOOST = 0.15  # D4: a second independent source raises the score
GAP_MIN, GAP_FULL = 2, 3   # linked unanswered questions: 2 make chat a source ("recurring"), 3 give full demand
LIFT_FULL = 2.0            # example spaces viewed twice their share of the library = full behaviour demand
PENALTY = 0.5              # not orthogonal, or failed the distinctness/nameability check
BACKTAG_BATCH = 50
LOW_CONFIDENCE = 0.6       # back-tags below this are flagged for review (QT01 "đủ features bắt buộc")

PROMPT = """Bạn là chuyên gia phân loại nội thất của D3 Studio.
Taxonomy HIỆN CÓ (chiều: các giá trị):
{taxonomy}

Một số không gian trong thư viện (id — mô tả):
{samples}

Câu hỏi khách chưa được trả lời (id — câu hỏi):
{gaps}

Hãy đề xuất các CHIỀU PHÂN LOẠI MỚI (dimension) mà taxonomy hiện có CHƯA bao quát, dùng để lọc portfolio.
Quy tắc:
- Chiều mới phải TRỰC GIAO với các chiều hiện có: giá trị của nó trải được trên nhiều phong cách/không gian khác nhau.
- BỎ QUA thuộc tính chụp ảnh (góc máy, ánh sáng, render hay ảnh thật, tác giả/bộ ảnh).
- "ten" và mỗi giá trị là tiếng Việt CÓ DẤU viết như nhãn cho khách đọc (vd "Mật độ cây xanh", "Nhiều cây"), không viết dạng mã.
- Mỗi chiều kèm 2-4 giá trị rời rạc, đặt tên được bằng cụm từ tiếng Việt ngắn.
- Chỉ dựa vào mô tả trên. "vi_du_space_ids": id (số) các không gian mà mô tả cho thấy RÕ một giá trị của chiều;
  "cau_hoi_lien_quan": id các câu hỏi của khách nói về chiều đó (nếu có).
Chỉ trả JSON: {{"candidates": [
  {{"ten": "...", "mo_ta": "...", "gia_tri": ["..."], "vi_du_space_ids": [1,2], "cau_hoi_lien_quan": [],
    "trung_voi_chieu_hien_co": false, "do_tin_cay": 0.0}}
]}}"""

CHECK_PROMPT = """Taxonomy nội thất HIỆN CÓ (chiều: các giá trị):
{taxonomy}

Các chiều MỚI được đề xuất:
{candidates}

Với từng đề xuất, kiểm tra:
- trung_lap: true nếu nó chỉ là cách nói khác của một chiều hoặc giá trị đã có (diễn đạt được bằng taxonomy hiện có).
- dat_ten_duoc: true nếu MỌI giá trị đặt tên được bằng một cụm từ tiếng Việt ngắn (tối đa 4 từ), rõ nghĩa với khách.
Chỉ trả JSON: {{"ket_qua": [{{"ten": "...", "trung_lap": false, "dat_ten_duoc": true, "ly_do": "..."}}]}}"""

BACKTAG_PROMPT = """Chiều phân loại nội thất mới: "{ten}" — {mo_ta}
Các giá trị (mã: tên): {values}

Gán cho MỖI không gian dưới đây đúng một giá trị (dùng mã), dựa vào mô tả, kèm độ tin cậy 0-1.
{spaces}
Chỉ trả JSON: {{"gan": [{{"id": 1, "gia_tri": "ma", "do_tin_cay": 0.0}}]}}"""


def _taxonomy_text() -> str:  # display names: Gemini answers in the words it is shown
    return "\n".join(f"- {d['ten']}: " + ", ".join(v["ten"] for v in d["values"].values())
                     for d in taxonomy.labelled().values())


def _key(name: str) -> str:  # one proposal record per dimension: "Mật độ cây xanh" == "mat do cay xanh"
    return " ".join(re.findall(r"[a-z0-9]+", _fold(name or "")))


def fetch_samples(limit: int = SAMPLE_CAP) -> list[tuple[int, str]]:
    """(space id, text) using the photo transcript if present, else the caption/alt text."""
    with psycopg.connect(DSN) as c:
        return c.execute(
            "SELECT s.id, COALESCE(t.transcript, s.caption, s.alt_text, '') "
            "FROM space s LEFT JOIN space_text t ON t.space_id = s.id "
            "WHERE COALESCE(t.transcript, s.caption, s.alt_text) IS NOT NULL ORDER BY s.id LIMIT %s",
            (min(limit, SAMPLE_CAP),)).fetchall()


def fetch_gaps(limit: int = GAP_CAP) -> list[tuple[int, str]]:
    """Newest unanswered chat questions (90 days) that carry at least one word the taxonomy does not know."""
    with psycopg.connect(DSN) as c:
        return c.execute("SELECT id, cau_hoi FROM khoang_trong_tri_thuc WHERE cardinality(tu_chua_khop) > 0 "
                         "AND created_at > now() - interval '90 days' ORDER BY id DESC LIMIT %s", (limit,)).fetchall()


def build_prompt(samples, gaps=()) -> str:
    return PROMPT.format(taxonomy=_taxonomy_text(),
                         samples="\n".join(f"{sid}: {text[:300]}" for sid, text in samples),
                         gaps="\n".join(f"{gid}: {q[:200]}" for gid, q in gaps) or "(chưa có)")


def _ids(xs) -> set:  # Gemini writes ids as 12 or "12"
    return {int(i) for i in (xs or []) if str(i).strip().isdigit()}


def _covered_ids(ex) -> set:
    """Gemini returns vi_du_space_ids either as a flat list or as {value: [ids]}; union both."""
    if isinstance(ex, dict):
        return {i for v in ex.values() for i in _ids(v)}
    return _ids(ex)


def _space_facts(ids: set) -> dict:
    """Orthogonality (spec: a 'dimension' that stays inside one existing value is a value signal) and view lift."""
    if not ids:
        return {"truc_giao": True, "do_nang_xem": 0.0}
    with psycopg.connect(DSN) as c:
        n, types, styles = c.execute("SELECT count(*), count(DISTINCT space_type), count(DISTINCT design_style) "
                                     "FROM space WHERE id = ANY(%s)", (list(ids),)).fetchone()
        pub_ex, pub_all = c.execute("SELECT count(*) FILTER (WHERE id = ANY(%s)), count(*) FROM space "
                                    "WHERE review_status = 'published'", (list(ids),)).fetchone()
        on, total = c.execute("SELECT count(*) FILTER (WHERE space_id = ANY(%s)), count(*) FROM su_kien "
                              "WHERE created_at > now() - interval '90 days' AND loai = 'xem_khong_gian' "
                              "AND phien_id NOT LIKE 'demo-%%'", (list(ids),)).fetchone()  # real views only
    lift = (on / total) / (pub_ex / pub_all) if total and pub_ex else 0.0
    return {"truc_giao": not (n >= 2 and (types == 1 or styles == 1)), "do_nang_xem": round(lift, 3)}


def evidence(c: dict, n: int, facts: dict, gap_ids: set = frozenset()) -> dict:
    """Score components of one proposal (D4). n = sample size; facts from _space_facts."""
    examples = _covered_ids(c.get("vi_du_space_ids"))
    linked = _ids(c.get("cau_hoi_lien_quan")) & set(gap_ids)
    lift = facts.get("do_nang_xem", 0.0)
    sources = ["image"] + (["chat"] if len(linked) >= GAP_MIN else []) + (["behavior"] if lift > 1.0 else [])
    return {
        "coverage": round(min(len(examples) / n, 1.0), 3) if n else 0.0,
        "distinct": 0.0 if c.get("trung_voi_chieu_hien_co") else float(c.get("do_tin_cay") or 0.0),
        "demand": round(max(min(len(linked) / GAP_FULL, 1.0), min(lift / LIFT_FULL, 1.0)), 3),
        "nguon": sources, "truc_giao": facts.get("truc_giao", True), "do_nang_xem": lift,
        "cau_hoi_lien_quan": sorted(linked), "vi_du_space_ids": sorted(examples),
    }


def score(ev: dict) -> float:
    s = sum(WEIGHTS[k] * ev.get(k, 0.0) for k in WEIGHTS)
    if len(ev.get("nguon", [])) >= 2:
        s += MULTI_SOURCE_BOOST
    if not ev.get("truc_giao", True):
        s *= PENALTY
    if ev.get("kiem_tra") is False:
        s *= PENALTY
    return round(min(s, 1.0), 3)


def merge(old: dict, new: dict) -> dict:
    """Same dimension seen again (another run or another source): keep the strongest evidence of each kind (2.1)."""
    out = {**old, **new}
    for k in ("coverage", "distinct", "demand", "do_nang_xem"):
        out[k] = max(old.get(k, 0.0), new.get(k, 0.0))
    for k in ("nguon", "cau_hoi_lien_quan", "vi_du_space_ids"):
        out[k] = sorted(set(old.get(k, [])) | set(new.get(k, [])))
    return out


def parse_and_score(reply: dict, n: int, facts_of=lambda ids: {}, gap_ids: set = frozenset()) -> list[dict]:
    """Gemini proposals -> [{ten, gia_tri, mo_ta, evidence..., score}] best first."""
    out = []
    for c in reply.get("candidates", []):
        if not c.get("ten"):
            continue
        ev = evidence(c, n, facts_of(_covered_ids(c.get("vi_du_space_ids"))), gap_ids)
        out.append({"ten": c["ten"], "mo_ta": c.get("mo_ta", ""), "gia_tri": c.get("gia_tri", []), **ev, "score": score(ev)})
    return sorted(out, key=lambda c: c["score"], reverse=True)


def check(candidates: list[dict]) -> None:
    """2.3: Gemini says whether each proposal is new and nameable; sets kiem_tra / ly_do and rescores in place."""
    listing = "\n".join(f"- {c['ten']}: {', '.join(map(str, c['gia_tri']))}" for c in candidates)
    reply, _ = vertex.generate([{"text": CHECK_PROMPT.format(taxonomy=_taxonomy_text(), candidates=listing)}])
    verdicts = {_key(r.get("ten")): r for r in reply.get("ket_qua", [])}
    for c in candidates:
        v = verdicts.get(_key(c["ten"]))
        c["kiem_tra"] = bool(v) and not v.get("trung_lap") and bool(v.get("dat_ten_duoc"))
        c["ly_do"] = (v or {}).get("ly_do", "không có kết quả kiểm tra")
        c["score"] = score(c)


def _known() -> tuple[dict, set]:
    """Pending proposals by key (to merge into) and keys that must not come back (live dimensions, decided ones)."""
    with psycopg.connect(DSN) as c:
        rows = c.execute("SELECT id, ten_de_xuat, bang_chung, trang_thai FROM ung_vien_phan_loai WHERE loai = 'chieu'").fetchall()
        dims = c.execute("SELECT ma_dinh_danh, ten FROM chieu_phan_loai").fetchall()
    pending = {_key(t.removeprefix(MARK)): (i, b or {}) for i, t, b, s in rows if s in ("cho_bang_chung", "cho_duyet")}
    blocked = {_key(t.removeprefix(MARK)) for _, t, _, s in rows if s in ("chap_nhan", "tu_choi")}
    blocked |= {_key(m.replace("_", " ")) for m, _ in dims} | {_key(t) for _, t in dims}
    return pending, blocked


def run(limit: int = SAMPLE_CAP, dry_run: bool = False) -> list[dict]:
    samples, gaps = fetch_samples(limit), fetch_gaps()
    if not samples:
        _log.warning("no spaces with text to analyse")
        return []
    reply, _ = vertex.generate([{"text": build_prompt(samples, gaps)}])  # call 1
    pending, blocked = _known()
    found = [c for c in parse_and_score(reply, len(samples), _space_facts, {g for g, _ in gaps}) if _key(c["ten"]) not in blocked]
    for c in found:  # merge with what earlier runs saw (2.1)
        if (old := pending.get(_key(c["ten"]))):
            c.update(merge(old[1], c))
            c.pop("kiem_tra", None), c.pop("ly_do", None)  # an old verdict must not stop a fresh check
            c["score"] = score(c)
    above = [c for c in found if c["score"] >= THRESHOLD]
    if above and MAX_CALLS >= 2:
        check(above)  # call 2, only for proposals that could be promoted
    for c in found:
        c["trang_thai"] = "cho_duyet" if c["score"] >= THRESHOLD and c.get("kiem_tra") else "cho_bang_chung"
    found.sort(key=lambda c: c["score"], reverse=True)
    if dry_run:
        print(json.dumps(found, ensure_ascii=False, indent=2))
    else:
        _store(found, pending)
    return found


def _store(found: list[dict], pending: dict):
    """3.1: one row per dimension, marked as unreviewed AI output, with the full score breakdown."""
    with psycopg.connect(DSN) as conn:
        for c in found:
            row = (MARK + c["ten"], Jsonb({k: v for k, v in c.items() if k != "trang_thai"}), c["trang_thai"])
            if (old := pending.get(_key(c["ten"]))):
                conn.execute("UPDATE ung_vien_phan_loai SET ten_de_xuat=%s, bang_chung=%s, trang_thai=%s, updated_at=now() "
                             "WHERE id=%s", (*row, old[0]))
            else:
                conn.execute("INSERT INTO ung_vien_phan_loai (loai, ten_de_xuat, bang_chung, trang_thai) "
                             "VALUES ('chieu', %s, %s, %s)", row)


def backtag(ten: str, mo_ta: str, values: dict[str, str]) -> dict[int, tuple[str, float]]:
    """3.3: Gemini puts every space on the new dimension. values: {ma: ten}. Returns {space_id: (ma, confidence)};
    a space Gemini skipped or answered with an unknown value is absent (the caller flags it for review)."""
    spaces = fetch_samples_all()
    listing = ", ".join(f"{m}: {t}" for m, t in values.items())
    tags = {}
    for i in range(0, len(spaces), BACKTAG_BATCH):
        batch = spaces[i:i + BACKTAG_BATCH]
        text = "\n".join(f"{sid}: {t[:300]}" for sid, t in batch)
        reply, _ = vertex.generate([{"text": BACKTAG_PROMPT.format(ten=ten, mo_ta=mo_ta or "", values=listing, spaces=text)}])
        ids = {sid for sid, _ in batch}
        for g in reply.get("gan", []):
            sid = next(iter(_ids([g.get("id")])), None)
            if sid in ids and g.get("gia_tri") in values:
                tags[sid] = (g["gia_tri"], float(g.get("do_tin_cay") or 0.0))
    return tags


def fetch_samples_all() -> list[tuple[int, str]]:
    """Every space with its best text (rollout covers the whole library, not the capped sample)."""
    with psycopg.connect(DSN) as c:
        return c.execute("SELECT s.id, COALESCE(t.transcript, s.caption, s.alt_text, '') FROM space s "
                         "LEFT JOIN space_text t ON t.space_id = s.id ORDER BY s.id").fetchall()


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Vietnamese output on a cp1252 Windows console
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=SAMPLE_CAP)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    results = run(args.limit, args.dry_run)
    promoted = sum(c["trang_thai"] == "cho_duyet" for c in results)
    print(f"{len(results)} candidate dimension(s), {promoted} promoted for review; top score {results[0]['score'] if results else 0}")
