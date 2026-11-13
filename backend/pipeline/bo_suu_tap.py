"""Saved collections (UC07, seq-13) and the frozen copies a design brief sends (UC08, seq-7).

'dang_luu' is an account's working collection, one per user. 'da_gui' is the copy a brief sent: its own rows,
a random share code, never edited afterwards. Anonymous working collections live in the visitor's browser only.
Every function takes an open connection (dict_row) so a caller can keep several steps in one transaction."""

import secrets

from psycopg.types.json import Jsonb

MAX_ITEMS, MAX_NOTE = 60, 300
SPACE_FIELDS = "s.id, s.relative_path, s.space_type, s.design_style, s.caption, s.alt_text"


class Full(Exception):
    """The collection already holds MAX_ITEMS spaces."""


def _clean(note):
    note = (note or "").strip()
    return note[:MAX_NOTE] or None


def published(c, space_ids) -> list[int]:
    """The given ids that are published, in the given order."""
    ok = {r["id"] for r in c.execute("SELECT id FROM space WHERE id = ANY(%s) AND review_status = 'published'",
                                     (list(space_ids),)).fetchall()}
    return [i for i in dict.fromkeys(space_ids) if i in ok]


def working_id(c, user_id: int) -> int:
    """The user's 'dang_luu' collection, created on first use."""
    c.execute("INSERT INTO bo_suu_tap (nguoi_dung_id, loai) VALUES (%s, 'dang_luu') "
              "ON CONFLICT (nguoi_dung_id) WHERE loai = 'dang_luu' DO NOTHING", (user_id,))
    return c.execute("SELECT id FROM bo_suu_tap WHERE nguoi_dung_id = %s AND loai = 'dang_luu'", (user_id,)).fetchone()["id"]


def items(c, coll_id: int) -> list[dict]:
    """Saved spaces still published, oldest first."""
    return c.execute(
        "SELECT a.space_id, a.ghi_chu, a.created_at FROM bo_suu_tap_anh a JOIN space s ON s.id = a.space_id "
        "WHERE a.bo_suu_tap_id = %s AND s.review_status = 'published' ORDER BY a.created_at, a.space_id",
        (coll_id,)).fetchall()


def put_item(c, user_id: int, space_id: int, note=None) -> bool:
    """Add a published space or update its note. False if the space is not published; Full at MAX_ITEMS."""
    if not published(c, [space_id]):
        return False
    cid = working_id(c, user_id)
    exists = c.execute("SELECT 1 FROM bo_suu_tap_anh WHERE bo_suu_tap_id = %s AND space_id = %s", (cid, space_id)).fetchone()
    if not exists and len(items(c, cid)) >= MAX_ITEMS:
        raise Full
    c.execute("INSERT INTO bo_suu_tap_anh (bo_suu_tap_id, space_id, ghi_chu) VALUES (%s, %s, %s) "
              "ON CONFLICT (bo_suu_tap_id, space_id) DO UPDATE SET ghi_chu = EXCLUDED.ghi_chu", (cid, space_id, _clean(note)))
    return True


def remove_item(c, user_id: int, space_id: int):
    c.execute("DELETE FROM bo_suu_tap_anh a USING bo_suu_tap b WHERE a.bo_suu_tap_id = b.id AND b.nguoi_dung_id = %s "
              "AND b.loai = 'dang_luu' AND a.space_id = %s", (user_id, space_id))


def merge(c, user_id: int, incoming: list[dict]) -> list[dict]:
    """Browser collection -> account at sign-in: add missing spaces (up to MAX_ITEMS), and let a browser note fill an
    empty account note. A non-empty account note wins."""
    cid = working_id(c, user_id)
    have = {r["space_id"]: r["ghi_chu"] for r in items(c, cid)}
    notes = {}
    for it in incoming:
        notes.setdefault(it["space_id"], _clean(it.get("ghi_chu")))
    for sid in published(c, list(notes)):
        if sid in have:
            if not have[sid] and notes[sid]:
                c.execute("UPDATE bo_suu_tap_anh SET ghi_chu = %s WHERE bo_suu_tap_id = %s AND space_id = %s",
                          (notes[sid], cid, sid))
        elif len(have) < MAX_ITEMS:
            c.execute("INSERT INTO bo_suu_tap_anh (bo_suu_tap_id, space_id, ghi_chu) VALUES (%s, %s, %s)",
                      (cid, sid, notes[sid]))
            have[sid] = notes[sid]
    return items(c, cid)


def send_copy(c, user_id, chosen: list[dict], tom_tat: dict) -> tuple[int, str]:
    """Freeze what a brief sends: a new 'da_gui' collection with its own rows and a share code."""
    code = secrets.token_urlsafe(12)
    cid = c.execute("INSERT INTO bo_suu_tap (nguoi_dung_id, loai, ma_chia_se, tom_tat) VALUES (%s, 'da_gui', %s, %s) "
                    "RETURNING id", (user_id, code, Jsonb(tom_tat))).fetchone()["id"]
    for it in chosen:
        c.execute("INSERT INTO bo_suu_tap_anh (bo_suu_tap_id, space_id, ghi_chu) VALUES (%s, %s, %s)",
                  (cid, it["space_id"], _clean(it.get("ghi_chu"))))
    return cid, code


def sent_items(c, coll_id: int) -> list[dict]:
    """Photos of a sent copy with their notes, as sent (a space unpublished later is left out)."""
    return c.execute(
        f"SELECT {SPACE_FIELDS}, a.ghi_chu FROM bo_suu_tap_anh a JOIN space s ON s.id = a.space_id "
        "WHERE a.bo_suu_tap_id = %s AND s.review_status = 'published' ORDER BY a.created_at, a.space_id",
        (coll_id,)).fetchall()


def shared(c, code: str) -> dict | None:
    """The read-only view of a sent brief: photos, notes, summary. No sender data."""
    row = c.execute("SELECT id, tom_tat, created_at FROM bo_suu_tap WHERE loai = 'da_gui' AND ma_chia_se = %s",
                    (code,)).fetchone()
    if not row:
        return None
    return {"items": sent_items(c, row["id"]), "tom_tat": row["tom_tat"], "created_at": row["created_at"]}
