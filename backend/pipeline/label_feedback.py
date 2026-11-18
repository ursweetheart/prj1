"""Corrected labels for model evaluation (labelling-queue-feedback; seq-1 b20-b21).

One row per photo and dimension in nhan_bi_sua while the saved room type / style differs from what the AI proposed
(space.space_type_ai / design_style_ai). Saving the AI's value again removes the row, so the table is always the
current set of corrections; review_log keeps the full history.
"""

from psycopg.rows import tuple_row

DIMS = (("khong_gian", "space_type", "space_type_ai", "space_type_confidence"),
        ("phong_cach", "design_style", "design_style_ai", "style_confidence"))


def record(conn, space_id: int, user_id: int | None) -> dict:
    """Compare the photo's labels with the AI's proposal and update its corrections. -> {chieu: correct value or None}"""
    cur = conn.cursor(row_factory=tuple_row)
    row = cur.execute(f"SELECT {', '.join(f'{col}, {ai}, {conf}' for _, col, ai, conf in DIMS)} FROM space WHERE id = %s",
                      (space_id,)).fetchone()
    if row is None:
        return {}
    out = {}
    for i, (chieu, *_cols) in enumerate(DIMS):
        now, ai, conf = row[3 * i: 3 * i + 3]
        if ai is None or now == ai:  # no AI proposal to compare with, or the AI was right after all
            cur.execute("DELETE FROM nhan_bi_sua WHERE space_id = %s AND chieu = %s", (space_id, chieu))
            out[chieu] = None
            continue
        cur.execute("INSERT INTO nhan_bi_sua (space_id, chieu, ai_gia_tri, do_tin_cay, gia_tri_dung, nguoi_id) "
                    "VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT (space_id, chieu) DO UPDATE SET "
                    "gia_tri_dung = EXCLUDED.gia_tri_dung, nguoi_id = EXCLUDED.nguoi_id, luc = now(), "
                    "ai_gia_tri = EXCLUDED.ai_gia_tri, do_tin_cay = EXCLUDED.do_tin_cay",
                    (space_id, chieu, ai, conf, now, user_id))
        out[chieu] = now
    return out
