"""Hotspots edited by hand and the item library (seq-14; class-1 Hotspot / MonDo; roadmap 1.9).

Hotspots stay in space.hotspots.objects (every reader already uses it: the visitor page, with_services, relabel.py).
class-1 Hotspot -> one object: hotspot_anchor = (toa_do_x, toa_do_y), nguon_tao ('ai' when absent | 'thu_cong'),
confidence = do_tin_cay (AI only), mon_do_id -> mon_do. A detected object keeps label / bbox / confidence when moved;
a hand-made one has none. The supplier and note live only in mon_do and are returned only to staff."""

import re
from collections import Counter

from psycopg.rows import tuple_row

from pipeline.taxonomy import fold

MAX_POINTS = 30
FIELDS = ("ten", "phan_loai", "kieu_dang", "vat_lieu", "mau_sac", "nha_cung_cap", "ghi_chu")
PUBLIC = ("id", "ten", "phan_loai")
USED = ("SELECT count(DISTINCT s.id) FROM space s, jsonb_array_elements(COALESCE(s.hotspots->'objects', '[]')) o "
        "WHERE o->>'mon_do_id' = %s::text")


class Conflict(Exception):
    def __init__(self, existing):
        super().__init__(f"đã có món đồ «{existing['ten']}»")
        self.existing = existing


class InUse(Exception):
    def __init__(self, n):
        super().__init__(f"đang dùng ở {n} ảnh")
        self.n = n


class NotFound(Exception):
    pass


class Invalid(Exception):
    def __init__(self, row, msg):
        super().__init__(msg)
        self.row, self.msg = row, msg


def _rows(conn, sql, args=()):
    return conn.cursor(row_factory=tuple_row).execute(sql, args).fetchall()


def key(name: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", fold(name or "")))


def _clean(data: dict) -> dict:
    return {k: (str(v).strip() or None) if v is not None else None for k, v in data.items() if k in FIELDS}


def get(conn, item_id):
    cols = ("id",) + FIELDS + ("updated_at",)
    r = _rows(conn, f"SELECT {', '.join(cols)} FROM mon_do WHERE id = %s", (item_id,))
    return dict(zip(cols, r[0])) if r else None


def _check_unique(conn, name, item_id=None):
    r = _rows(conn, "SELECT id, ten FROM mon_do WHERE ten_khoa = %s AND id IS DISTINCT FROM %s", (key(name), item_id))
    if r:
        raise Conflict({"id": r[0][0], "ten": r[0][1]})


def create(conn, data: dict, user_id=None) -> dict:
    d = _clean(data)
    if not d.get("ten") or not key(d["ten"]):
        raise Invalid(None, "tên món đồ trống")
    _check_unique(conn, d["ten"])
    cols = list(d)
    item_id = _rows(conn, f"INSERT INTO mon_do ({', '.join(cols)}, ten_khoa, tao_boi, cap_nhat_boi) "
                          f"VALUES ({', '.join(['%s'] * len(cols))}, %s, %s, %s) RETURNING id",
                    (*d.values(), key(d["ten"]), user_id, user_id))[0][0]
    return get(conn, item_id)


def update(conn, item_id, data: dict, user_id=None) -> dict:
    if not get(conn, item_id):
        raise NotFound(item_id)
    d = _clean(data)
    if "ten" in d:
        if not d["ten"] or not key(d["ten"]):
            raise Invalid(None, "tên món đồ trống")
        _check_unique(conn, d["ten"], item_id)
        d["ten_khoa"] = key(d["ten"])
    if d:
        sets = ", ".join(f"{k} = %s" for k in d)
        conn.execute(f"UPDATE mon_do SET {sets}, cap_nhat_boi = %s, updated_at = now() WHERE id = %s",
                     (*d.values(), user_id, item_id))
    return get(conn, item_id)


def usage(conn, item_id) -> int:
    return _rows(conn, USED, (item_id,))[0][0]


def delete(conn, item_id):
    if not get(conn, item_id):
        raise NotFound(item_id)
    if n := usage(conn, item_id):
        raise InUse(n)
    conn.execute("DELETE FROM mon_do WHERE id = %s", (item_id,))


def search(conn, q: str = "", limit: int = 20) -> list:
    """Items whose name, type or material contains the folded query, with how many photos use each."""
    rows = list_with_usage(conn)
    needle = key(q)
    if needle:
        rows = [r for r in rows if needle in key(" ".join(filter(None, (r["ten"], r["phan_loai"], r["vat_lieu"]))))]
    return rows[:limit]


def list_with_usage(conn) -> list:
    cols = ("id",) + FIELDS + ("updated_at", "so_anh")
    rows = _rows(conn, f"""
        SELECT m.id, {', '.join('m.' + f for f in FIELDS)}, m.updated_at, COALESCE(u.n, 0)
          FROM mon_do m LEFT JOIN (
               SELECT (o->>'mon_do_id')::int AS id, count(DISTINCT s.id) AS n
                 FROM space s, jsonb_array_elements(COALESCE(s.hotspots->'objects', '[]')) o
                WHERE o ? 'mon_do_id' AND o->>'mon_do_id' ~ '^[0-9]+$' GROUP BY 1) u ON u.id = m.id
         ORDER BY lower(m.ten)""")
    return [dict(zip(cols, r)) for r in rows]


def validate_hotspots(conn, current: dict | None, edited: list) -> dict:
    """The editor's list -> the hotspots document to store. Raises Invalid(row, msg)."""
    objs = (current or {}).get("objects", [])
    if len(edited) > MAX_POINTS:
        raise Invalid(None, f"tối đa {MAX_POINTS} điểm")
    ids = {p.get("mon_do_id") for p in edited if p.get("mon_do_id") is not None}
    known = {i for (i,) in _rows(conn, "SELECT id FROM mon_do WHERE id = ANY(%s)", (list(ids),))} if ids else set()
    out = []
    for i, p in enumerate(edited):
        x, y = p.get("x"), p.get("y")
        if not all(isinstance(v, (int, float)) and 0 <= v <= 1 for v in (x, y)):
            raise Invalid(i, "vị trí phải nằm trong ảnh (0 đến 1)")
        name = (p.get("label_vi") or "").strip()
        if not 1 <= len(name) <= 120:
            raise Invalid(i, "tên điểm phải từ 1 đến 120 ký tự")
        item = p.get("mon_do_id")
        if item is not None and item not in known:
            raise Invalid(i, "món đồ không tồn tại")
        idx = p.get("index")
        if idx is not None:
            if not (isinstance(idx, int) and 0 <= idx < len(objs)):
                raise Invalid(i, "điểm gốc không tồn tại")
            o = {**objs[idx]}
            o.setdefault("nguon_tao", "ai")
        else:
            o = {"nguon_tao": "thu_cong"}
        o.update({"hotspot_anchor": [round(float(x), 4), round(float(y), 4)], "label_vi": name, "mon_do_id": item})
        out.append(o)
    doc = {k: v for k, v in (current or {}).items() if k != "objects"}
    doc["objects"] = out
    doc["counts_by_category"] = dict(Counter(o["label"] for o in out if o.get("nguon_tao", "ai") == "ai" and o.get("label")))
    return doc


def spaces_for(conn, item_id, staff: bool) -> dict | None:
    item = get(conn, item_id)
    if not item:
        return None
    rows = _rows(conn, "SELECT DISTINCT s.id, s.relative_path, s.space_type, s.design_style, s.review_status FROM space s, "
                       "jsonb_array_elements(COALESCE(s.hotspots->'objects', '[]')) o WHERE o->>'mon_do_id' = %s::text "
                       "AND (%s OR s.review_status = 'published') ORDER BY s.id", (item_id, staff))
    spaces = [{"id": i, "relative_path": p, "space_type": t, "design_style": st, **({"review_status": rs} if staff else {})}
              for i, p, t, st, rs in rows]
    return {"mon_do": item if staff else {k: item[k] for k in PUBLIC}, "spaces": spaces}
