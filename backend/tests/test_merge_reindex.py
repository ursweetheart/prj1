"""admin-tools 4.1: seq-15 b20-b22, a merge queues the refresh of the affected photos' descriptions."""
import uuid

import psycopg
import pytest

from conftest import client
from pipeline import space_knowledge, taxonomy, vertex
from pipeline.store import DSN


@pytest.fixture
def two_values(drafts):
    [sid] = drafts(1)
    tag = uuid.uuid4().hex[:5]
    with psycopg.connect(DSN) as c:
        dim = c.execute("SELECT id FROM chieu_phan_loai WHERE ma_dinh_danh='vat_lieu'").fetchone()[0]
        src = c.execute("INSERT INTO gia_tri_phan_loai (chieu_id, ma_dinh_danh, ten) VALUES (%s, %s, %s) RETURNING id",
                        (dim, f"tmr_a_{tag}", f"Đá Tmr {tag}")).fetchone()[0]
        dst = c.execute("INSERT INTO gia_tri_phan_loai (chieu_id, ma_dinh_danh, ten) VALUES (%s, %s, %s) RETURNING id",
                        (dim, f"tmr_b_{tag}", f"Gỗ Tmr {tag}")).fetchone()[0]
        c.execute("INSERT INTO space_gia_tri (space_id, gia_tri_id, nguon_tao) VALUES (%s, %s, 'nguoi')", (sid, src))
        c.execute("UPDATE space SET review_status='published' WHERE id=%s", (sid,))
    taxonomy.reload()
    yield sid, src, dst, tag
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM space_text WHERE space_id=%s", (sid,))
        c.execute("DELETE FROM hang_doi_tac_vu WHERE loai='cap_nhat_chi_muc' AND du_lieu->'space_ids' @> %s::jsonb", (f"[{sid}]",))
        c.execute("DELETE FROM space_gia_tri WHERE gia_tri_id = ANY(%s)", ([src, dst],))
        c.execute("DELETE FROM gia_tri_phan_loai WHERE id = ANY(%s)", ([src, dst],))
        c.execute("DELETE FROM nhat_ky_phan_loai WHERE doi_tuong LIKE %s", (f"%tmr_%_{tag}",))
    taxonomy.reload()


def test_merge_queues_refresh_and_description_drops_the_old_name(two_values, as_role, monkeypatch):
    sid, src, dst, tag = two_values
    monkeypatch.setattr(vertex, "embed", lambda texts, kind: [[0.01] * 768 for _ in texts])
    with psycopg.connect(DSN, autocommit=True) as c:
        space_knowledge.refresh(c, sid)
        assert f"Đá Tmr {tag}" in c.execute("SELECT transcript FROM space_text WHERE space_id=%s", (sid,)).fetchone()[0]
    r = client.post(f"/taxonomy/values/{src}/merge", json={"target_id": dst}, headers=as_role("lead_architect"))
    assert r.status_code == 200, r.text
    assert r.json()["so_anh_cap_nhat"] == 1
    with psycopg.connect(DSN, autocommit=True) as c:
        task = c.execute("SELECT id, du_lieu FROM hang_doi_tac_vu WHERE loai='cap_nhat_chi_muc' ORDER BY id DESC LIMIT 1").fetchone()
        assert task[1]["space_ids"] == [sid]
        space_knowledge.reindex(c, {"id": task[0], "du_lieu": task[1]}, {})
        text = c.execute("SELECT transcript FROM space_text WHERE space_id=%s", (sid,)).fetchone()[0]
    assert f"Đá Tmr {tag}" not in text and f"Gỗ Tmr {tag}" in text
