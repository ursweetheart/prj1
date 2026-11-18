"""A reviewer suggests a room type / style the taxonomy doesn't have yet (change: review-tag-autocomplete).

Before anything is saved: an exact match (code, name, synonym), then a near spelling, then Gemini looking at the photo
and the current values. Only a word none of them place becomes a suggestion (ung_vien_phan_loai, loai 'gia_tri'),
with Gemini's draft description and synonyms for the lead architect to edit, accept, map or reject.
"""

import difflib
import logging
from pathlib import Path

from psycopg.types.json import Jsonb

from pipeline import taxonomy, vertex

DIMS = {"khong_gian": "space_type", "phong_cach": "design_style"}  # dimension -> the space column it mirrors
SPELLING_CUTOFF = 0.8
IMG_DIR = Path("image_d3")
_log = logging.getLogger(__name__)

PROMPT = """Bạn là chuyên gia phân loại nội thất của D3 Studio. Một kiến trúc sư xem ảnh đính kèm và gõ "{text}" cho
chiều "{dim_ten}", nhưng danh mục hiện chưa có giá trị này.

Các giá trị đang có (mã: tên. mô tả):
{values}

Thông tin đã biết về ảnh: {facts}

Trả lời JSON:
{{"trung_voi": "<mã của giá trị đang có mà "{text}" CÙNG NGHĨA (từ đồng nghĩa, tên tiếng Việt / tiếng Anh, viết sai chính tả)>" hoặc null,
 "ly_do": "<một câu tiếng Việt: vì sao cùng nghĩa với giá trị đó, hoặc vì sao là giá trị riêng>",
 "gan_nhat": "<mã của giá trị đang có GẦN NHẤT với "{text}">" hoặc null,
 "khac_biet": "<một câu: "{text}" khác giá trị gần nhất ở điểm nào, nêu đặc điểm nhìn thấy được>",
 "dac_trung": ["<3-5 đặc điểm nhận biết "{text}": đồ nội thất, vật liệu, màu, hình khối, chi tiết>"],
 "anh_khop": <true nếu ẢNH ĐÍNH KÈM thể hiện rõ các đặc điểm của "{text}", false nếu không>,
 "nhan_xet_anh": "<một câu: ảnh có / thiếu đặc điểm nào của "{text}"; nếu không khớp, ảnh giống giá trị nào hơn>",
 "mo_ta": "<nếu là giá trị mới: 1-2 câu tiếng Việt định nghĩa {dim_ten} này NÓI CHUNG (đặc điểm nhận biết, vật liệu, màu, đồ nội thất), không tả riêng ảnh này>",
 "tu_dong_nghia": ["<2-5 cách gọi khác, chữ thường, có cả không dấu và tiếng Anh nếu có>"],
 "caption": "<15-30 từ tiếng Việt mô tả cảm xúc và điểm nhấn của CHÍNH ẢNH NÀY, coi {dim_ten} của ảnh là "{text}"; chỉ nhắc chi tiết thấy trong ảnh>",
 "alt_text": "<tiếng Việt, ngắn: '[Không gian] phong cách [Phong cách] [Vật liệu chính] D3 Studio', với {dim_ten} là "{text}">"}}
Chỉ trả "trung_voi" khi chắc chắn cùng nghĩa; một phong cách gần giống nhưng khác (vd Japandi và Scandinavian) là null."""


def key(text: str) -> str:
    return taxonomy.key(text)


def exact(dim: str, text: str) -> str | None:
    return taxonomy.resolve(dim, text)


def spelling(dim: str, text: str) -> str | None:
    """A near spelling of a code, name or synonym ("Japandy" -> Japandi), without the AI."""
    words = {}
    for ma, v in taxonomy.labelled().get(dim, {}).get("values", {}).items():
        for w in (ma, v["ten"], *v["syn"]):
            words.setdefault(key(w), ma)
    hit = difflib.get_close_matches(key(text), list(words), n=1, cutoff=SPELLING_CUTOFF)
    return words[hit[0]] if hit else None


def _facts(space: dict) -> str:
    labels = [o.get("label_vi") for o in ((space.get("hotspots") or {}).get("objects") or []) if o.get("label_vi")]
    palette = space.get("palette") or {}
    parts = [space.get("caption"), "vật liệu: " + ", ".join(space.get("materials") or []) if space.get("materials") else None,
             f"tông {palette.get('temperature')}, {palette.get('brightness')}" if palette else None,
             "đồ vật: " + ", ".join(labels) if labels else None]
    return "; ".join(p for p in parts if p) or "không có"


def ai_check(space: dict, dim: str, text: str) -> dict | None:
    """Gemini's view: {trung_voi: code | None, ly_do, gan_nhat, khac_biet, dac_trung[], anh_khop, nhan_xet_anh, mo_ta,
    tu_dong_nghia}: what the word means, how it differs from the closest value, and whether this photo shows it. None when Vertex is missing or fails,
    so the suggestion is still saved, just without a draft. A trung_voi that is not a current code is dropped."""
    if not vertex.available():
        return None
    tax = taxonomy.labelled().get(dim, {})
    values = "\n".join(f"- {ma}: {v['ten']}. {v.get('mo_ta') or ''}".rstrip(". ") for ma, v in tax.get("values", {}).items())
    parts = [{"text": PROMPT.format(text=text, dim_ten=tax.get("ten", dim), values=values, facts=_facts(space))}]
    try:
        from pipeline.multimodal_classifier import MultimodalClassifier
        b64, mime = MultimodalClassifier._prepare_image_payload(IMG_DIR / space["relative_path"])
        parts.append({"inline_data": {"mime_type": mime, "data": b64}})
    except Exception as e:  # the photo file is missing: the text facts still let Gemini judge the word
        _log.info("value_suggest: no image for space %s (%s)", space.get("id"), e)
    try:
        reply, _ = vertex.generate(parts)
    except Exception as e:
        _log.warning("value_suggest: Gemini failed (%s)", e)
        return None
    if not isinstance(reply, dict):
        return None
    same = reply.get("trung_voi")
    syn = reply.get("tu_dong_nghia")
    near = reply.get("gan_nhat")
    feats = reply.get("dac_trung")
    match = reply.get("anh_khop")
    return {"trung_voi": same if same in tax.get("values", {}) else None,
            "ly_do": str(reply.get("ly_do") or "")[:300],
            "gan_nhat": near if near in tax.get("values", {}) else None,
            "khac_biet": str(reply.get("khac_biet") or "")[:300],
            "dac_trung": [str(f).strip()[:120] for f in feats if str(f).strip()][:5] if isinstance(feats, list) else [],
            "anh_khop": match if isinstance(match, bool) else None,  # None: Gemini didn't say
            "nhan_xet_anh": str(reply.get("nhan_xet_anh") or "")[:300],
            "caption": str(reply.get("caption") or "").strip()[:2000],  # same limits as the photo's own fields
            "alt_text": str(reply.get("alt_text") or "").strip()[:300],
            "mo_ta": str(reply.get("mo_ta") or "")[:500],
            "tu_dong_nghia": [str(s).strip().lower()[:60] for s in syn if str(s).strip()][:5] if isinstance(syn, list) else []}


def _first(row):  # tuple rows (scripts, tests) or dict rows (the API's connections)
    return None if row is None else row["id"] if isinstance(row, dict) else row[0]


def pending(conn, dim: str, text: str) -> int | None:
    row = conn.execute("SELECT id FROM ung_vien_phan_loai WHERE loai = 'gia_tri' AND trang_thai = 'cho_duyet' "
                       "AND bang_chung->>'chieu' = %s AND bang_chung->>'khoa' = %s", (dim, key(text))).fetchone()
    return _first(row)


def upsert(conn, dim: str, text: str, space_id: int, user_id: int, draft: dict | None, space: dict | None = None) -> int:
    """One undecided suggestion per dimension + folded word: a second reviewer's photo is added to it.
    mo_ta_anh keeps, per photo, the caption / alt text the AI drafted for the new word and the caption the photo had
    then ('cu'): accepting writes the draft only if nobody changed the caption meanwhile."""
    draft = draft or {}
    captions = {}
    if draft.get("caption") and draft.get("anh_khop") is not False and space is not None:
        captions[str(space_id)] = {"caption": draft["caption"], "alt_text": draft.get("alt_text", ""), "cu": space.get("caption")}
    ev = {"chieu": dim, "khoa": key(text), "space_ids": [space_id], "nguoi_de_xuat": [user_id],
          "mo_ta": draft.get("mo_ta", ""), "tu_dong_nghia": draft.get("tu_dong_nghia", []),
          "ai": {k: draft.get(k) for k in ("ly_do", "trung_voi", "gan_nhat", "khac_biet", "dac_trung", "anh_khop", "nhan_xet_anh")}
          if draft else None, "mo_ta_anh": captions}
    return _first(conn.execute(
        "INSERT INTO ung_vien_phan_loai AS u (loai, ten_de_xuat, bang_chung) VALUES ('gia_tri', %s, %s) "
        "ON CONFLICT ((bang_chung->>'chieu'), (bang_chung->>'khoa')) WHERE loai = 'gia_tri' AND trang_thai = 'cho_duyet' "
        "DO UPDATE SET updated_at = now(), bang_chung = u.bang_chung || jsonb_build_object("
        "'space_ids', (SELECT jsonb_agg(DISTINCT x) FROM jsonb_array_elements((u.bang_chung->'space_ids') || (EXCLUDED.bang_chung->'space_ids')) x), "
        "'nguoi_de_xuat', (SELECT jsonb_agg(DISTINCT x) FROM jsonb_array_elements((u.bang_chung->'nguoi_de_xuat') || (EXCLUDED.bang_chung->'nguoi_de_xuat')) x), "
        "'mo_ta_anh', COALESCE(u.bang_chung->'mo_ta_anh', '{}') || (EXCLUDED.bang_chung->'mo_ta_anh')) "
        "RETURNING id", (text.strip(), Jsonb(ev))).fetchone())


# ── the approver decides (lead architect / admin) ───────────────────────────────────────────────────────────────
def _undecided(conn, cid) -> dict:
    from pipeline import taxonomy_admin as ta
    row = conn.execute("SELECT id, ten_de_xuat, bang_chung, trang_thai FROM ung_vien_phan_loai "
                       "WHERE id = %s AND loai = 'gia_tri' FOR UPDATE", (cid,)).fetchone()
    if not row:
        raise ta.NotFound("value suggestion not found")
    row = dict(row) if isinstance(row, dict) else dict(zip(("id", "ten_de_xuat", "bang_chung", "trang_thai"), row))
    if row["trang_thai"] != "cho_duyet":
        raise ta.Conflict(f"suggestion is {row['trang_thai']}, only cho_duyet can be decided")
    return row


def _redraft_captions(conn, user, cand, moved, ten) -> list[int]:
    """Moved photos get the caption / alt text the AI drafted for them, unless someone edited the caption since.
    The draft names the word the reviewer typed; an approver's rename is carried into it."""
    typed, done = cand["ten_de_xuat"], []
    for sid in moved:
        d = (cand["bang_chung"].get("mo_ta_anh") or {}).get(str(sid))
        if not d:
            continue
        row = conn.execute("SELECT caption, alt_text FROM space WHERE id = %s", (sid,)).fetchone()
        now, alt = (row["caption"], row["alt_text"]) if isinstance(row, dict) else row
        if now != d.get("cu"):
            continue  # a person rewrote it while the suggestion waited: theirs stays
        cap, new_alt = d["caption"].replace(typed, ten), (d.get("alt_text") or alt or "").replace(typed, ten)
        conn.execute("UPDATE space SET caption = %s, alt_text = %s WHERE id = %s", (cap, new_alt, sid))
        conn.execute("INSERT INTO review_log (space_id, user_id, action, detail) VALUES (%s, %s, 'edit', %s)",
                     (sid, user["id"], Jsonb({"from": {"caption": now, "alt_text": alt}, "to": {"caption": cap, "alt_text": new_alt},
                                              "goi_y": cand["id"], "nguon": "ai_soan_lai"})))
        done.append(sid)
    return done


def _move_waiting(conn, user, cand, code) -> list[int]:
    """Photos still on "Other" move to the decided value; a photo someone changed meanwhile is left alone."""
    dim = cand["bang_chung"]["chieu"]
    col, other = DIMS[dim], taxonomy.OTHER[dim]
    moved = [r[0] if not isinstance(r, dict) else r["id"] for r in conn.execute(
        f"UPDATE space SET {col} = %s WHERE id = ANY(%s) AND {col} = %s RETURNING id",
        (code, cand["bang_chung"].get("space_ids", []), other)).fetchall()]
    for sid in moved:
        conn.execute("INSERT INTO review_log (space_id, user_id, action, detail) VALUES (%s, %s, 'edit', %s)",
                     (sid, user["id"], Jsonb({"from": {col: other}, "to": {col: code}, "goi_y": cand["id"]})))
    return moved


def _close(conn, user, cand, status, extra):
    conn.execute("UPDATE ung_vien_phan_loai SET trang_thai = %s, updated_at = now(), bang_chung = bang_chung || %s WHERE id = %s",
                 (status, Jsonb({"nguoi_duyet": user["id"], **extra}), cand["id"]))


def _dim_id(conn, dim) -> int:
    row = conn.execute("SELECT id FROM chieu_phan_loai WHERE ma_dinh_danh = %s", (dim,)).fetchone()
    return row["id"] if isinstance(row, dict) else row[0]


def accept(conn, user, cid, ten: str, mo_ta=None, syn=None) -> dict:
    """Create the value (taxonomy log included; 409 if its code exists) and move the waiting photos to it."""
    from pipeline import taxonomy_admin as ta
    cand = _undecided(conn, cid)
    value = ta.add_value(conn, user, _dim_id(conn, cand["bang_chung"]["chieu"]), ten, mo_ta, syn)
    moved = _move_waiting(conn, user, cand, value["ma_dinh_danh"])
    rewritten = _redraft_captions(conn, user, cand, moved, value["ten"])
    _close(conn, user, cand, "chap_nhan", {"gia_tri_id": value["id"], "da_chuyen": moved, "viet_lai_mo_ta": rewritten})
    return {"gia_tri": value, "da_chuyen": moved, "viet_lai_mo_ta": rewritten}


def map_to(conn, user, cid, value_id: int) -> dict:
    """The word means an existing value: it becomes a synonym of it, and the waiting photos get that value."""
    from pipeline import taxonomy_admin as ta
    cand = _undecided(conn, cid)
    value = ta._value(conn, value_id)
    if value["chieu"] != cand["bang_chung"]["chieu"]:
        raise ta.Invalid("the value belongs to another dimension")
    value = ta.edit_value(conn, user, value_id, syn=[*(value["tu_dong_nghia"] or []), cand["ten_de_xuat"]])
    moved = _move_waiting(conn, user, cand, value["ma_dinh_danh"])
    rewritten = _redraft_captions(conn, user, cand, moved, value["ten"])
    _close(conn, user, cand, "chap_nhan", {"gia_tri_id": value_id, "gop_vao": True, "da_chuyen": moved, "viet_lai_mo_ta": rewritten})
    return {"gia_tri": value, "da_chuyen": moved, "viet_lai_mo_ta": rewritten}


def reject(conn, user, cid) -> dict:
    cand = _undecided(conn, cid)
    _close(conn, user, cand, "tu_choi", {})
    return {"id": cid, "trang_thai": "tu_choi"}
