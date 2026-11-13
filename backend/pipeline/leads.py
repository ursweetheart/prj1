"""Lead intake (change lead-intake; dfd-2-4 4.1, act-2, seq-5): every source — contact form, chat handoff, later the
brief and the estimate — creates its lead here, so all get the same consented behaviour profile and the same notice.

Following up a lead (call, assign, quote) happens outside the system (usecase-0 / usecase-4 note)."""

from collections import Counter

import psycopg
from psycopg.rows import dict_row, tuple_row
from psycopg.types.json import Jsonb

from pipeline.store import DSN

SOURCES = ("form", "chat", "brief", "estimate")
MAX_SPACES, MAX_TOP = 12, 5
SUMMARY_DIMS = ("phong_cach", "khong_gian")


def behaviour_profile(phien_id: str, conn=None) -> dict | None:
    """Snapshot of a consented session: newest distinct spaces viewed, most frequent facet values, number of views."""
    own = conn is None
    conn = conn or psycopg.connect(DSN)
    db = conn.cursor(row_factory=tuple_row)  # callers may hand over a dict_row connection
    try:
        events = db.execute("SELECT space_id, gia_tri FROM su_kien WHERE phien_id = %s ORDER BY created_at DESC, id DESC",
                              (phien_id,)).fetchall()
        if not events:
            return None
        ids = list(dict.fromkeys(e[0] for e in events if e[0] is not None))[:MAX_SPACES]
        rows = {r[0]: r for r in db.execute(
            "SELECT id, relative_path, space_type, design_style FROM space WHERE id = ANY(%s)", (ids,)).fetchall()}
        spaces = [{"id": i, "relative_path": rows[i][1], "space_type": rows[i][2], "design_style": rows[i][3]}
                  for i in ids if i in rows]
        counts = Counter(v for e in events for v in (e[1] or []))
        top = counts.most_common(MAX_TOP)
        for dim in SUMMARY_DIMS:  # the summary line needs the leading style and room even when ties push them out
            best = max(((k, n) for k, n in counts.items() if k.startswith(dim + ":") and not k.lower().endswith(":khac")),
                       key=lambda kv: kv[1], default=None)
            if best and best not in top:
                top.append(best)
        names = dict(db.execute(
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
        cands = [t for t in profile.get("top", []) if t["gia_tri"].startswith(dim + ":") and not t["gia_tri"].lower().endswith(":khac")]
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
                intent=None, request=None, conversation=None, contact=None, phien_id=None, gui_ho_so=False,
                bo_suu_tap_id=None, conn=None) -> int:
    """Store a lead. The profile (and the session link) is attached only when the visitor ticked "send what I viewed"
    AND the session exists — a phien_truy_cap row is written only after banner consent (act-7, NĐ13/2023)."""
    if nguon not in SOURCES:
        raise ValueError(f"unknown lead source {nguon!r}")
    own = conn is None  # a caller's connection keeps the lead in its transaction (the brief writes its copy first)
    conn = conn or psycopg.connect(DSN)
    db = conn.cursor(row_factory=tuple_row)
    try:
        profile = None
        if gui_ho_so and phien_id and db.execute("SELECT 1 FROM phien_truy_cap WHERE id = %s", (phien_id,)).fetchone():
            profile = behaviour_profile(phien_id, conn)
        else:
            phien_id = None
        lead_id = db.execute(
            "INSERT INTO lead (nguon, ho_ten, so_dien_thoai, email, loi_nhan, ngu_canh, intent, request, conversation, "
            "contact, phien_id, ho_so_hanh_vi, bo_suu_tap_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
            (nguon, ho_ten, so_dien_thoai, email, loi_nhan, Jsonb(ngu_canh) if ngu_canh else None, intent,
             Jsonb(request) if request is not None else None, Jsonb(conversation) if conversation is not None else None,
             contact, phien_id, Jsonb(profile) if profile else None, bo_suu_tap_id)).fetchone()[0]
        if own:
            conn.commit()
        return lead_id
    finally:
        if own:
            conn.close()


def brief_summary(space_ids, conn=None) -> dict:
    """What the photos a visitor chose have in common (seq-7 #7): leading style and its share, leading colour tone,
    up to 2 space types seen on at least 2 photos (the only one for a single photo). '*:khac' is never named.
    Chosen on purpose by the visitor, so unlike behaviour_profile this needs no collection consent."""
    own = conn is None
    conn = conn or psycopg.connect(DSN)
    try:
        rows = conn.cursor(row_factory=tuple_row).execute(
            "SELECT DISTINCT sg.space_id, d.ma_dinh_danh, v.ma_dinh_danh, v.ten FROM space_gia_tri sg "
            "JOIN gia_tri_phan_loai v ON v.id = sg.gia_tri_id JOIN chieu_phan_loai d ON d.id = v.chieu_id "
            "WHERE sg.space_id = ANY(%s) AND d.ma_dinh_danh IN ('phong_cach', 'tong_mau', 'khong_gian') "
            "AND lower(v.ma_dinh_danh) <> 'khac'", (list(space_ids),)).fetchall()
    finally:
        if own:
            conn.close()
    n = len(set(space_ids))
    counts = {dim: Counter() for dim in ("phong_cach", "tong_mau", "khong_gian")}
    names = {}
    for _, dim, code, ten in rows:
        counts[dim][code] += 1
        names[(dim, code)] = ten

    def ranked(dim):  # most photos first, then by code so ties are stable
        return sorted(counts[dim].items(), key=lambda kv: (-kv[1], kv[0]))

    style = ranked("phong_cach")[:1]
    tone = ranked("tong_mau")[:1]
    rooms = [kv for kv in ranked("khong_gian") if kv[1] >= 2 or n == 1][:2]
    parts = []
    if style:
        parts.append(f"{names[('phong_cach', style[0][0])]} {round(100 * style[0][1] / n)}%")
    if tone:
        parts.append(f"tông {names[('tong_mau', tone[0][0])]}")
    if rooms:
        parts.append(", ".join(names[("khong_gian", k)].lower() for k, _ in rooms))
    return {"n": n, "line": " · ".join(parts),
            "phong_cach": [{"gia_tri": k, "ten": names[("phong_cach", k)], "so_anh": c} for k, c in style],
            "tong_mau": [{"gia_tri": k, "ten": names[("tong_mau", k)], "so_anh": c} for k, c in tone],
            "khong_gian": [{"gia_tri": k, "ten": names[("khong_gian", k)], "so_anh": c} for k, c in rooms]}


def get_lead(lead_id: int) -> dict | None:
    with psycopg.connect(DSN, row_factory=dict_row) as conn:
        return conn.execute("SELECT * FROM lead WHERE id = %s", (lead_id,)).fetchone()
