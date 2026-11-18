"""The chatbot's knowledge entries, managed by staff (change assistant-knowledge-admin; UC16, seq-16).

An entry is said by the chatbot only while 'dang_dung'. Statuses: nhap (draft) -> cho_duyet (waiting for the lead
architect) -> dang_dung (in use) <-> tat (off); any -> nhap. "Giá chỉ được nêu sau khi được duyệt": an entry of kind
'price', or whose answer states an amount of money, is switched on only by an approver; a content editor's change to
the answer of such a live entry sends it back to cho_duyet. Every write logs to nhat_ky_tri_thuc in the caller's
transaction; title and match phrases are re-embedded on save, so the next question already uses them."""

import re

from psycopg.rows import dict_row, tuple_row  # the API passes dict-row connections: positional reads use _tup
from psycopg.types.json import Jsonb

from pipeline.assistant import AI_MARK, KB_KINDS, MONEY, SAMPLE_MARK, SERVICE_BY_LABEL
from pipeline.taxonomy import fold

APPROVER_ROLES = {"lead_architect", "admin"}
STATUSES = ("nhap", "cho_duyet", "dang_dung", "tat")
MOVES = {"cho_duyet": {"nhap"}, "dang_dung": {"nhap", "cho_duyet", "tat"}, "tat": {"dang_dung"},
         "nhap": {"cho_duyet", "dang_dung", "tat"}}
LINKED = set(SERVICE_BY_LABEL.values())  # hotspots link to these titles (assistant.with_services)
# a number followed by a money unit that ends there ("3 đến 4 tuần" is not money: "đ" runs on into "ến")
# MONEY lives in pipeline.assistant: the chatbot also uses it to keep amounts out of its answers
FIELDS = ("id, kind, title, cum_tu_khop, content, trang_thai, nguon, tu_cau_hoi, updated_at, "
          "(SELECT email FROM app_user u WHERE u.id = k.updated_by) AS updated_by")


class NotFound(LookupError):
    pass


class Conflict(ValueError):
    pass


class Invalid(ValueError):
    pass


class Forbidden(PermissionError):
    pass


def needs_price_approval(kind: str, content: str) -> bool:
    return kind == "price" or bool(MONEY.search(content or ""))


def is_approver(user) -> bool:
    return bool(user) and user["role"] in APPROVER_ROLES


def _embedding(title: str, phrases: str) -> str:
    """pgvector text form of the SigLIP2 text embedding (same input as assistant.load_kb)."""
    from pipeline.search import _embedder  # loads the model on first use only
    vec = _embedder().embed_text(f"{title}. {phrases}")
    return "[" + ",".join(f"{float(x):.7f}" for x in vec) + "]"


def _shape(row: dict) -> dict:
    row["can_duyet_gia"] = needs_price_approval(row["kind"], row["content"])
    row["mau"] = row["content"].startswith(SAMPLE_MARK)
    row["ai"] = row["content"].startswith(AI_MARK)
    row["lien_ket"] = row["title"] in LINKED
    return row


def _cur(conn):
    return conn.cursor(row_factory=dict_row)


def _tup(conn):
    return conn.cursor(row_factory=tuple_row)


def _log(conn, user, entry_id, action, before, after):
    conn.execute("INSERT INTO nhat_ky_tri_thuc (kb_chunk_id, nguoi_dung_id, hanh_dong, truoc, sau) VALUES (%s,%s,%s,%s,%s)",
                 (entry_id, user["id"] if user else None, action, Jsonb(before) if before is not None else None,
                  Jsonb(after) if after is not None else None))


def _clean(kind, title, phrases, content):
    if kind is not None and kind not in KB_KINDS:
        raise Invalid(f"kind must be one of {KB_KINDS}")
    for name, v in (("title", title), ("cum_tu_khop", phrases), ("content", content)):
        if v is not None and not v.strip():
            raise Invalid(f"{name} cannot be empty")


# ── read ──────────────────────────────────────────────────────────────────────
def get(conn, entry_id) -> dict:
    row = _cur(conn).execute(f"SELECT {FIELDS} FROM kb_chunk k WHERE id = %s", (entry_id,)).fetchone()
    if not row:
        raise NotFound("entry not found")
    return _shape(row)


def list_entries(conn, q: str | None = None, trang_thai: str | None = None) -> dict:
    rows = [_shape(r) for r in _cur(conn).execute(
        f"SELECT {FIELDS} FROM kb_chunk k WHERE (%(s)s::text IS NULL OR trang_thai = %(s)s) "
        "ORDER BY CASE trang_thai WHEN 'cho_duyet' THEN 0 WHEN 'nhap' THEN 1 WHEN 'dang_dung' THEN 2 ELSE 3 END, "
        "updated_at DESC, id", {"s": trang_thai}).fetchall()]
    if q and q.strip():
        needle = fold(q.strip())
        rows = [r for r in rows if needle in fold(f"{r['title']} {r['cum_tu_khop']} {r['content']}")]
    counts = dict(_tup(conn).execute("SELECT trang_thai, count(*) FROM kb_chunk GROUP BY 1").fetchall())
    return {"items": rows, "dem": {s: counts.get(s, 0) for s in STATUSES}}


# ── write ─────────────────────────────────────────────────────────────────────
def create(conn, user, kind, title, cum_tu_khop, content, trang_thai="nhap", tu_cau_hoi=()) -> dict:
    _clean(kind, title, cum_tu_khop, content)
    if trang_thai not in ("nhap", "cho_duyet"):
        raise Invalid("a new entry starts as nhap or cho_duyet; switch it on afterwards")
    title = title.strip()
    if conn.execute("SELECT 1 FROM kb_chunk WHERE title = %s", (title,)).fetchone():
        raise Conflict("title already exists")
    vec = _embedding(title, cum_tu_khop.strip())
    new_id = _tup(conn).execute(
        "INSERT INTO kb_chunk (kind, title, cum_tu_khop, content, embedding, trang_thai, nguon, tu_cau_hoi, updated_by) "
        "VALUES (%s,%s,%s,%s,%s::vector,%s,'nhan_vien',%s,%s) RETURNING id",
        (kind, title, cum_tu_khop.strip(), content.strip(), vec, trang_thai, list(tu_cau_hoi or []),
         user["id"] if user else None)).fetchone()[0]
    _log(conn, user, new_id, "tao", None, {"title": title, "kind": kind, "trang_thai": trang_thai})
    return get(conn, new_id)


def update(conn, user, entry_id, kind=None, title=None, cum_tu_khop=None, content=None) -> dict:
    _clean(kind, title, cum_tu_khop, content)
    before = get(conn, entry_id)
    new = {"kind": kind, "title": title.strip() if title is not None else None,
           "cum_tu_khop": cum_tu_khop.strip() if cum_tu_khop is not None else None,
           "content": content.strip() if content is not None else None}
    changed = {k: v for k, v in new.items() if v is not None and v != before[k]}
    if not changed:
        return before
    if "title" in changed:
        if before["lien_ket"]:
            raise Conflict("Điểm nóng đang liên kết tới mục này, không đổi tên được (vẫn sửa được nội dung).")
        if conn.execute("SELECT 1 FROM kb_chunk WHERE title = %s AND id <> %s", (changed["title"], entry_id)).fetchone():
            raise Conflict("title already exists")
    sets = dict(changed)
    after_kind, after_content = changed.get("kind", before["kind"]), changed.get("content", before["content"])
    if ("content" in changed or "kind" in changed) and before["trang_thai"] == "dang_dung" and not is_approver(user) \
            and needs_price_approval(after_kind, after_content):
        sets["trang_thai"] = "cho_duyet"  # the chatbot stops quoting it until the lead architect approves the new figure
    cols = [f"{k} = %s" for k in sets]
    vals = list(sets.values())
    if "title" in changed or "cum_tu_khop" in changed:
        cols.append("embedding = %s::vector")
        vals.append(_embedding(changed.get("title", before["title"]), changed.get("cum_tu_khop", before["cum_tu_khop"])))
    conn.execute(f"UPDATE kb_chunk SET {', '.join(cols)}, updated_at = now(), updated_by = %s WHERE id = %s",
                 vals + [user["id"] if user else None, entry_id])
    _log(conn, user, entry_id, "sua", {k: before[k] for k in sets}, sets)
    return get(conn, entry_id)


def set_status(conn, user, entry_id, to: str) -> dict:
    if to not in STATUSES:
        raise Invalid(f"status must be one of {STATUSES}")
    before = get(conn, entry_id)
    if before["trang_thai"] == to:
        return before
    if before["trang_thai"] not in MOVES[to]:
        raise Invalid(f"cannot go from {before['trang_thai']} to {to}")
    sets = {"trang_thai": to}
    if to == "dang_dung":
        if before["can_duyet_gia"] and not is_approver(user):
            raise Forbidden("Mục có giá cần KTS trưởng duyệt trước khi trợ lý được nêu.")
        if before["ai"]:  # approved by a person: the "unreviewed" marker goes, the text becomes the studio's
            sets["content"] = before["content"][len(AI_MARK):].lstrip()
            sets["nguon"] = "nhan_vien"
    conn.execute(f"UPDATE kb_chunk SET {', '.join(k + ' = %s' for k in sets)}, updated_at = now(), updated_by = %s WHERE id = %s",
                 list(sets.values()) + [user["id"] if user else None, entry_id])
    closed = 0
    if to == "dang_dung" and before["tu_cau_hoi"]:
        closed = conn.execute("UPDATE khoang_trong_tri_thuc SET trang_thai = 'da_xu_ly', kb_chunk_id = %s "
                              "WHERE id = ANY(%s) AND trang_thai = 'mo'", (entry_id, before["tu_cau_hoi"])).rowcount
    _log(conn, user, entry_id, "trang_thai", {"trang_thai": before["trang_thai"]}, {**sets, "cau_hoi_da_dong": closed})
    return get(conn, entry_id)


def delete(conn, user, entry_id) -> None:
    before = get(conn, entry_id)
    if before["lien_ket"]:
        raise Conflict("Điểm nóng đang liên kết tới mục này, không xoá được.")
    conn.execute("DELETE FROM kb_chunk WHERE id = %s", (entry_id,))
    _log(conn, user, entry_id, "xoa", {k: before[k] for k in ("kind", "title", "content", "trang_thai")}, None)


# ── unanswered questions (khoang_trong_tri_thuc) ──────────────────────────────
def gaps(conn) -> list:
    """Open questions grouped by the same wording (case and accents ignored), most asked first."""
    groups: dict = {}
    for gid, q, terms, at in _tup(conn).execute("SELECT id, cau_hoi, tu_chua_khop, created_at FROM khoang_trong_tri_thuc "
                                          "WHERE trang_thai = 'mo' ORDER BY created_at DESC, id DESC").fetchall():
        key = " ".join(re.findall(r"[a-z0-9]+", fold(q)))
        g = groups.setdefault(key, {"cau_hoi": q.strip(), "ids": [], "so_lan": 0, "lan_cuoi": at, "tu_chua_khop": []})
        g["ids"].append(gid)
        g["so_lan"] += 1
        g["tu_chua_khop"] += [t for t in terms or [] if t not in g["tu_chua_khop"]]
    return sorted(groups.values(), key=lambda g: (-g["so_lan"], -g["lan_cuoi"].timestamp()))


def dismiss_gaps(conn, user, ids) -> int:
    n = conn.execute("UPDATE khoang_trong_tri_thuc SET trang_thai = 'bo_qua' WHERE id = ANY(%s) AND trang_thai = 'mo'",
                     (list(ids),)).rowcount
    _log(conn, user, None, "bo_qua_cau_hoi", None, {"ids": list(ids), "so_cau": n})
    return n
