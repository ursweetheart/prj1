"""labelling-queue-feedback 4.1: corrected labels are recorded for model evaluation (seq-1 b21)."""
import psycopg

from conftest import client
from pipeline import label_feedback
from pipeline.store import DSN


def _fix(sid):
    with psycopg.connect(DSN) as c:
        return c.execute("SELECT chieu, ai_gia_tri, gia_tri_dung FROM nhan_bi_sua WHERE space_id=%s ORDER BY chieu",
                         (sid,)).fetchall()


def test_correction_then_revert(drafts, as_role):
    sid = drafts(1, "design_style = design_style_ai AND space_type = space_type_ai")[0]
    with psycopg.connect(DSN) as c:
        ai = c.execute("SELECT design_style_ai FROM space WHERE id=%s", (sid,)).fetchone()[0]
    other = "Japandi" if ai != "Japandi" else "Indochine"
    h = as_role("architect")
    assert client.patch(f"/spaces/{sid}", json={"design_style": other}, headers=h).status_code == 200
    assert _fix(sid) == [("phong_cach", ai, other)]
    assert client.patch(f"/spaces/{sid}", json={"design_style": ai}, headers=h).status_code == 200
    assert _fix(sid) == []


def test_one_row_per_photo_and_dimension_with_the_latest_value(drafts):
    sid = drafts(1, "design_style = design_style_ai AND space_type = space_type_ai")[0]
    with psycopg.connect(DSN) as c:
        ai = c.execute("SELECT design_style_ai FROM space WHERE id=%s", (sid,)).fetchone()[0]
        for v in ("Khac", "Indochine" if ai != "Indochine" else "Japandi"):  # waiting on a suggestion, then decided
            c.execute("UPDATE space SET design_style=%s WHERE id=%s", (v, sid))
            label_feedback.record(c, sid, None)
        rows = c.execute("SELECT count(*), max(gia_tri_dung) FROM nhan_bi_sua WHERE space_id=%s", (sid,)).fetchone()
    assert rows[0] == 1 and rows[1] != "Khac"


def test_room_type_corrections_too(drafts):
    sid = drafts(1, "design_style = design_style_ai AND space_type = space_type_ai")[0]
    with psycopg.connect(DSN) as c:
        ai = c.execute("SELECT space_type_ai FROM space WHERE id=%s", (sid,)).fetchone()[0]
        new = "phong_tam" if ai != "phong_tam" else "phong_khach"
        c.execute("UPDATE space SET space_type=%s WHERE id=%s", (new, sid))
        assert label_feedback.record(c, sid, None) == {"khong_gian": new, "phong_cach": None}
