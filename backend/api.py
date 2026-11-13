"""D3 Studio AI API.  Run: uvicorn api:app --reload"""

import io
import os
import re
import shutil
from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

import psycopg
from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi import Path as PathParam
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from PIL import Image
from psycopg.types.json import Jsonb
from starlette.middleware.sessions import SessionMiddleware
from psycopg.rows import dict_row
from psycopg.errors import UniqueViolation
from pydantic import BaseModel, Field, field_validator, model_validator

import auth
from pipeline import bo_suu_tap, discovery, estimate, leads, notify, taxonomy, vertex
from pipeline.assistant import _fold, respond, with_services
from auth import APPROVERS, ROLES, STAFF, optional_user, require
from pipeline.schemas import SpaceClassificationResult
from pipeline.search import by_image, by_text, similar_to
from pipeline.store import DSN, save_records
from ratelimit import limit

IMG_DIR = Path("image_d3")
UPLOAD_DIR = IMG_DIR / "uploads"
IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".webp"}
MAX_UPLOAD = 8 * 1024 * 1024  # photo search; nginx allows 50 MB, so this is the limit users hit
FIELDS = "id, relative_path, space_type, design_style, style_confidence, materials, caption, alt_text, review_status"
# taxonomy values of each space as {dimension: [value, ...]}; the portfolio filters on these
TAGS = ("(SELECT COALESCE(jsonb_object_agg(dim, vals), '{}') FROM (SELECT d.ma_dinh_danh AS dim, jsonb_agg(v.ma_dinh_danh) AS vals "
        "FROM space_gia_tri sg JOIN gia_tri_phan_loai v ON v.id = sg.gia_tri_id JOIN chieu_phan_loai d ON d.id = v.chieu_id "
        "WHERE sg.space_id = space.id GROUP BY d.ma_dinh_danh) t) AS tags")
# QT-01 order; an architect confirms AI tags before anything is published
NEXT = {"draft": "in_review", "in_review": "approved", "approved": "cleared", "cleared": "published"}
SPACE_TYPES = SpaceClassificationResult.model_fields["space_type"].annotation.__args__
STYLES = SpaceClassificationResult.model_fields["design_style"].annotation.__args__

app = FastAPI(title="D3 Studio AI")
app.add_middleware(SessionMiddleware, secret_key=auth.SECRET)  # only holds the OAuth state during Google sign-in
if origins := [o.strip() for o in os.getenv("D3_CORS_ORIGINS", "").split(",") if o.strip()]:
    # the site on GitHub Pages calls this API from another origin; tokens travel in the Authorization header, so no cookies
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["Authorization", "Content-Type"])
app.include_router(auth.router)
IMG_DIR.mkdir(exist_ok=True)
app.mount("/images", StaticFiles(directory=IMG_DIR), name="images")


def _db():
    return psycopg.connect(DSN, row_factory=dict_row)


def _is_staff(user) -> bool:  # staff and content editors see every review state; everyone else only published spaces
    return bool(user) and user["role"] in STAFF | {"content"}


def _log(c, space_id, user, action, detail):
    c.execute("INSERT INTO review_log (space_id, user_id, action, detail) VALUES (%s,%s,%s,%s)",
              (space_id, user["id"], action, Jsonb(detail)))


def _hit(r):  # tuple from pipeline.search -> dict
    return {"relative_path": r[0], "space_type": r[1], "design_style": r[2], "score": round(float(r[3]), 4), "id": r[4]}


@lru_cache(maxsize=1)
def _processor():  # loads YOLO + SigLIP2 on first ingest only
    from pipeline.processor import SpaceImageProcessor
    return SpaceImageProcessor()


@app.get("/spaces")
def list_spaces(space_type: Optional[str] = None, design_style: Optional[str] = None,
                review_status: Optional[str] = None, limit: int = 50, offset: int = 0,
                ids: Optional[str] = Query(default=None, pattern=r"^\d+(,\d+)*$", description="comma list, ≤ 60"),
                user=Depends(optional_user)):
    id_list = [int(i) for i in ids.split(",")] if ids else None  # the browser collection shows its photos in one call
    if id_list and len(id_list) > bo_suu_tap.MAX_ITEMS:
        raise HTTPException(422, f"at most {bo_suu_tap.MAX_ITEMS} ids")
    if not _is_staff(user):
        review_status = "published" if review_status in (None, "published") else "none"  # no such status: matches nothing
    with _db() as c:
        return c.execute(
            f"SELECT {FIELDS}, palette->>'brightness' AS brightness, palette->>'temperature' AS temperature, {TAGS} "
            "FROM space WHERE (%(t)s::text IS NULL OR space_type=%(t)s) "
            "AND (%(s)s::text IS NULL OR design_style=%(s)s) AND (%(r)s::text IS NULL OR review_status=%(r)s) "
            "AND (%(i)s::int[] IS NULL OR id = ANY(%(i)s)) ORDER BY id LIMIT %(l)s OFFSET %(o)s",
            {"t": space_type, "s": design_style, "r": review_status, "i": id_list,
             "l": max(min(limit, 200), len(id_list or [])), "o": offset}).fetchall()


@app.get("/spaces/{space_id}")
def get_space(space_id: int, user=Depends(optional_user)):
    with _db() as c:
        row = c.execute(f"SELECT {FIELDS}, palette, hotspots FROM space WHERE id=%s", (space_id,)).fetchone()
    if not row or (row["review_status"] != "published" and not _is_staff(user)):
        raise HTTPException(404, "space not found")  # 404, not 403: do not reveal unpublished spaces
    row["hotspots"] = with_services(row["hotspots"])
    return row


@app.get("/spaces/{space_id}/similar")
def similar(space_id: int, k: int = 6, user=Depends(optional_user)):
    with _db() as c:
        row = c.execute("SELECT relative_path, review_status FROM space WHERE id=%s", (space_id,)).fetchone()
    staff = _is_staff(user)
    if not row or (row["review_status"] != "published" and not staff):
        raise HTTPException(404, "space not found")
    return [_hit(r) for r in similar_to(row["relative_path"], min(k, 24), published_only=not staff)]


@app.get("/projects/{folder}/spaces")
def project_spaces(folder: str = PathParam(pattern=r"^[a-z0-9_]{1,60}$"), user=Depends(optional_user)):
    """Spaces of one project folder (the site's slug with '-' -> '_'), by file name; visitors get published ones only."""
    with _db() as c:
        return c.execute(
            f"SELECT {FIELDS} FROM space WHERE split_part(relative_path, '/', 1) = %(f)s "
            "AND (%(all)s OR review_status = 'published') ORDER BY relative_path",
            {"f": folder, "all": _is_staff(user)}).fetchall()


@app.get("/search")
def search(q: str, space_type: Optional[str] = None, k: int = 6, user=Depends(optional_user)):
    if space_type and space_type not in SPACE_TYPES:
        raise HTTPException(422, f"space_type must be one of {SPACE_TYPES}")
    return [_hit(r) for r in by_text(q, space_type, min(k, 24), published_only=not _is_staff(user))]


@app.post("/search/image", dependencies=[Depends(limit("search_image", 10, 60))])
def search_image(file: UploadFile = File(...), space_type: Optional[str] = Form(None), k: int = 6,
                 user=Depends(optional_user)):
    """Spaces that look like the uploaded photo; the photo is embedded in memory and never stored."""
    if Path(file.filename or "").suffix.lower() not in IMAGE_TYPES:
        raise HTTPException(415, "Chỉ nhận ảnh JPG, PNG hoặc WEBP.")
    if space_type and space_type not in SPACE_TYPES:
        raise HTTPException(422, f"space_type must be one of {SPACE_TYPES}")
    data = file.file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "Ảnh quá lớn, tối đa 8 MB.")
    try:
        hits = by_image(io.BytesIO(data), space_type, k, published_only=not _is_staff(user))
    except (OSError, Image.DecompressionBombError):  # not an image, truncated, or a decompression bomb
        raise HTTPException(415, "Không đọc được ảnh này, hãy thử một ảnh JPG, PNG hoặc WEBP khác.")
    return [_hit(r) for r in hits]


def project_folder(name: str) -> str:
    """'Biệt thự Thảo Điền' -> 'biet_thu_thao_dien': the folder doubles as the project name, keep it URL- and path-safe."""
    return re.sub(r"[^a-z0-9]+", "_", _fold(name)).strip("_")[:60]


@app.post("/spaces/ingest", status_code=201)
def ingest(file: UploadFile = File(...), project: str = Form(""), user=Depends(require(*STAFF))):
    if Path(file.filename or "").suffix.lower() not in IMAGE_TYPES:
        raise HTTPException(415, "image only (jpg/png/webp)")
    folder = IMG_DIR / (project_folder(project) or UPLOAD_DIR.name)
    folder.mkdir(exist_ok=True)
    dest = folder / Path(file.filename).name  # .name strips any path component; same name in a project = re-upload
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    rec = _processor().process_image(dest, base_dir=IMG_DIR)  # sync on purpose: GPU is a single resource
    save_records([rec])
    with _db() as c:
        row = c.execute(f"SELECT {FIELDS} FROM space WHERE relative_path=%s", (rec.relative_path,)).fetchone()
        _log(c, row["id"], user, "ingest", {"relative_path": rec.relative_path})
        return row


class HotspotKeep(BaseModel):
    index: int = Field(ge=0)  # position in the detector's objects list
    label_vi: str = Field(min_length=1, max_length=120)


class Review(BaseModel):
    space_type: Optional[str] = None
    design_style: Optional[str] = None
    caption: Optional[str] = Field(default=None, max_length=2000)
    alt_text: Optional[str] = Field(default=None, max_length=300)
    materials: Optional[list[str]] = Field(default=None, max_length=12)
    hotspots: Optional[list[HotspotKeep]] = None  # objects to keep, in order; the rest are dropped
    advance: bool = False  # move to the next review state
    rights_confirmed: bool = False  # the client allowed publishing these photos; needed to reach 'cleared'


EDITABLE = ("space_type", "design_style", "caption", "alt_text", "materials")
TEXT = {"caption", "alt_text"}  # all the content role may touch


def _advance(c, space_id: int, status: str, user, rights_confirmed: bool) -> str:
    """One QT-01 step with its role and rights rules. Raising inside `with _db()` rolls the transaction back."""
    if status not in NEXT:
        raise HTTPException(409, f"space {space_id}: '{status}' is the final state")
    if status != "draft" and user["role"] not in APPROVERS:  # only the lead architect approves, clears, publishes
        raise HTTPException(403, f"space {space_id}: approving, clearing and publishing require lead_architect")
    new = NEXT[status]
    if new == "cleared" and not rights_confirmed:
        raise HTTPException(422, f"space {space_id}: confirm the client allowed publishing these photos (rights_confirmed)")
    c.execute("UPDATE space SET review_status=%s WHERE id=%s", (new, space_id))
    _log(c, space_id, user, "advance", {"from": status, "to": new, **({"rights_confirmed": True} if new == "cleared" else {})})
    return new


@app.patch("/spaces/{space_id}")
def review(space_id: int, body: Review, user=Depends(require(*STAFF, "content"))):
    if body.space_type and body.space_type not in SPACE_TYPES:
        raise HTTPException(422, f"space_type must be one of {SPACE_TYPES}")
    if body.design_style and body.design_style not in STYLES:
        raise HTTPException(422, f"design_style must be one of {STYLES}")
    sent = {k: v for k, v in body.model_dump(include=set(EDITABLE)).items() if v is not None}
    if "materials" in sent:
        sent["materials"] = [m.strip() for m in sent["materials"] if m.strip()]
    with _db() as c:
        row = c.execute("SELECT review_status, space_type, design_style, caption, alt_text, materials, hotspots "
                        "FROM space WHERE id=%s FOR UPDATE", (space_id,)).fetchone()
        if not row:
            raise HTTPException(404, "space not found")
        if user["role"] == "content" and (body.advance or body.hotspots is not None or set(sent) - TEXT
                                          or row["review_status"] != "in_review"):
            raise HTTPException(403, "content editors may only edit the caption and alt text of spaces in review")
        if changes := {k: v for k, v in sent.items() if v != row[k]}:
            c.execute(f"UPDATE space SET {', '.join(k + '=%s' for k in changes)} WHERE id=%s", (*changes.values(), space_id))
            _log(c, space_id, user, "edit", {"from": {k: row[k] for k in changes}, "to": changes})
        if body.hotspots is not None:
            objs = (row["hotspots"] or {}).get("objects", [])
            if bad := [h.index for h in body.hotspots if h.index >= len(objs)]:
                raise HTTPException(422, f"no detected object at index {bad[0]}")
            kept = [{**objs[h.index], "label_vi": h.label_vi} for h in body.hotspots]  # coordinates stay as detected
            c.execute("UPDATE space SET hotspots = jsonb_set(hotspots, '{objects}', %s) WHERE id=%s", (Jsonb(kept), space_id))
            _log(c, space_id, user, "hotspots", {"kept": [h.index for h in body.hotspots], "of": len(objs)})
        if body.advance:
            _advance(c, space_id, row["review_status"], user, body.rights_confirmed)
        return c.execute(f"SELECT {FIELDS} FROM space WHERE id=%s", (space_id,)).fetchone()


class AdvanceMany(BaseModel):
    space_ids: list[int] = Field(min_length=1, max_length=500)
    rights_confirmed: bool = False


@app.post("/spaces/advance")
def advance_many(body: AdvanceMany, user=Depends(require(*STAFF))):
    """All or nothing: one space that cannot move rolls the whole selection back, and the error names it."""
    with _db() as c:
        rows = c.execute("SELECT id, review_status FROM space WHERE id = ANY(%s) ORDER BY id FOR UPDATE",
                         (body.space_ids,)).fetchall()
        if missing := set(body.space_ids) - {r["id"] for r in rows}:
            raise HTTPException(404, f"space {min(missing)} not found")
        moved = {r["id"]: _advance(c, r["id"], r["review_status"], user, body.rights_confirmed) for r in rows}
    return {"advanced": sorted(moved), "status": sorted(set(moved.values()))}


AI_DIMS = {"khong_gian", "phong_cach", "tong_mau", "vat_lieu"}  # mirrored from space columns by sync_ai_tags


class SetTags(BaseModel):
    space_ids: list[int] = Field(default_factory=list, max_length=500)
    project: Optional[str] = None  # first folder of relative_path: every space of that project
    dimension: str
    values: list[str] = Field(default_factory=list, max_length=20)


@app.put("/spaces/tags")
def set_tags(body: SetTags, user=Depends(require(*STAFF))):
    """Human tags (loai_cong_trinh, muc_dau_tu, ...): replaces that dimension's human values on the chosen spaces."""
    if body.dimension in AI_DIMS:
        raise HTTPException(422, f"{body.dimension} follows the AI labels; edit space_type / design_style / materials instead")
    with _db() as c:
        dim = c.execute("SELECT id, cho_phep_nhieu_gia_tri FROM chieu_phan_loai WHERE ma_dinh_danh=%s",
                        (body.dimension,)).fetchone()
        if not dim:
            raise HTTPException(422, f"unknown dimension {body.dimension}")
        vals = c.execute("SELECT id, ma_dinh_danh FROM gia_tri_phan_loai WHERE chieu_id=%s AND ma_dinh_danh = ANY(%s)",
                         (dim["id"], body.values)).fetchall()
        if len(vals) != len(set(body.values)):
            raise HTTPException(422, f"unknown value for {body.dimension}")
        if len(vals) > 1 and not dim["cho_phep_nhieu_gia_tri"]:
            raise HTTPException(422, f"{body.dimension} takes a single value")
        ids = [r["id"] for r in c.execute("SELECT id FROM space WHERE id = ANY(%s) OR split_part(relative_path, '/', 1) = %s",
                                          (body.space_ids, body.project)).fetchall()]
        if not ids:
            raise HTTPException(404, "no space matches")
        c.execute("DELETE FROM space_gia_tri sg USING gia_tri_phan_loai v WHERE sg.gia_tri_id = v.id AND v.chieu_id = %s "
                  "AND sg.space_id = ANY(%s)", (dim["id"], ids))  # incl. AI back-tags of a new dimension
        for v in vals:
            c.execute("INSERT INTO space_gia_tri (space_id, gia_tri_id, nguon_tao) SELECT unnest(%s::int[]), %s, 'nguoi' "
                      "ON CONFLICT DO NOTHING", (ids, v["id"]))
        for sid in ids:
            _log(c, sid, user, "tags", {body.dimension: [v["ma_dinh_danh"] for v in vals]})
    return {"spaces": len(ids), "values": [v["ma_dinh_danh"] for v in vals]}


class Event(BaseModel):
    loai: Literal["xem_khong_gian"]
    dong_y: bool                                     # the visitor's answer on the consent banner
    phien_id: Optional[str] = Field(default=None, pattern=r"^[A-Za-z0-9_-]{16,64}$")  # random browser token
    space_id: Optional[int] = None


@app.post("/events", status_code=204, dependencies=[Depends(limit("events", 120, 60))])
def track(body: Event):
    """Behaviour signal for taxonomy discovery (act-7, UC21). Only a consented session is stored, enriched with the
    viewed space's facet values; otherwise nothing per visitor is kept, just the day's anonymous count (NFR-09)."""
    with _db() as c:
        if not (body.dong_y and body.phien_id):
            c.execute("INSERT INTO su_kien_an_danh (ngay, loai, so_luong) VALUES (current_date, %s, 1) "
                      "ON CONFLICT (ngay, loai) DO UPDATE SET so_luong = su_kien_an_danh.so_luong + 1", (body.loai,))
            return
        c.execute("INSERT INTO phien_truy_cap (id, da_dong_y_thu_thap) VALUES (%s, true) ON CONFLICT DO NOTHING",
                  (body.phien_id,))
        c.execute("INSERT INTO su_kien (phien_id, loai, space_id, gia_tri) "
                  "SELECT %(p)s, %(l)s, s.id, COALESCE((SELECT array_agg(d.ma_dinh_danh || ':' || v.ma_dinh_danh) "
                  "  FROM space_gia_tri sg JOIN gia_tri_phan_loai v ON v.id = sg.gia_tri_id "
                  "  JOIN chieu_phan_loai d ON d.id = v.chieu_id WHERE sg.space_id = s.id), '{}') "
                  "FROM space s WHERE s.id = %(s)s AND s.review_status = 'published'",
                  {"p": body.phien_id, "l": body.loai, "s": body.space_id})


PHIEN = r"^[A-Za-z0-9_-]{16,64}$"  # the random browser session token of /events


class Chat(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    history: list[dict] = Field(default_factory=list, max_length=40)  # earlier turns, kept by the client
    contact: Optional[str] = Field(default=None, max_length=200)
    phien_id: Optional[str] = Field(default=None, pattern=PHIEN)
    gui_ho_so: bool = False                          # "gửi kèm những không gian tôi đã xem", ticked in the chat


@app.post("/chat", dependencies=[Depends(limit("chat", 20, 60))])
def chat(body: Chat, tasks: BackgroundTasks):
    """Public. Answers only from the knowledge base; otherwise says so and hands off to an architect."""
    out = respond(body.message, body.history, body.contact, body.phien_id, body.gui_ho_so)
    if out.get("lead_id"):
        tasks.add_task(notify.notify_new_lead, out["lead_id"])
    return out


# ── Lead intake (UC11, seq-5, dfd-2-4) ─────────────────────────────────────────
PHONE_SEPARATORS = re.compile(r"[\s.\-()]")
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_FILL_MS = 3000  # a person needs longer than this to type a name and a phone number


class LeadIn(BaseModel):
    ho_ten: str = Field(max_length=100)
    so_dien_thoai: str = Field(max_length=30)
    email: Optional[str] = Field(default=None, max_length=200)
    loi_nhan: Optional[str] = Field(default=None, max_length=1000)
    trang: Optional[str] = Field(default=None, max_length=200, pattern=r"^/")   # page the form was on
    du_an: Optional[str] = Field(default=None, max_length=100, pattern=r"^[a-z0-9-]+$")  # project slug
    space_id: Optional[int] = None
    phien_id: Optional[str] = Field(default=None, pattern=PHIEN)
    gui_ho_so: bool = False
    website: Optional[str] = None                    # honeypot: hidden from people, filled by naive bots
    t_ms: Optional[int] = None                       # ms between showing the form and sending it

    @field_validator("ho_ten")
    @classmethod
    def _name(cls, v):
        if not v.strip():
            raise ValueError("ho_ten_trong")
        return v.strip()

    @field_validator("so_dien_thoai")
    @classmethod
    def _phone(cls, v):  # Vietnamese mobile/landline: 0 or +84 then 9 digits; spaces, dots, dashes ignored
        v = PHONE_SEPARATORS.sub("", v)
        v = "0" + v[3:] if v.startswith("+84") else v
        if not re.fullmatch(r"0\d{9}", v):
            raise ValueError("so_dien_thoai_sai")
        return v

    @field_validator("email")
    @classmethod
    def _email(cls, v):
        v = (v or "").strip()
        if v and not EMAIL.match(v):
            raise ValueError("email_sai")
        return v or None

    @field_validator("loi_nhan")
    @classmethod
    def _message(cls, v):
        return (v or "").strip() or None


@app.post("/leads", status_code=201, dependencies=[Depends(limit("leads", 5, 600))])
def post_lead(body: LeadIn, tasks: BackgroundTasks):
    """Public contact form. Bots (honeypot filled, or sent faster than a person can type) get the same answer and
    nothing is stored or sent, so they learn nothing."""
    ok = {"message": "Đã nhận yêu cầu, tư vấn viên sẽ gọi lại số " + body.so_dien_thoai}
    if body.website or (body.t_ms is not None and body.t_ms < MIN_FILL_MS):
        return {"lead_id": None, **ok}
    context = {k: v for k, v in {"trang": body.trang, "du_an": body.du_an, "space_id": body.space_id}.items() if v}
    lead_id = leads.create_lead("form", ho_ten=body.ho_ten, so_dien_thoai=body.so_dien_thoai, email=body.email,
                                loi_nhan=body.loi_nhan, ngu_canh=context or None, phien_id=body.phien_id,
                                gui_ho_so=body.gui_ho_so)
    tasks.add_task(notify.notify_new_lead, lead_id)
    tasks.add_task(notify.confirm_to_visitor, lead_id)
    return {"lead_id": lead_id, **ok}


@app.get("/leads")
def list_leads(status: Optional[str] = None, nguon: Optional[Literal[leads.SOURCES]] = None, limit: int = 50,
               offset: int = 0, user=Depends(require("sales", *APPROVERS))):
    """Leads from every source (form, chat, later brief / estimate), newest first."""
    with _db() as c:
        rows = c.execute(
            "SELECT l.id, nguon, intent, ho_ten, so_dien_thoai, email, loi_nhan, ngu_canh, ho_so_hanh_vi, request, "
            "conversation, contact, status, l.created_at, bo_suu_tap_id, b.ma_chia_se "
            "FROM lead l LEFT JOIN bo_suu_tap b ON b.id = l.bo_suu_tap_id "
            "WHERE (%(s)s::text IS NULL OR status=%(s)s) AND (%(n)s::text IS NULL OR nguon=%(n)s) "
            "ORDER BY id DESC LIMIT %(l)s OFFSET %(o)s",
            {"s": status, "n": nguon, "l": limit, "o": offset}).fetchall()
        for r in rows:
            r["tom_tat"] = leads.profile_summary(r["ho_so_hanh_vi"])
            r["bo_suu_tap"] = bo_suu_tap.sent_items(c, r["bo_suu_tap_id"]) if r["bo_suu_tap_id"] else None
    return rows


# ── Saved collection (UC07, seq-13) and design brief (UC08, seq-7) ─────────────
class CollectionItem(BaseModel):
    space_id: int
    ghi_chu: Optional[str] = Field(default=None, max_length=bo_suu_tap.MAX_NOTE)


class Note(BaseModel):
    ghi_chu: Optional[str] = Field(default=None, max_length=bo_suu_tap.MAX_NOTE)


class Merge(BaseModel):
    items: list[CollectionItem] = Field(default_factory=list, max_length=bo_suu_tap.MAX_ITEMS)


SIGNED_IN = [Depends(limit("collections", 120, 60))]


@app.get("/collections/me", dependencies=SIGNED_IN)
def my_collection(user=Depends(require(*ROLES))):
    with _db() as c:
        return bo_suu_tap.items(c, bo_suu_tap.working_id(c, user["id"]))


@app.put("/collections/me/items/{space_id}", dependencies=SIGNED_IN)
def save_to_collection(space_id: int, body: Note = Note(), user=Depends(require(*ROLES))):
    with _db() as c:
        try:
            if not bo_suu_tap.put_item(c, user["id"], space_id, body.ghi_chu):
                raise HTTPException(404, "space not published")
        except bo_suu_tap.Full:
            raise HTTPException(409, "bo_suu_tap_day")
        return bo_suu_tap.items(c, bo_suu_tap.working_id(c, user["id"]))


@app.delete("/collections/me/items/{space_id}", status_code=204, dependencies=SIGNED_IN)
def remove_from_collection(space_id: int, user=Depends(require(*ROLES))):
    with _db() as c:
        bo_suu_tap.remove_item(c, user["id"], space_id)


@app.post("/collections/me/merge", dependencies=SIGNED_IN)
def merge_collection(body: Merge, user=Depends(require(*ROLES))):
    """The browser collection joins the account at sign-in (seq-13 #13)."""
    with _db() as c:
        return bo_suu_tap.merge(c, user["id"], [i.model_dump() for i in body.items])


@app.get("/collections/shared/{code}")
def shared_collection(code: str = PathParam(pattern=r"^[A-Za-z0-9_-]{8,64}$")):
    """Read-only view of a sent brief: photos, notes, summary; never the sender's name or contact."""
    with _db() as c:
        out = bo_suu_tap.shared(c, code)
    if not out:
        raise HTTPException(404, "Không tìm thấy bộ sưu tập")
    return out


HOUSE_TYPES = ("can_ho", "nha_pho", "biet_thu", "van_phong", "thuong_mai", "khac")
BUDGETS = ("duoi_300tr", "300tr_700tr", "700tr_1500tr", "tren_1500tr", "chua_ro")


class BriefIn(LeadIn):
    loai_nha: Literal[HOUSE_TYPES]
    dien_tich_m2: Optional[float] = Field(default=None, ge=10, le=5000)
    ngan_sach: Literal[BUDGETS] = "chua_ro"
    items: list[CollectionItem] = Field(min_length=1, max_length=bo_suu_tap.MAX_ITEMS)


@app.post("/briefs", status_code=201, dependencies=[Depends(limit("leads", 5, 600))])  # one bucket with /leads
def post_brief(body: BriefIn, tasks: BackgroundTasks, user=Depends(optional_user)):
    """Send a collection to an architect. Signed in or not; the photos are copied so the brief never changes."""
    ok = {"message": "Đã gửi bộ sưu tập cho kiến trúc sư, tư vấn viên sẽ gọi lại số " + body.so_dien_thoai}
    if body.website or (body.t_ms is not None and body.t_ms < MIN_FILL_MS):
        return {"lead_id": None, "ma_chia_se": None, **ok}
    with _db() as c:
        ids = bo_suu_tap.published(c, [i.space_id for i in body.items])
        if not ids:
            raise HTTPException(422, [{"loc": ["body", "items"], "msg": "bo_suu_tap_trong", "type": "value_error"}])
        notes = {i.space_id: i.ghi_chu for i in body.items}
        chosen = [{"space_id": i, "ghi_chu": notes[i]} for i in ids]
        summary = leads.brief_summary(ids, c)
        coll_id, code = bo_suu_tap.send_copy(c, user["id"] if user else None, chosen, summary)
        context = {k: v for k, v in {"trang": body.trang, "du_an": body.du_an, "space_id": body.space_id}.items() if v}
        lead_id = leads.create_lead(
            "brief", ho_ten=body.ho_ten, so_dien_thoai=body.so_dien_thoai, email=body.email, loi_nhan=body.loi_nhan,
            ngu_canh=context or None, phien_id=body.phien_id, gui_ho_so=body.gui_ho_so, bo_suu_tap_id=coll_id,
            request={"loai_nha": body.loai_nha, "dien_tich_m2": body.dien_tich_m2, "ngan_sach": body.ngan_sach,
                     "tom_tat": summary}, conn=c)
    tasks.add_task(notify.notify_new_lead, lead_id)
    tasks.add_task(notify.confirm_to_visitor, lead_id)
    return {"lead_id": lead_id, "ma_chia_se": code, **ok}


# ── Cost estimate (UC10, seq-9, act-6) and its price table D8 ─────────────────────
class EstimateIn(BaseModel):
    loai_nha: Literal[tuple(estimate.HOUSE_VI)]
    dien_tich_m2: float = Field(ge=10, le=5000)
    so_phong_ngu: int = Field(default=2, ge=0, le=10)
    goi: Literal[tuple(estimate.PACKAGE_VI)] = "tieu_chuan"


@app.post("/estimates", dependencies=[Depends(limit("estimates", 30, 60))])
def post_estimate(body: EstimateIn):
    """Public. Arithmetic on the price table; nothing is stored."""
    with _db() as c:
        return estimate.estimate(c, body.loai_nha, body.dien_tich_m2, body.so_phong_ngu, body.goi)


class EstimateLeadIn(LeadIn, EstimateIn):
    email: str = Field(max_length=200)  # required here: the details go by email

    @field_validator("email")
    @classmethod
    def _email_required(cls, v):
        v = (v or "").strip()
        if not v:
            raise ValueError("email_trong")
        if not EMAIL.match(v):
            raise ValueError("email_sai")
        return v


@app.post("/estimates/send", status_code=201, dependencies=[Depends(limit("leads", 5, 600))])  # one bucket with /leads
def send_estimate(body: EstimateLeadIn, tasks: BackgroundTasks):
    """'Nhận bản chi tiết qua email': the server recomputes (a client total is never trusted) and stores a lead."""
    ok = {"message": "Đã gửi bản ước tính chi tiết tới " + body.email}
    if body.website or (body.t_ms is not None and body.t_ms < MIN_FILL_MS):
        return {"lead_id": None, **ok}
    dau_vao = {"loai_nha": body.loai_nha, "dien_tich_m2": body.dien_tich_m2, "so_phong_ngu": body.so_phong_ngu,
               "goi": body.goi}
    with _db() as c:
        ket_qua = estimate.estimate(c, body.loai_nha, body.dien_tich_m2, body.so_phong_ngu, body.goi)
        context = {k: v for k, v in {"trang": body.trang, "du_an": body.du_an, "space_id": body.space_id}.items() if v}
        lead_id = leads.create_lead("estimate", ho_ten=body.ho_ten, so_dien_thoai=body.so_dien_thoai, email=body.email,
                                    loi_nhan=body.loi_nhan, ngu_canh=context or None, phien_id=body.phien_id,
                                    gui_ho_so=body.gui_ho_so, request={"dau_vao": dau_vao, "ket_qua": ket_qua}, conn=c)
    tasks.add_task(notify.notify_new_lead, lead_id)
    tasks.add_task(notify.confirm_to_visitor, lead_id)
    return {"lead_id": lead_id, **ok}


class PriceIn(BaseModel):
    gia_min: int = Field(ge=0, le=1_000_000_000)
    gia_max: int = Field(ge=0, le=1_000_000_000)
    ghi_chu: Optional[str] = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def _ordered(self):
        if self.gia_min > self.gia_max:
            raise ValueError("gia_min_lon_hon_gia_max")
        return self


@app.get("/prices")
def list_prices(user=Depends(require(*APPROVERS))):
    """The whole price table D8 for the staff page; nguon 'mau' = sample price, 'd3' = set by staff."""
    with _db() as c:
        return c.execute("SELECT g.id, loai_nha, hang_muc, goi, gia_min, gia_max, nguon, ghi_chu, cap_nhat_luc, "
                         "u.email AS cap_nhat_boi FROM don_gia g LEFT JOIN app_user u ON u.id = g.cap_nhat_boi "
                         "ORDER BY loai_nha, array_position(ARRAY['thiet_ke','phan_tho','hoan_thien','noi_that'], hang_muc), "
                         "array_position(ARRAY['co_ban','tieu_chuan','cao_cap'], goi)").fetchall()


@app.put("/prices/{price_id}")
def save_price(price_id: int, body: PriceIn, user=Depends(require(*APPROVERS))):
    """act-6: staff change prices without touching code. A saved row is no longer a sample."""
    with _db() as c:
        row = c.execute("UPDATE don_gia SET gia_min=%s, gia_max=%s, ghi_chu=%s, nguon='d3', cap_nhat_boi=%s, "
                        "cap_nhat_luc=now() WHERE id=%s RETURNING id, loai_nha, hang_muc, goi, gia_min, gia_max, nguon, "
                        "ghi_chu, cap_nhat_luc", (body.gia_min, body.gia_max, body.ghi_chu, user["id"], price_id)).fetchone()
    if not row:
        raise HTTPException(404, "no such price")
    return row


# ── Taxonomy admin (UC15) — data-driven dimensions/values; seq-15 flow ────────
@app.get("/taxonomy")
def taxonomy_list():
    """Dimensions with their values. Public: the portfolio filters read this too."""
    with _db() as c:
        dims = c.execute("SELECT id, ma_dinh_danh, ten, bat_buoc, cho_phep_nhieu_gia_tri, hien_thi_cho_khach, thu_tu "
                         "FROM chieu_phan_loai ORDER BY thu_tu, id").fetchall()
        vals = c.execute("SELECT id, chieu_id, ma_dinh_danh, ten, tu_dong_nghia "
                         "FROM gia_tri_phan_loai ORDER BY id").fetchall()
    by_dim: dict = {}
    for v in vals:
        by_dim.setdefault(v["chieu_id"], []).append(v)
    for d in dims:
        d["values"] = by_dim.get(d["id"], [])
    return dims


class NewValue(BaseModel):
    ma_dinh_danh: str = Field(min_length=1, max_length=64)
    ten: str = Field(min_length=1, max_length=120)
    tu_dong_nghia: list[str] = Field(default_factory=list)


@app.post("/taxonomy/{dim_id}/values", status_code=201)
def add_value(dim_id: int, body: NewValue, user=Depends(require(*APPROVERS))):
    with _db() as c:
        if not c.execute("SELECT 1 FROM chieu_phan_loai WHERE id=%s", (dim_id,)).fetchone():
            raise HTTPException(404, "dimension not found")
        try:
            row = c.execute(
                "INSERT INTO gia_tri_phan_loai (chieu_id, ma_dinh_danh, ten, tu_dong_nghia) "
                "VALUES (%s,%s,%s,%s) RETURNING id, chieu_id, ma_dinh_danh, ten, tu_dong_nghia",
                (dim_id, body.ma_dinh_danh, body.ten, Jsonb(body.tu_dong_nghia))).fetchone()
        except UniqueViolation:
            raise HTTPException(409, "value already exists in this dimension")
    taxonomy.reload()
    return row


class RenameValue(BaseModel):
    ten: str = Field(min_length=1, max_length=120)


@app.patch("/taxonomy/values/{value_id}")
def rename_value(value_id: int, body: RenameValue, user=Depends(require(*APPROVERS))):
    """Rename keeps ma_dinh_danh, so facet URLs stay valid (seq-15 b13)."""
    with _db() as c:
        row = c.execute("UPDATE gia_tri_phan_loai SET ten=%s WHERE id=%s RETURNING id, ma_dinh_danh, ten",
                        (body.ten, value_id)).fetchone()
    if not row:
        raise HTTPException(404, "value not found")
    taxonomy.reload()
    return row


class MergeValue(BaseModel):
    target_id: int


@app.post("/taxonomy/values/{value_id}/merge")
def merge_value(value_id: int, body: MergeValue, user=Depends(require(*APPROVERS))):
    """Move every space tag from the source value to the target, then delete the source (seq-15 b19)."""
    if value_id == body.target_id:
        raise HTTPException(422, "cannot merge a value into itself")
    with _db() as c:
        if len(c.execute("SELECT id FROM gia_tri_phan_loai WHERE id IN (%s,%s)",
                         (value_id, body.target_id)).fetchall()) != 2:
            raise HTTPException(404, "value not found")
        affected = c.execute("SELECT COUNT(*) AS n FROM space_gia_tri WHERE gia_tri_id=%s", (value_id,)).fetchone()["n"]
        c.execute("UPDATE space_gia_tri SET gia_tri_id=%s WHERE gia_tri_id=%s "
                  "AND space_id NOT IN (SELECT space_id FROM space_gia_tri WHERE gia_tri_id=%s)",
                  (body.target_id, value_id, body.target_id))
        c.execute("DELETE FROM space_gia_tri WHERE gia_tri_id=%s", (value_id,))  # any duplicates left behind
        c.execute("DELETE FROM gia_tri_phan_loai WHERE id=%s", (value_id,))
    taxonomy.reload()  # ponytail: vector-index label refresh (seq-15 b20-22) is a future queue job
    return {"merged_into": body.target_id, "affected": affected}


# ── Taxonomy discovery review (seq-15, change discover-taxonomy-dimensions 3.2-3.3) ────────────
@app.get("/taxonomy/candidates")
def list_candidates(user=Depends(require(*APPROVERS))):
    """Proposals promoted for review, with example spaces; plus how many still wait for more evidence."""
    with _db() as c:
        rows = c.execute("SELECT id, ten_de_xuat, bang_chung, created_at, updated_at FROM ung_vien_phan_loai "
                         "WHERE loai = 'chieu' AND trang_thai = 'cho_duyet' ORDER BY (bang_chung->>'score')::float DESC NULLS LAST").fetchall()
        for r in rows:
            ids = (r["bang_chung"] or {}).get("vi_du_space_ids", [])[:8]
            r["vi_du"] = c.execute("SELECT id, relative_path, space_type, design_style FROM space WHERE id = ANY(%s) ORDER BY id",
                                   (ids,)).fetchall()
        waiting = c.execute("SELECT count(*) AS n FROM ung_vien_phan_loai WHERE trang_thai = 'cho_bang_chung'").fetchone()["n"]
    return {"candidates": rows, "cho_bang_chung": waiting}


class AcceptCandidate(BaseModel):
    ten: str = Field(min_length=2, max_length=80)
    gia_tri: list[str] = Field(min_length=2, max_length=8)


def _pending(c, cid):
    row = c.execute("SELECT id, trang_thai, bang_chung FROM ung_vien_phan_loai WHERE id=%s AND loai='chieu'", (cid,)).fetchone()
    if not row:
        raise HTTPException(404, "candidate not found")
    if row["trang_thai"] != "cho_duyet":
        raise HTTPException(409, f"candidate is {row['trang_thai']}, only cho_duyet can be decided")
    return row


@app.post("/taxonomy/candidates/{cid}/accept", status_code=201)
def accept_candidate(cid: int, body: AcceptCandidate, user=Depends(require(*APPROVERS))):
    """The human gate: only here does a proposed dimension become live. Gemini back-tags the whole library first,
    then dimension, values, tags and the decision are written in one transaction (no half-made dimension)."""
    ma = project_folder(body.ten)
    values = {project_folder(v): v.strip() for v in body.gia_tri if v.strip()}
    if not ma or len(values) != len(body.gia_tri) or "" in values:
        raise HTTPException(422, "name and every value need letters or digits, and values must differ")
    with _db() as c:
        cand = _pending(c, cid)
        if c.execute("SELECT 1 FROM chieu_phan_loai WHERE ma_dinh_danh=%s", (ma,)).fetchone():
            raise HTTPException(409, f"dimension {ma} already exists")
    if not vertex.available():
        raise HTTPException(503, "Chưa cấu hình Vertex nên không gắn nhãn thư viện được.")
    tags = discovery.backtag(body.ten, (cand["bang_chung"] or {}).get("mo_ta", ""), values)  # slow: one call per 50 spaces
    with _db() as c:
        _pending(c, cid)  # still undecided after the Gemini calls
        dim = c.execute("INSERT INTO chieu_phan_loai (ma_dinh_danh, ten, thu_tu) "
                        "VALUES (%s, %s, (SELECT COALESCE(max(thu_tu), 0) + 1 FROM chieu_phan_loai)) RETURNING id",
                        (ma, body.ten.strip())).fetchone()["id"]
        val_id = {m: c.execute("INSERT INTO gia_tri_phan_loai (chieu_id, ma_dinh_danh, ten) VALUES (%s,%s,%s) RETURNING id",
                               (dim, m, t)).fetchone()["id"] for m, t in values.items()}
        for sid, (m, conf) in tags.items():
            c.execute("INSERT INTO space_gia_tri (space_id, gia_tri_id, do_tin_cay, nguon_tao) VALUES (%s,%s,%s,'ai_bo_sung') "
                      "ON CONFLICT DO NOTHING", (sid, val_id[m], conf))
        all_ids = [r["id"] for r in c.execute("SELECT id FROM space ORDER BY id").fetchall()]
        review = [i for i in all_ids if i not in tags or tags[i][1] < discovery.LOW_CONFIDENCE]
        c.execute("UPDATE ung_vien_phan_loai SET trang_thai='chap_nhan', ten_de_xuat=%s, updated_at=now(), "
                  "bang_chung = bang_chung || %s WHERE id=%s",
                  (body.ten.strip(), Jsonb({"chieu_id": dim, "nguoi_duyet": user["id"], "gia_tri_chot": list(values.values()),
                                            "gan_nhan": len(tags), "can_xem_lai": review}), cid))
    taxonomy.reload()
    return {"chieu": ma, "gia_tri": list(values), "gan_nhan": len(tags), "can_xem_lai": review}


@app.post("/taxonomy/candidates/{cid}/reject")
def reject_candidate(cid: int, user=Depends(require(*APPROVERS))):
    with _db() as c:
        _pending(c, cid)
        c.execute("UPDATE ung_vien_phan_loai SET trang_thai='tu_choi', updated_at=now(), bang_chung = "
                  "COALESCE(bang_chung, '{}') || %s WHERE id=%s", (Jsonb({"nguoi_duyet": user["id"]}), cid))
    return {"id": cid, "trang_thai": "tu_choi"}
