"""Taxonomy admin (change taxonomy-admin; seq-15, UC15): the staff side of chieu_phan_loai / gia_tri_phan_loai.

Every write runs in the caller's transaction together with its row in nhat_ky_phan_loai, and the caller calls
taxonomy.reload() after commit. Codes (ma_dinh_danh) are derived here from the name and never change afterwards.

Merging keeps the space columns that the AI tags mirror in step (phong_cach <- design_style, khong_gian <- space_type):
the sync_ai_tags trigger and the quiz read those columns, so moving only the tag rows would lose the tag on the next
edit of the space. tong_mau values come from the colour extractor and are never merged."""

import re

from psycopg.rows import dict_row  # every read goes through _cur: the API passes dict-row connections, tests plain ones
from psycopg.types.json import Jsonb

from pipeline.taxonomy import fold

MIRRORED = {"phong_cach": "design_style", "khong_gian": "space_type"}
DERIVED = {"tong_mau"}
MAX_SYN, MAX_SYN_LEN, LOG_SHOWN = 30, 60, 20


class NotFound(LookupError):
    pass


class Conflict(ValueError):
    pass


class Invalid(ValueError):
    pass


def slug(name: str) -> str:
    """'Địa Trung Hải' -> 'dia_trung_hai'."""
    return re.sub(r"[^a-z0-9]+", "_", fold(name)).strip("_")[:60]


def synonyms(items) -> list:
    """Trimmed, lower case, accents kept, no duplicates, in the order given."""
    out = []
    for s in items or []:
        s = " ".join(str(s).split()).lower()
        if s and s not in out:
            if len(s) > MAX_SYN_LEN:
                raise Invalid(f"a synonym is at most {MAX_SYN_LEN} characters")
            out.append(s)
    if len(out) > MAX_SYN:
        raise Invalid(f"at most {MAX_SYN} synonyms")
    return out


def _cur(conn):
    return conn.cursor(row_factory=dict_row)


def _log(conn, user, action, target, before, after):
    conn.execute("INSERT INTO nhat_ky_phan_loai (nguoi_dung_id, hanh_dong, doi_tuong, truoc, sau) VALUES (%s,%s,%s,%s,%s)",
                 (user["id"] if user else None, action, target, Jsonb(before) if before is not None else None,
                  Jsonb(after) if after is not None else None))


def _dim(conn, dim_id):
    row = _cur(conn).execute("SELECT id, ma_dinh_danh, ten, cho_phep_nhieu_gia_tri, hien_thi_cho_khach, thu_tu "
                             "FROM chieu_phan_loai WHERE id=%s", (dim_id,)).fetchone()
    if not row:
        raise NotFound("dimension not found")
    return row


def _value(conn, value_id):
    row = _cur(conn).execute("SELECT v.id, v.chieu_id, v.ma_dinh_danh, v.ten, v.mo_ta, v.tu_dong_nghia, d.ma_dinh_danh AS chieu "
                             "FROM gia_tri_phan_loai v JOIN chieu_phan_loai d ON d.id = v.chieu_id WHERE v.id=%s",
                             (value_id,)).fetchone()
    if not row:
        raise NotFound("value not found")
    return row


# ── read ──────────────────────────────────────────────────────────────────────
USAGE = ("SELECT count(*) AS so_khong_gian, count(*) FILTER (WHERE s.review_status = 'published') AS so_da_dang, "
         "count(DISTINCT split_part(s.relative_path, '/', 1)) AS so_du_an "
         "FROM space_gia_tri sg JOIN space s ON s.id = sg.space_id WHERE sg.gia_tri_id = %s")


def usage(conn, value_id) -> dict:
    return _cur(conn).execute(USAGE, (value_id,)).fetchone()


def tree(conn) -> dict:
    cur = _cur(conn)
    dims = cur.execute("SELECT id, ma_dinh_danh, ten, cho_phep_nhieu_gia_tri, hien_thi_cho_khach, thu_tu "
                       "FROM chieu_phan_loai ORDER BY thu_tu, id").fetchall()
    vals = cur.execute(
        "SELECT v.id, v.chieu_id, v.ma_dinh_danh, v.ten, v.mo_ta, v.tu_dong_nghia, "
        "count(sg.space_id) AS so_khong_gian, count(sg.space_id) FILTER (WHERE s.review_status = 'published') AS so_da_dang, "
        "count(DISTINCT split_part(s.relative_path, '/', 1)) AS so_du_an "
        "FROM gia_tri_phan_loai v LEFT JOIN space_gia_tri sg ON sg.gia_tri_id = v.id LEFT JOIN space s ON s.id = sg.space_id "
        "GROUP BY v.id ORDER BY v.id").fetchall()
    by_dim = {}
    for v in vals:
        by_dim.setdefault(v.pop("chieu_id"), []).append(v)
    for d in dims:
        d["gia_tri"] = by_dim.get(d["id"], [])
        d["co_the_gop"] = d["ma_dinh_danh"] not in DERIVED
    log = cur.execute("SELECT n.id, n.hanh_dong, n.doi_tuong, n.truoc, n.sau, n.created_at, u.email "
                      "FROM nhat_ky_phan_loai n LEFT JOIN app_user u ON u.id = n.nguoi_dung_id "
                      "ORDER BY n.created_at DESC, n.id DESC LIMIT %s", (LOG_SHOWN,)).fetchall()
    return {"chieu": dims, "gan_day": log}


# ── dimensions ────────────────────────────────────────────────────────────────
def add_dimension(conn, user, ten: str, nhieu: bool = False, hien_thi: bool = True) -> dict:
    ten, ma = ten.strip(), slug(ten)
    if not ma:
        raise Invalid("the name needs letters or digits")
    if conn.execute("SELECT 1 FROM chieu_phan_loai WHERE lower(ma_dinh_danh) = %s", (ma,)).fetchone():
        raise Conflict(f"dimension {ma} already exists")
    row = _cur(conn).execute(
        "INSERT INTO chieu_phan_loai (ma_dinh_danh, ten, cho_phep_nhieu_gia_tri, hien_thi_cho_khach, thu_tu) "
        "VALUES (%s, %s, %s, %s, (SELECT COALESCE(max(thu_tu), 0) + 1 FROM chieu_phan_loai)) "
        "RETURNING id, ma_dinh_danh, ten, cho_phep_nhieu_gia_tri, hien_thi_cho_khach, thu_tu",
        (ma, ten, nhieu, hien_thi)).fetchone()
    _log(conn, user, "them_chieu", ma, None, {"ten": ten, "nhieu": nhieu, "hien_thi": hien_thi})
    return row


def _renumber(conn) -> list:
    ids = [r["id"] for r in _cur(conn).execute("SELECT id FROM chieu_phan_loai ORDER BY thu_tu, id").fetchall()]
    for n, i in enumerate(ids, 1):
        conn.execute("UPDATE chieu_phan_loai SET thu_tu = %s WHERE id = %s AND thu_tu <> %s", (n, i, n))
    return ids


def edit_dimension(conn, user, dim_id, ten=None, hien_thi=None, move=None) -> dict:
    before = _dim(conn, dim_id)
    changed = {}
    if ten is not None and ten.strip() and ten.strip() != before["ten"]:
        conn.execute("UPDATE chieu_phan_loai SET ten = %s WHERE id = %s", (ten.strip(), dim_id))
        changed["ten"] = ten.strip()
    if hien_thi is not None and hien_thi != before["hien_thi_cho_khach"]:
        conn.execute("UPDATE chieu_phan_loai SET hien_thi_cho_khach = %s WHERE id = %s", (hien_thi, dim_id))
        changed["hien_thi"] = hien_thi
    if move in ("up", "down"):
        ids = _renumber(conn)
        at = ids.index(dim_id)
        other = at - 1 if move == "up" else at + 1
        if 0 <= other < len(ids):
            conn.execute("UPDATE chieu_phan_loai SET thu_tu = %s WHERE id = %s", (other + 1, dim_id))
            conn.execute("UPDATE chieu_phan_loai SET thu_tu = %s WHERE id = %s", (at + 1, ids[other]))
            changed["thu_tu"] = other + 1
    if changed:
        old = {"ten": before["ten"], "hien_thi": before["hien_thi_cho_khach"], "thu_tu": before["thu_tu"]}
        _log(conn, user, "sua_chieu", before["ma_dinh_danh"], {k: old[k] for k in changed}, changed)
    return _dim(conn, dim_id)


# ── values ────────────────────────────────────────────────────────────────────
def add_value(conn, user, dim_id, ten: str, mo_ta=None, syn=None, ma=None) -> dict:
    dim = _dim(conn, dim_id)
    ten = ten.strip()
    ma = ma or slug(ten)
    if not ma:
        raise Invalid("the name needs letters or digits")
    if conn.execute("SELECT 1 FROM gia_tri_phan_loai WHERE chieu_id = %s AND lower(ma_dinh_danh) = lower(%s)",
                    (dim_id, ma)).fetchone():
        raise Conflict("value already exists in this dimension")
    syn = synonyms(syn)
    row = _cur(conn).execute(
        "INSERT INTO gia_tri_phan_loai (chieu_id, ma_dinh_danh, ten, mo_ta, tu_dong_nghia) VALUES (%s,%s,%s,%s,%s) "
        "RETURNING id, chieu_id, ma_dinh_danh, ten, mo_ta, tu_dong_nghia",
        (dim_id, ma, ten, (mo_ta or "").strip() or None, Jsonb(syn))).fetchone()
    _log(conn, user, "them_gia_tri", f"{dim['ma_dinh_danh']}:{ma}", None, {"ten": ten, "tu_dong_nghia": syn})
    return row


def edit_value(conn, user, value_id, ten=None, mo_ta=None, syn=None) -> dict:
    before = _value(conn, value_id)
    changed, old = {}, {}
    if ten is not None and ten.strip() and ten.strip() != before["ten"]:
        changed["ten"], old["ten"] = ten.strip(), before["ten"]
    if mo_ta is not None and ((mo_ta.strip() or None) != before["mo_ta"]):
        changed["mo_ta"], old["mo_ta"] = mo_ta.strip() or None, before["mo_ta"]
    if syn is not None:
        new = synonyms(syn)
        if new != list(before["tu_dong_nghia"] or []):
            changed["tu_dong_nghia"], old["tu_dong_nghia"] = new, before["tu_dong_nghia"]
    if changed:
        sets = ", ".join(f"{k} = %s" for k in changed)
        conn.execute(f"UPDATE gia_tri_phan_loai SET {sets} WHERE id = %s",
                     [Jsonb(v) if k == "tu_dong_nghia" else v for k, v in changed.items()] + [value_id])
        _log(conn, user, "sua_gia_tri", f"{before['chieu']}:{before['ma_dinh_danh']}", old, changed)
    row = _value(conn, value_id)
    row.pop("chieu")
    return row


def merge(conn, user, source_id, target_id) -> dict:
    """Source's tags (and mirrored space columns) move to the target; the source is deleted."""
    if source_id == target_id:
        raise Invalid("cannot merge a value into itself")
    src, dst = _value(conn, source_id), _value(conn, target_id)
    if src["chieu_id"] != dst["chieu_id"]:
        raise Invalid("both values must belong to the same dimension")
    if src["chieu"] in DERIVED:
        raise Invalid(f"{src['chieu']} values are computed from the photo and cannot be merged")
    counts = usage(conn, source_id)
    col = MIRRORED.get(src["chieu"])
    moved_cols = 0
    if col:  # the trigger re-tags these spaces with the target value
        moved_cols = conn.execute(f"UPDATE space SET {col} = %s WHERE {col} = %s",
                                  (dst["ma_dinh_danh"], src["ma_dinh_danh"])).rowcount
    conn.execute("UPDATE space_gia_tri SET gia_tri_id = %s WHERE gia_tri_id = %s "
                 "AND space_id NOT IN (SELECT space_id FROM space_gia_tri WHERE gia_tri_id = %s)",
                 (target_id, source_id, target_id))
    conn.execute("DELETE FROM space_gia_tri WHERE gia_tri_id = %s", (source_id,))
    conn.execute("DELETE FROM gia_tri_phan_loai WHERE id = %s", (source_id,))
    detail = {"nguon": src["ma_dinh_danh"], "dich": dst["ma_dinh_danh"], **counts, "cot_cap_nhat": moved_cols}
    _log(conn, user, "gop_gia_tri", f"{src['chieu']}:{src['ma_dinh_danh']}", {"ten": src["ten"]}, detail)
    return {"merged_into": target_id, "affected": counts["so_khong_gian"], **detail}
