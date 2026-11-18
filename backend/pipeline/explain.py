"""Why a search result fits (search-explanations; seq-2 b9-b10, seq-8 b4-b6 / b13, seq-11 b3-b4 / b11-b12).

Everything here uses the stored labels and the local SigLIP2 embedder: no Gemini call.
  - reasons on similar spaces: the labels a result shares with the source photo;
  - a description is split into hard constraints (room type, style named in it) and the words compared by meaning;
  - reasons on description results: the result's labels the description names;
  - an uploaded photo: is it an interior (zero-shot prompts + the calibrated similarity floor), and its likely style
    and tone by a weighted vote of the closest library photos.
"""

import re
from collections import defaultdict
from functools import lru_cache

import numpy as np
from psycopg.rows import tuple_row

from pipeline import taxonomy

CONSTRAINT_DIMS = ("khong_gian", "phong_cach")
PHRASE = {"khong_gian": "loại phòng", "phong_cach": "phong cách", "tong_mau": "tông màu", "vat_lieu": "vật liệu",
          "bo_cuc_cong_nang": "bố cục", "loai_cong_trinh": "loại công trình", "muc_dau_tu": "mức đầu tư"}
MAX_REASONS = 3
KNN, MIN_TRAIT = 15, 0.4
INTERIOR = "a photo of an interior room"
NOT_INTERIOR = ("a logo", "a document or text", "a portrait of a person", "an outdoor landscape",
                "a product on a plain background")


def _rows(conn, sql, args=()):
    return conn.cursor(row_factory=tuple_row).execute(sql, args).fetchall()


def labels(conn, ids) -> dict[int, list[tuple]]:
    """{space id: [(dimension, dimension name, value code, value name)]} in display order, visitor-facing, no 'khac'."""
    out = defaultdict(list)
    for sid, d, dn, v, vn in _rows(conn, """
        SELECT sg.space_id, c.ma_dinh_danh, c.ten, g.ma_dinh_danh, g.ten FROM space_gia_tri sg
          JOIN gia_tri_phan_loai g ON g.id = sg.gia_tri_id JOIN chieu_phan_loai c ON c.id = g.chieu_id
         WHERE sg.space_id = ANY(%s) AND c.hien_thi_cho_khach AND lower(g.ma_dinh_danh) <> 'khac'
         ORDER BY c.ma_dinh_danh <> 'khong_gian', c.ma_dinh_danh <> 'phong_cach', c.thu_tu, c.id, g.ten""", (list(ids),)):
        out[sid].append((d, dn, v, vn))
    return out


def phrase(dim: str, dim_name: str, name: str) -> str:
    return f"{PHRASE.get(dim, dim_name.lower())} {name}"


def shared_reasons(conn, source_id: int, hit_ids: list[int]) -> dict[int, list[str]]:
    """seq-2 b9: per result, "Cùng phong cách Japandi" for the labels it shares with the source; at most 3."""
    lab = labels(conn, [source_id, *hit_ids])
    src = {(d, v) for d, _, v, _ in lab.get(source_id, [])}
    out = {}
    for h in hit_ids:
        shared = [(d, dn, vn) for d, dn, v, vn in lab.get(h, []) if (d, v) in src]
        seen, keep = set(), []
        for d, dn, vn in shared:  # one per dimension: room type, style, then others
            if d not in seen:
                seen.add(d)
                keep.append("Cùng " + phrase(d, dn, vn))
        out[h] = keep[:MAX_REASONS]
    return out


def _words(text: str) -> str:
    return " " + re.sub(r"[^a-z0-9]+", " ", taxonomy.fold(text).lower()).strip() + " "


def _fold_token(tok: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", taxonomy.fold(tok).lower())


def parse_query(text: str) -> tuple[list[dict], str]:
    """seq-11 b3-b4: room type / style named in the description (name, code or synonym, whole words, accents and
    case ignored, longest first) -> ([{chieu, ma, ten}], the remaining words with their accents). The first match
    per dimension counts."""
    tax = taxonomy.labelled()
    tokens = text.split()
    folded = [_fold_token(t) for t in tokens]
    candidates = []
    for dim in CONSTRAINT_DIMS:
        for ma, v in tax.get(dim, {}).get("values", {}).items():
            if ma.lower() == "khac":
                continue
            for term in {v["ten"], ma.replace("_", " "), *v.get("syn", [])}:
                words = [w for w in (_fold_token(x) for x in re.split(r"[\s_\-]+", term)) if w]
                if words:
                    candidates.append((len(" ".join(words)), dim, ma, v["ten"], words))
    found, used = [], set()
    for _, dim, ma, ten, words in sorted(candidates, key=lambda c: -c[0]):
        if any(f["chieu"] == dim for f in found):
            continue
        n = len(words)
        for i in range(len(folded) - n + 1):
            span = set(range(i, i + n))
            if folded[i:i + n] == words and not span & used:
                found.append({"chieu": dim, "ma": ma, "ten": ten})
                used |= span
                break
    rest = " ".join(t for i, t in enumerate(tokens) if i not in used and folded[i])
    return found, rest


# first words too common to name a label alone ("phòng khách" must not match "Phòng ngủ")
STOP = {"phong", "khong", "gian", "mau", "tong", "phong cach", "va", "co", "cac", "nha", "can", "ho", "kieu"}


def _term_in(term: str, folded: str) -> bool:
    words = _words(term).split()
    if not words:
        return False
    if f" {' '.join(words)} " in folded:  # the whole name, e.g. "go tu nhien"
        return True
    return len(words) > 1 and words[0] not in STOP and f" {words[0]} " in folded  # its head word, e.g. "go"


def text_reasons(conn, text: str, constraints: list[dict], hit_ids: list[int]) -> dict[int, list[str]]:
    """seq-11 b11: per result, its labels the description names (by name, head word or synonym), constraints first."""
    tax = taxonomy.labelled()
    folded = _words(text)
    named = {(c["chieu"], c["ma"]) for c in constraints}
    out = {}
    for h, labs in labels(conn, hit_ids).items():
        keep = [vn for d, _, v, vn in labs if (d, v) in named]
        for d, _, v, vn in labs:
            terms = {vn, *tax.get(d, {}).get("values", {}).get(v, {}).get("syn", [])}
            if (d, v) not in named and any(_term_in(term, folded) for term in terms):
                keep.append(vn)
        out[h] = list(dict.fromkeys(keep))[:MAX_REASONS]
    return out


@lru_cache(maxsize=1)
def _prompt_vectors():
    from pipeline.search import _embedder
    e = _embedder()
    return np.asarray([e.embed_text(p) for p in (INTERIOR, *NOT_INTERIOR)], dtype=np.float32)


def interior_score(vec) -> float:
    """Probability-like share of the interior prompt among the prompts (softmax over scaled cosines)."""
    p = _prompt_vectors()
    v = np.asarray(vec, dtype=np.float32)
    sims = p @ v / (np.linalg.norm(p, axis=1) * np.linalg.norm(v) + 1e-9)
    z = np.exp(100 * (sims - sims.max()))
    return float(z[0] / z.sum())


def traits(conn, vec, published_only=True) -> dict:
    """seq-8 b13: likely style and tone by a weighted vote of the KNN closest library photos; under MIN_TRAIT left out."""
    rows = _rows(conn, "SELECT id, 1 - (embedding <=> %s) FROM space WHERE embedding IS NOT NULL "
                       + ("AND review_status = 'published' " if published_only else "")
                       + "ORDER BY embedding <=> %s LIMIT %s", (vec, vec, KNN))
    if not rows:
        return {}
    weight = {sid: max(float(s), 0.0) for sid, s in rows}
    lab = labels(conn, list(weight))
    out = {}
    for dim in ("phong_cach", "tong_mau"):
        votes, names = defaultdict(float), {}
        for sid, w in weight.items():
            for d, _, v, vn in lab.get(sid, []):
                if d == dim:
                    votes[v] += w
                    names[v] = vn
        total = sum(weight.values())
        if votes and total:
            best = max(votes, key=votes.get)
            conf = votes[best] / total
            if conf >= MIN_TRAIT:
                out[dim] = {"ma": best, "ten": names[best], "do_tin_cay": round(conf, 2)}
    return out
