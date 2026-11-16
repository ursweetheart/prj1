"""Forbidden topics (seq-3 step 15; change topic-guard-sitemap-item-services).

Staff keep topics, each a list of keywords. The assistant checks the visitor's question and its own answer: a hit on a
switched-on topic replaces the answer with the handoff message. Matching is on folded text (case and accents ignored,
'-' read as a space) and on whole words, so "thuế" never matches inside "thiết kế". No cache: one small query per chat
turn, and every backend worker sees an edit at once."""

import re

from psycopg.rows import dict_row

from pipeline.taxonomy import fold

FIELDS = ("ten", "tu_khoa", "ghi_chu", "bat")
COLS = "id, ten, tu_khoa, ghi_chu, bat, updated_at"


class Invalid(Exception):
    def __init__(self, field, msg):
        super().__init__(msg)
        self.field, self.msg = field, msg


class Conflict(Exception):
    def __init__(self, existing):
        super().__init__(f"đã có chủ đề «{existing['ten']}»")
        self.existing = existing


class NotFound(Exception):
    pass


def norm(text: str) -> str:
    """Folded, '-' as a space, one space between words."""
    return " ".join(re.findall(r"[a-z0-9]+", fold((text or "").replace("-", " "))))


def _cur(conn):
    return conn.cursor(row_factory=dict_row)


def matches(topics, text: str):
    """(topic, keyword) of the first switched-on topic whose keyword is a whole word or phrase of text, else None."""
    t = f" {norm(text)} "
    for topic in topics:
        if not topic.get("bat", True):
            continue
        for kw in topic["tu_khoa"]:
            k = norm(kw)
            if k and f" {k} " in t:
                return topic, kw
    return None


def check(conn, text: str):
    """{id, ten, tu_khoa} of the hit (tu_khoa: the keyword that matched), or None."""
    hit = matches(_cur(conn).execute("SELECT id, ten, tu_khoa, bat FROM chu_de_cam WHERE bat ORDER BY id").fetchall(), text)
    return {"id": hit[0]["id"], "ten": hit[0]["ten"], "tu_khoa": hit[1]} if hit else None


def _clean(data: dict) -> dict:
    d = {k: v for k, v in data.items() if k in FIELDS}
    if "ten" in d:
        d["ten"] = (d["ten"] or "").strip()
        if not 1 <= len(d["ten"]) <= 80 or not norm(d["ten"]):
            raise Invalid("ten", "tên chủ đề phải từ 1 đến 80 ký tự")
    if "tu_khoa" in d:
        seen, out = set(), []
        for kw in d["tu_khoa"] or []:
            kw = str(kw).strip()
            if not kw:
                continue
            if not 2 <= len(kw) <= 60 or not norm(kw):
                raise Invalid("tu_khoa", f"từ khoá «{kw[:60]}» phải từ 2 đến 60 ký tự")
            if norm(kw) not in seen:
                seen.add(norm(kw))
                out.append(kw)
        if not out:
            raise Invalid("tu_khoa", "cần ít nhất một từ khoá")
        if len(out) > 30:
            raise Invalid("tu_khoa", "tối đa 30 từ khoá")
        d["tu_khoa"] = out
    if "ghi_chu" in d:
        d["ghi_chu"] = (d["ghi_chu"] or "").strip() or None
        if d["ghi_chu"] and len(d["ghi_chu"]) > 300:
            raise Invalid("ghi_chu", "ghi chú tối đa 300 ký tự")
    if "bat" in d and not isinstance(d["bat"], bool):
        raise Invalid("bat", "bật/tắt không hợp lệ")
    return d


def _unique(conn, name, topic_id=None):
    r = _cur(conn).execute("SELECT id, ten FROM chu_de_cam WHERE ten_khoa = %s AND id IS DISTINCT FROM %s",
                           (norm(name), topic_id)).fetchone()
    if r:
        raise Conflict(r)


def get(conn, topic_id):
    return _cur(conn).execute(f"SELECT {COLS} FROM chu_de_cam WHERE id = %s", (topic_id,)).fetchone()


def list_all(conn):
    return _cur(conn).execute(f"SELECT {COLS} FROM chu_de_cam ORDER BY lower(ten)").fetchall()


def create(conn, data: dict, user_id=None) -> dict:
    d = _clean({"bat": True, **data})
    if "ten" not in d:
        raise Invalid("ten", "tên chủ đề phải từ 1 đến 80 ký tự")
    if "tu_khoa" not in d:
        raise Invalid("tu_khoa", "cần ít nhất một từ khoá")
    _unique(conn, d["ten"])
    cols = list(d)
    tid = _cur(conn).execute(f"INSERT INTO chu_de_cam ({', '.join(cols)}, ten_khoa, tao_boi, cap_nhat_boi) "
                       f"VALUES ({', '.join(['%s'] * len(cols))}, %s, %s, %s) RETURNING id",
                       (*d.values(), norm(d["ten"]), user_id, user_id)).fetchone()["id"]
    return get(conn, tid)


def update(conn, topic_id, data: dict, user_id=None) -> dict:
    if not get(conn, topic_id):
        raise NotFound(topic_id)
    d = _clean(data)
    if "ten" in d:
        _unique(conn, d["ten"], topic_id)
        d["ten_khoa"] = norm(d["ten"])
    if d:
        sets = ", ".join(f"{k} = %s" for k in d)
        conn.execute(f"UPDATE chu_de_cam SET {sets}, cap_nhat_boi = %s, updated_at = now() WHERE id = %s",
                     (*d.values(), user_id, topic_id))
    return get(conn, topic_id)


def delete(conn, topic_id):
    if conn.execute("DELETE FROM chu_de_cam WHERE id = %s", (topic_id,)).rowcount == 0:
        raise NotFound(topic_id)
