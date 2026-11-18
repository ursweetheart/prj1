"""Data-driven taxonomy: dimensions, values, synonyms (change: discover-taxonomy-dimensions).

Reads chieu_phan_loai / gia_tri_phan_loai. If the tables are empty or the DB is
unreachable it falls back to kb/taxonomy_seed.json, so behaviour matches the old
in-code enums even before the tables are populated. Cached per process; call
reload() after editing the taxonomy (the admin API does).
"""

import json
import logging
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

_SEED = Path(__file__).resolve().parent.parent / "kb" / "taxonomy_seed.json"
_log = logging.getLogger(__name__)


def _shape(dims, vals) -> dict:
    """dims: [(ma, ten)]; vals: [(chieu_ma, ma, ten, [syn], mo_ta)] -> ordered {dim: {ten, values}}."""
    tax = {ma: {"ten": ten, "values": {}} for ma, ten in dims}
    for chieu, ma, ten, syn, mo_ta in vals:
        if chieu in tax:
            tax[chieu]["values"][ma] = {"ten": ten, "mo_ta": mo_ta or "", "syn": list(syn or [])}
    return tax


def _from_db():
    import psycopg
    from pipeline.store import DSN

    with psycopg.connect(DSN, connect_timeout=3) as c:
        dims = c.execute("SELECT ma_dinh_danh, ten FROM chieu_phan_loai ORDER BY thu_tu, id").fetchall()
        vals = c.execute(
            "SELECT d.ma_dinh_danh, v.ma_dinh_danh, v.ten, v.tu_dong_nghia, v.mo_ta "
            "FROM gia_tri_phan_loai v JOIN chieu_phan_loai d ON d.id = v.chieu_id ORDER BY d.thu_tu, v.id"
        ).fetchall()
    return _shape(dims, vals) if dims else None  # empty tables -> fall back to the seed


def _from_seed():
    data = json.loads(_SEED.read_text(encoding="utf-8"))
    dims = [(d["ma_dinh_danh"], d["ten"]) for d in data["chieu"]]
    vals = [(v["chieu"], v["ma_dinh_danh"], v["ten"], v.get("tu_dong_nghia", []), v.get("mo_ta")) for v in data["gia_tri"]]
    return _shape(dims, vals)


@lru_cache(maxsize=1)
def _tax() -> dict:
    try:
        if db := _from_db():
            return db
    except Exception as e:  # DB down / tables missing: the seed keeps the app working
        _log.info("taxonomy: using seed file (%s)", e)
    return _from_seed()


def reload():
    """Drop the cache after the taxonomy changes (admin edit, merge, newly accepted dimension)."""
    _tax.cache_clear()


def labelled() -> dict:
    """{dim: {"ten": label, "values": {ma: {"ten", "mo_ta", "syn"}}}}: display names and descriptions for prompts."""
    return _tax()


def dimensions() -> list[str]:
    return list(_tax())


def values(dim: str) -> list[str]:
    return list(_tax().get(dim, {}).get("values", {}))


def fold(s: str) -> str:
    """lower-case, no diacritics: "Phòng ngủ" == "phong ngu" (request parsing compares folded text)."""
    s = unicodedata.normalize("NFD", s.lower().replace("đ", "d"))
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")


OTHER = {"khong_gian": "khac", "phong_cach": "Khac"}  # where an answer that fits no value goes


def key(s: str) -> str:
    """fold() and drop spaces, '-' and '_': "Wabi-sabi" == "wabi_sabi" == "wabisabi"."""
    return re.sub(r"[\s_\-]+", "", fold(s))


def resolve(dim: str, answer) -> str | None:
    """A free-text answer (code, display name or synonym, any case or accents) -> that value's code, else None.
    Codes win over names, names over synonyms, so a synonym can't shadow another value's own name."""
    if not answer or not str(answer).strip():
        return None
    k = key(str(answer))
    vals = _tax().get(dim, {}).get("values", {})
    for words in (lambda ma, v: [ma], lambda ma, v: [v["ten"]], lambda ma, v: v["syn"]):
        for ma, v in vals.items():
            if any(key(w) == k for w in words(ma, v)):
                return ma
    return None


def synonym_map(dim: str) -> dict[str, str]:
    """folded synonym phrase -> value ma_dinh_danh, for parse_request. Synonyms are stored as staff typed them
    (with accents: material tagging needs "gỗ"), so they are folded here to meet the folded message."""
    return {fold(s): ma for ma, v in _tax().get(dim, {}).get("values", {}).items() for s in v["syn"]}
