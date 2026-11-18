"""POST /spaces/{id}/suggest-value (change: review-tag-autocomplete 3.3). Gemini is stubbed; throw-away spaces
'test_tsv_*' and suggestions whose folded word starts with 'tsv' are removed afterwards."""

import uuid

import psycopg
import pytest

from conftest import client
from pipeline import taxonomy, vertex
from pipeline.store import DSN


def _q(sql, *args):
    with psycopg.connect(DSN) as c:
        return c.execute(sql, args).fetchall()


@pytest.fixture
def scratch():
    yield
    with psycopg.connect(DSN) as c:
        c.execute("DELETE FROM review_log WHERE space_id IN (SELECT id FROM space WHERE relative_path LIKE 'test_tsv_%%')")
        c.execute("DELETE FROM space WHERE relative_path LIKE 'test_tsv_%%'")
        c.execute("DELETE FROM ung_vien_phan_loai WHERE loai = 'gia_tri' AND bang_chung->>'khoa' LIKE 'tsv%%'")
        c.execute("DELETE FROM gia_tri_phan_loai WHERE lower(ma_dinh_danh) LIKE 'tsv%%'")
        c.execute("DELETE FROM nhat_ky_phan_loai WHERE doi_tuong ILIKE '%%tsv%%' OR sau::text ILIKE '%%tsv%%'")
        c.execute("UPDATE gia_tri_phan_loai SET tu_dong_nghia = COALESCE((SELECT jsonb_agg(x) FROM "
                  "jsonb_array_elements_text(tu_dong_nghia) x WHERE x NOT ILIKE 'tsv%%'), '[]') WHERE tu_dong_nghia::text ILIKE '%%tsv%%'")
    taxonomy.reload()


def _space(style="Hien_dai"):
    with psycopg.connect(DSN) as c:
        return c.execute("INSERT INTO space (relative_path, space_type, design_style, review_status, caption) "
                         "VALUES (%s, 'phong_khach', %s, 'draft', 'Phòng khách gỗ sáng') RETURNING id",
                         (f"test_tsv_p/{uuid.uuid4().hex[:8]}.jpg", style)).fetchone()[0]


@pytest.fixture
def gemini(monkeypatch):
    """gemini(reply) -> list of prompts sent; gemini(None) -> Vertex unavailable."""
    calls = []

    def set_reply(reply=..., available=True):
        monkeypatch.setattr(vertex, "available", lambda: available)

        def fake(parts, **_):
            calls.append(parts[0]["text"])
            return reply, {}
        monkeypatch.setattr(vertex, "generate", fake)
        return calls
    return set_reply


NEW = {"trung_voi": None, "ly_do": "phong cách mới", "mo_ta": "Chân gỗ vát, đường cong hữu cơ.", "tu_dong_nghia": ["mcm"]}


def _suggest(sid, text, h, force=False, dim="phong_cach"):
    return client.post(f"/spaces/{sid}/suggest-value", json={"chieu": dim, "text": text, "force": force}, headers=h)


def test_exact_or_synonym_is_existing(scratch, as_role, gemini):
    calls = gemini(NEW)
    r = _suggest(_space(), "modern", as_role("architect")).json()
    assert r == {"kind": "existing", "ma": "Hien_dai", "source": "exact"} and not calls


def test_typo_offers_existing_without_ai(scratch, as_role, gemini):
    calls = gemini(NEW)
    r = _suggest(_space(), "Japandy", as_role("architect")).json()
    assert (r["kind"], r["ma"], r["source"]) == ("existing", "Japandi", "spelling") and not calls


def test_same_meaning_offers_existing_then_force_saves(scratch, as_role, gemini):
    calls = gemini({"trung_voi": "Japandi", "ly_do": "Nhật Bắc Âu là Japandi", "mo_ta": "", "tu_dong_nghia": []})
    sid, h = _space(), as_role("architect")
    r = _suggest(sid, "Tsv Nhật Bắc Âu", h).json()
    assert (r["kind"], r["ma"], r["source"]) == ("existing", "Japandi", "ai") and "Japandi" in r["ly_do"]
    assert _q("SELECT design_style FROM space WHERE id=%s", sid)[0][0] == "Hien_dai"  # nothing changed yet
    r = _suggest(sid, "Tsv Nhật Bắc Âu", h, force=True).json()
    assert r["kind"] == "suggested" and len(calls) == 2


def test_new_word_saves_suggestion_and_photo_waits_on_other(scratch, as_role, gemini):
    gemini(NEW)
    sid = _space()
    r = _suggest(sid, "Tsv Brutalist zeta", as_role("architect")).json()
    assert r["kind"] == "suggested"
    ten, ev = _q("SELECT ten_de_xuat, bang_chung FROM ung_vien_phan_loai WHERE id=%s", r["id"])[0]
    assert ten == "Tsv Brutalist zeta" and ev["space_ids"] == [sid] and ev["mo_ta"].startswith("Chân gỗ") and ev["tu_dong_nghia"] == ["mcm"]
    assert _q("SELECT design_style FROM space WHERE id=%s", sid)[0][0] == "Khac"
    assert _q("SELECT detail->'to'->>'design_style' FROM review_log WHERE space_id=%s AND action='edit'", sid)[0][0] == "Khac"


def test_room_type_waits_on_khac(scratch, as_role, gemini):
    gemini(NEW)
    sid = _space()
    assert _suggest(sid, "Tsv Phòng xông hơi", as_role("architect"), dim="khong_gian").json()["kind"] == "suggested"
    assert _q("SELECT space_type FROM space WHERE id=%s", sid)[0][0] == "khac"


def test_ai_unavailable_still_saves_without_draft(scratch, as_role, gemini):
    gemini(available=False)
    r = _suggest(_space(), "Tsv Art deco", as_role("architect")).json()
    assert r["kind"] == "suggested"
    assert _q("SELECT bang_chung->>'mo_ta' FROM ung_vien_phan_loai WHERE id=%s", r["id"])[0][0] == ""


def test_same_word_twice_is_one_suggestion_and_one_ai_call(scratch, as_role, gemini):
    calls = gemini(NEW)
    a, b = _space(), _space()
    r1 = _suggest(a, "Tsv Brutalist zeta", as_role("architect")).json()
    r2 = _suggest(b, "tsv brutalist-zeta", as_role("lead_architect")).json()
    assert r1["id"] == r2["id"] and len(calls) == 1
    assert sorted(_q("SELECT bang_chung->'space_ids' FROM ung_vien_phan_loai WHERE id=%s", r1["id"])[0][0]) == sorted([a, b])
    assert len(_q("SELECT bang_chung->'nguoi_de_xuat' FROM ung_vien_phan_loai WHERE id=%s", r1["id"])[0][0]) == 2


def test_roles_and_limits(scratch, as_role, gemini):
    gemini(NEW)
    sid = _space()
    assert _suggest(sid, "Tsv x", {}).status_code == 401
    assert _suggest(sid, "Tsv x", as_role("content")).status_code == 403
    assert _suggest(sid, "Tsv x", as_role("architect"), dim="vat_lieu").status_code == 422
    assert client.post("/spaces/999999999/suggest-value", json={"chieu": "phong_cach", "text": "Tsv q"},
                       headers=as_role("architect")).status_code == 404
    h = as_role("architect")
    codes = [_suggest(sid, f"Tsv word {i:02d} zq", h).status_code for i in range(11)]
    assert codes[:10] == [200] * 10 and codes[10] == 429


def test_review_list_shows_what_a_photo_waits_on(scratch, as_role, gemini):
    gemini(NEW)
    sid, h = _space(), as_role("architect")
    _suggest(sid, "Tsv Brutalist zeta", h)
    assert client.get("/spaces", params={"ids": str(sid)}, headers=h).json()[0]["cho_duyet_gia_tri"] == {"phong_cach": "Tsv Brutalist zeta"}
    assert client.get("/spaces", params={"ids": str(sid)}).json() == []  # visitors never see drafts


# ── 4.1 the approver decides ─────────────────────────────────────────────────────────────────────────────────
def _waiting(as_role, gemini, n=1, word="Tsv Brutalist zeta"):
    gemini(NEW)
    ids = [_space() for _ in range(n)]
    cid = None
    for sid in ids:
        cid = _suggest(sid, word, as_role("architect")).json()["id"]
    return cid, ids


def _dec(cid, action, h, **body):
    return client.post(f"/taxonomy/value-candidates/{cid}/{action}", json=body or None, headers=h)


def test_listing_shows_value_suggestions_with_waiting_photos(scratch, as_role, gemini):
    cid, ids = _waiting(as_role, gemini, n=2)
    out = client.get("/taxonomy/candidates", headers=as_role("lead_architect")).json()
    v = next(x for x in out["gia_tri"] if x["id"] == cid)
    assert v["ten_de_xuat"] == "Tsv Brutalist zeta" and v["bang_chung"]["mo_ta"].startswith("Chân gỗ")
    assert [s["id"] for s in v["cho"]] == sorted(ids)


def test_accept_creates_value_and_moves_waiting_photos(scratch, as_role, gemini):
    cid, (a, b) = _waiting(as_role, gemini, n=2)
    lead = as_role("lead_architect")
    with psycopg.connect(DSN) as c:  # b was set by hand while the suggestion waited
        c.execute("UPDATE space SET design_style = 'Japandi' WHERE id = %s", (b,))
    r = _dec(cid, "accept", lead, ten="Tsv Brutalist zeta", mo_ta="Chân gỗ vát.", tu_dong_nghia=["mcm"])
    assert r.status_code == 201, r.text
    code = r.json()["gia_tri"]["ma_dinh_danh"]
    assert r.json()["da_chuyen"] == [a]
    assert _q("SELECT design_style FROM space WHERE id=%s", a)[0][0] == code
    assert _q("SELECT design_style FROM space WHERE id=%s", b)[0][0] == "Japandi"
    tags = {t[0] for t in _q("SELECT v.ma_dinh_danh FROM space_gia_tri sg JOIN gia_tri_phan_loai v ON v.id = sg.gia_tri_id "
                             "WHERE sg.space_id = %s", a)}
    assert code in tags
    assert _q("SELECT mo_ta, tu_dong_nghia FROM gia_tri_phan_loai WHERE ma_dinh_danh=%s", code)[0] == ("Chân gỗ vát.", ["mcm"])
    assert _q("SELECT hanh_dong FROM nhat_ky_phan_loai WHERE doi_tuong LIKE %s", f"%{code}")[0][0] == "them_gia_tri"
    assert _q("SELECT trang_thai FROM ung_vien_phan_loai WHERE id=%s", cid)[0][0] == "chap_nhan"
    assert code in taxonomy.values("phong_cach")  # the autocomplete and the AI see it straight away
    assert _dec(cid, "reject", lead).status_code == 409  # decided once


def test_accept_with_taken_name_is_409_and_changes_nothing(scratch, as_role, gemini):
    cid, (a,) = _waiting(as_role, gemini)
    assert _dec(cid, "accept", as_role("lead_architect"), ten="Japandi").status_code == 409
    assert _q("SELECT trang_thai FROM ung_vien_phan_loai WHERE id=%s", cid)[0][0] == "cho_duyet"
    assert _q("SELECT design_style FROM space WHERE id=%s", a)[0][0] == "Khac"


def test_map_adds_synonym_and_moves_photos(scratch, as_role, gemini):
    cid, (a,) = _waiting(as_role, gemini, word="Tsv Nhật Bắc Âu")
    japandi = _q("SELECT v.id FROM gia_tri_phan_loai v JOIN chieu_phan_loai d ON d.id = v.chieu_id "
                 "WHERE d.ma_dinh_danh = 'phong_cach' AND v.ma_dinh_danh = 'Japandi'")[0][0]
    r = _dec(cid, "map", as_role("lead_architect"), gia_tri_id=japandi)
    assert r.status_code == 200, r.text
    assert "tsv nhật bắc âu" in _q("SELECT tu_dong_nghia FROM gia_tri_phan_loai WHERE id=%s", japandi)[0][0]
    assert _q("SELECT design_style FROM space WHERE id=%s", a)[0][0] == "Japandi"
    other_dim = _q("SELECT v.id FROM gia_tri_phan_loai v JOIN chieu_phan_loai d ON d.id = v.chieu_id "
                   "WHERE d.ma_dinh_danh = 'khong_gian' LIMIT 1")[0][0]
    cid2, _ = _waiting(as_role, gemini, word="Tsv Khác chiều")
    assert _dec(cid2, "map", as_role("lead_architect"), gia_tri_id=other_dim).status_code == 422


def test_reject_leaves_photos_on_other_and_note_gone(scratch, as_role, gemini):
    cid, (a,) = _waiting(as_role, gemini)
    assert _dec(cid, "reject", as_role("lead_architect")).status_code == 200
    assert _q("SELECT design_style FROM space WHERE id=%s", a)[0][0] == "Khac"
    h = as_role("architect")
    assert client.get("/spaces", params={"ids": str(a)}, headers=h).json()[0]["cho_duyet_gia_tri"] == {}


def test_only_approvers_decide(scratch, as_role, gemini):
    cid, _ = _waiting(as_role, gemini)
    h = as_role("architect")
    assert _dec(cid, "accept", h, ten="Tsv X").status_code == 403
    assert _dec(cid, "reject", h).status_code == 403
    assert client.get("/taxonomy/candidates", headers=h).status_code == 403
    assert _dec(999999999, "reject", as_role("lead_architect")).status_code == 404


def test_reviewer_is_warned_when_the_photo_does_not_show_the_word(scratch, as_role, gemini):
    gemini({**NEW, "anh_khop": False, "nhan_xet_anh": "Ảnh giống Indochine hơn", "gan_nhat": "Indochine",
            "dac_trung": ["chân gỗ vát"]})
    r = _suggest(_space(), "Tsv Brutalist zeta", as_role("architect")).json()
    assert r["kind"] == "suggested" and r["canh_bao"] == "Ảnh giống Indochine hơn" and r["gan_nhat"] == "Indochine"
    ai = _q("SELECT bang_chung->'ai' FROM ung_vien_phan_loai WHERE id=%s", r["id"])[0][0]
    assert ai["dac_trung"] == ["chân gỗ vát"] and ai["anh_khop"] is False  # the lead architect sees the same
    gemini({**NEW, "anh_khop": True, "nhan_xet_anh": "khớp"})
    assert "canh_bao" not in _suggest(_space(), "Tsv Art deco", as_role("architect")).json()


def test_same_call_drafts_caption_only_when_the_photo_matches(scratch, as_role, gemini):
    calls = gemini({**NEW, "anh_khop": True, "caption": "Phòng khách bê tông thô, khối hình mạnh.",
                    "alt_text": "Phòng khách phong cách Brutalist bê tông D3 Studio"})
    sid = _space()
    r = _suggest(sid, "Tsv Brutalist zeta", as_role("architect")).json()
    assert r["caption"].startswith("Phòng khách bê tông") and "Brutalist" in r["alt_text"] and len(calls) == 1
    assert _q("SELECT caption FROM space WHERE id=%s", sid)[0][0] == "Phòng khách gỗ sáng"  # unsaved until Lưu
    assert "TSV BRUTALIST ZETA".lower() in calls[0].lower()  # the prompt asks for the caption with the new word
    gemini({**NEW, "anh_khop": False, "nhan_xet_anh": "giống Indochine", "caption": "sai"})
    r = _suggest(_space(), "Tsv Other zeta", as_role("architect")).json()
    assert "caption" not in r and r["canh_bao"] == "giống Indochine"


DRAFT = {**NEW, "anh_khop": True, "caption": "Phòng khách Tsv Brutalist zeta với bê tông thô, khối hình mạnh.",
         "alt_text": "Phòng khách phong cách Tsv Brutalist zeta bê tông D3 Studio"}


def test_accept_writes_the_drafted_caption_unless_someone_edited_it(scratch, as_role, gemini):
    gemini(DRAFT)
    h = as_role("architect")
    a, b = _space(), _space()
    cid = _suggest(a, "Tsv Brutalist zeta", h).json()["id"]
    _suggest(b, "Tsv Brutalist zeta", h)  # joins: no AI call, so no caption draft for b
    ev = _q("SELECT bang_chung->'mo_ta_anh' FROM ung_vien_phan_loai WHERE id=%s", cid)[0][0]
    assert set(ev) == {str(a)} and ev[str(a)]["cu"] == "Phòng khách gỗ sáng"
    r = _dec(cid, "accept", as_role("lead_architect"), ten="Tsv Bê tông thô")
    assert r.status_code == 201, r.text
    assert r.json()["viet_lai_mo_ta"] == [a]
    cap, alt = _q("SELECT caption, alt_text FROM space WHERE id=%s", a)[0]
    assert cap == "Phòng khách Tsv Bê tông thô với bê tông thô, khối hình mạnh."  # the approver's name, not the typed word
    assert "Tsv Bê tông thô" in alt
    assert _q("SELECT caption FROM space WHERE id=%s", b)[0][0] == "Phòng khách gỗ sáng"
    log = _q("SELECT detail FROM review_log WHERE space_id=%s AND detail->>'nguon' = 'ai_soan_lai'", a)[0][0]
    assert log["from"]["caption"] == "Phòng khách gỗ sáng"


def test_a_caption_edited_while_waiting_is_kept(scratch, as_role, gemini):
    gemini(DRAFT)
    a = _space()
    cid = _suggest(a, "Tsv Brutalist zeta", as_role("architect")).json()["id"]
    with psycopg.connect(DSN) as conn:
        conn.execute("UPDATE space SET caption = 'Chữ của người' WHERE id = %s", (a,))
    r = _dec(cid, "accept", as_role("lead_architect"), ten="Tsv Brutalist zeta").json()
    assert r["da_chuyen"] == [a] and r["viet_lai_mo_ta"] == []
    assert _q("SELECT caption FROM space WHERE id=%s", a)[0][0] == "Chữ của người"


def test_map_rewrites_the_caption_with_the_existing_value_name(scratch, as_role, gemini):
    gemini(DRAFT)
    a = _space()
    cid = _suggest(a, "Tsv Brutalist zeta", as_role("architect")).json()["id"]
    luxury = _q("SELECT v.id FROM gia_tri_phan_loai v JOIN chieu_phan_loai d ON d.id = v.chieu_id "
                "WHERE d.ma_dinh_danh = 'phong_cach' AND v.ma_dinh_danh = 'Luxury'")[0][0]
    assert _dec(cid, "map", as_role("lead_architect"), gia_tri_id=luxury).json()["viet_lai_mo_ta"] == [a]
    assert "phong cách Luxury" in _q("SELECT alt_text FROM space WHERE id=%s", a)[0][0]
