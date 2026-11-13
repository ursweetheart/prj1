"""Lead intake (change lead-intake; dfd-2-4 4.1, act-2, seq-5): every source — contact form, chat handoff, later the
brief and the estimate — creates its lead here, so all get the same consented behaviour profile and the same notice.

Following up a lead (call, assign, quote) happens outside the system (usecase-0 / usecase-4 note)."""

from collections import Counter

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from pipeline.store import DSN

SOURCES = ("form", "chat", "brief", "estimate")
MAX_SPACES, MAX_TOP = 12, 5
SUMMARY_DIMS = ("phong_cach", "khong_gian")


def behaviour_profile(phien_id: str, conn=None) -> dict | None:
    """Snapshot of a consented session: newest distinct spaces viewed, most frequent facet values, number of views."""
    own = conn is None
    conn = conn or psycopg.connect(DSN)
    try:
        events = conn.execute("SELECT space_id, gia_tri FROM su_kien WHERE phien_id = %s ORDER BY created_at DESC, id DESC",
                              (phien_id,)).fetchall()
        if not events:
            return None
        ids = list(dict.fromkeys(e[0] for e in events if e[0] is not None))[:MAX_SPACES]
        rows = {r[0]: r for r in conn.execute(
            "SELECT id, relative_path, space_type, design_style FROM space WHERE id = ANY(%s)", (ids,)).fetchall()}
        spaces = [{"id": i, "relative_path": rows[i][1], "space_type": rows[i][2], "design_style": rows[i][3]}
                  for i in ids if i in rows]
        counts = Counter(v for e in events for v in (e[1] or []))
        top = counts.most_common(MAX_TOP)
        for dim in SUMMARY_DIMS:  # the summary line needs the leading style and room even when ties push them out
            best = max(((k, n) for k, n in counts.items() if k.startswith(dim + ":") and not k.endswith(":khac")),
                       key=lambda kv: kv[1], default=None)
            if best and best not in top:
                top.append(best)
        names = dict(conn.execute(
            "SELECT d.ma_dinh_danh || ':' || v.ma_dinh_danh, v.ten FROM gia_tri_phan_loai v "
            "JOIN chieu_phan_loai d ON d.id = v.chieu_id WHERE d.ma_dinh_danh || ':' || v.ma_dinh_danh = ANY(%s)",
            ([k for k, _ in top],)).fetchall()) if top else {}
        return {"spaces": spaces, "views": len(events),
                "top": [{"gia_tri": k, "ten": names.get(k, k.split(":", 1)[-1]), "so_lan": n} for k, n in top]}
    finally:
        if own:
            conn.close()


def profile_summary(profile: dict | None) -> str:
    """One line for the consultant: "Wabi-sabi 75% · phòng khách · 4 không gian" (style share of the views)."""
    if not profile:
        return ""
    views = profile.get("views") or 0
    def lead(dim):
        cands = [t for t in profile.get("top", []) if t["gia_tri"].startswith(dim + ":") and not t["gia_tri"].endswith(":khac")]
        return max(cands, key=lambda t: t["so_lan"], default=None)
    style, room = lead("phong_cach"), lead("khong_gian")
    parts = []
    if style and views:
        parts.append(f"{style['ten']} {round(100 * style['so_lan'] / views)}%")
    if room:
        parts.append(room["ten"].lower())
    parts.append(f"{len(profile.get('spaces', []))} không gian")
    return " · ".join(parts)


def create_lead(nguon: str, *, ho_ten=None, so_dien_thoai=None, email=None, loi_nhan=None, ngu_canh=None,
                intent=None, request=None, conversation=None, contact=None, phien_id=None, gui_ho_so=False) -> int:
    """Store a lead. The profile (and the session link) is attached only when the visitor ticked "send what I viewed"
    AND the session exists — a phien_truy_cap row is written only after banner consent (act-7, NĐ13/2023)."""
    if nguon not in SOURCES:
        raise ValueError(f"unknown lead source {nguon!r}")
    with psycopg.connect(DSN) as conn:
        profile = None
        if gui_ho_so and phien_id and conn.execute("SELECT 1 FROM phien_truy_cap WHERE id = %s", (phien_id,)).fetchone():
            profile = behaviour_profile(phien_id, conn)
        else:
            phien_id = None
        return conn.execute(
            "INSERT INTO lead (nguon, ho_ten, so_dien_thoai, email, loi_nhan, ngu_canh, intent, request, conversation, "
            "contact, phien_id, ho_so_hanh_vi) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (nguon, ho_ten, so_dien_thoai, email, loi_nhan, Jsonb(ngu_canh) if ngu_canh else None, intent,
             Jsonb(request) if request is not None else None, Jsonb(conversation) if conversation is not None else None,
             contact, phien_id, Jsonb(profile) if profile else None)).fetchone()[0]


def get_lead(lead_id: int) -> dict | None:
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        return conn.execute("SELECT * FROM lead WHERE id = %s", (lead_id,)).fetchone()
