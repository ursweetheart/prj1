"""D3 Studio AI API.  Run: uvicorn api:app --reload"""

import os
import re
import shutil
from functools import lru_cache
from pathlib import Path
from typing import Optional

import psycopg
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from psycopg.types.json import Jsonb
from starlette.middleware.sessions import SessionMiddleware
from psycopg.rows import dict_row
from psycopg.errors import UniqueViolation
from pydantic import BaseModel, Field

import auth
from pipeline import taxonomy
from pipeline.assistant import _fold, respond, with_services
from auth import APPROVERS, STAFF, optional_user, require
from pipeline.schemas import SpaceClassificationResult
from pipeline.search import by_text, similar_to
from pipeline.store import DSN, save_records
from ratelimit import limit

IMG_DIR = Path("image_d3")
UPLOAD_DIR = IMG_DIR / "uploads"
FIELDS = "id, relative_path, space_type, design_style, style_confidence, materials, caption, alt_text, review_status"
# taxonomy values of each space as {dimension: [value, ...]}; the portfolio filters on these
TAGS = ("(SELECT COALESCE(jsonb_object_agg(dim, vals), '{}') FROM (SELECT d.ma_dinh_danh AS dim, jsonb_agg(v.ma_dinh_danh) AS vals "
        "FROM space_gia_tri sg JOIN gia_tri_phan_loai v ON v.id = sg.gia_tri_id JOIN chieu_phan_loai d ON d.id = v.chieu_id "
        "WHERE sg.space_id = space.id GROUP BY d.ma_dinh_danh) t) AS tags")
# QT-01 order; an architect confirms AI tags before anything is published
NEXT = {"draft": "in_review", "in_review": "approved", "approved": "published"}
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


def _is_staff(user) -> bool:  # staff see every review state; everyone else only published spaces
    return bool(user) and user["role"] in STAFF


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
                review_status: Optional[str] = None, limit: int = 50, offset: int = 0, user=Depends(optional_user)):
    if not _is_staff(user):
        review_status = "published" if review_status in (None, "published") else "none"  # no such status: matches nothing
    with _db() as c:
        return c.execute(
            f"SELECT {FIELDS}, palette->>'brightness' AS brightness, palette->>'temperature' AS temperature, {TAGS} "
            "FROM space WHERE (%(t)s::text IS NULL OR space_type=%(t)s) "
            "AND (%(s)s::text IS NULL OR design_style=%(s)s) AND (%(r)s::text IS NULL OR review_status=%(r)s) "
            "ORDER BY id LIMIT %(l)s OFFSET %(o)s",
            {"t": space_type, "s": design_style, "r": review_status, "l": min(limit, 200), "o": offset}).fetchall()


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


@app.get("/search")
def search(q: str, space_type: Optional[str] = None, k: int = 6, user=Depends(optional_user)):
    if space_type and space_type not in SPACE_TYPES:
        raise HTTPException(422, f"space_type must be one of {SPACE_TYPES}")
    return [_hit(r) for r in by_text(q, space_type, min(k, 24), published_only=not _is_staff(user))]


def project_folder(name: str) -> str:
    """'Biệt thự Thảo Điền' -> 'biet_thu_thao_dien': the folder doubles as the project name, keep it URL- and path-safe."""
    return re.sub(r"[^a-z0-9]+", "_", _fold(name)).strip("_")[:60]


@app.post("/spaces/ingest", status_code=201)
def ingest(file: UploadFile = File(...), project: str = Form(""), user=Depends(require(*STAFF))):
    if Path(file.filename or "").suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
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


class Review(BaseModel):
    space_type: Optional[str] = None
    design_style: Optional[str] = None
    advance: bool = False  # move to the next review state


@app.patch("/spaces/{space_id}")
def review(space_id: int, body: Review, user=Depends(require(*STAFF))):
    if body.space_type and body.space_type not in SPACE_TYPES:
        raise HTTPException(422, f"space_type must be one of {SPACE_TYPES}")
    if body.design_style and body.design_style not in STYLES:
        raise HTTPException(422, f"design_style must be one of {STYLES}")
    with _db() as c:
        row = c.execute("SELECT review_status, space_type, design_style FROM space WHERE id=%s FOR UPDATE", (space_id,)).fetchone()
        if not row:
            raise HTTPException(404, "space not found")
        status = row["review_status"]
        if body.advance:
            if status not in NEXT:
                raise HTTPException(409, f"'{status}' is the final state")
            if status != "draft" and user["role"] not in APPROVERS:  # only the lead architect approves / publishes
                raise HTTPException(403, "approval and publishing require lead_architect")
            status = NEXT[status]
        new = c.execute(
            f"UPDATE space SET space_type=COALESCE(%s,space_type), design_style=COALESCE(%s,design_style), "
            f"review_status=%s WHERE id=%s RETURNING {FIELDS}",
            (body.space_type, body.design_style, status, space_id)).fetchone()
        if body.space_type or body.design_style:
            _log(c, space_id, user, "edit", {"from": {"space_type": row["space_type"], "design_style": row["design_style"]},
                                              "to": {"space_type": new["space_type"], "design_style": new["design_style"]}})
        if body.advance:
            _log(c, space_id, user, "advance", {"from": row["review_status"], "to": status})
        return new


class Chat(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    history: list[dict] = Field(default_factory=list, max_length=40)  # earlier turns, kept by the client
    contact: Optional[str] = Field(default=None, max_length=200)


@app.post("/chat", dependencies=[Depends(limit("chat", 20, 60))])
def chat(body: Chat):
    """Public. Answers only from the knowledge base; otherwise says so and hands off to an architect."""
    return respond(body.message, body.history, body.contact)


@app.get("/leads")
def list_leads(status: Optional[str] = None, limit: int = 50, offset: int = 0, user=Depends(require("sales", *APPROVERS))):
    """Leads created by the chat (price / appointment / handoff), newest first."""
    with _db() as c:
        return c.execute(
            "SELECT id, intent, request, conversation, contact, status, created_at FROM lead "
            "WHERE (%(s)s::text IS NULL OR status=%(s)s) ORDER BY id DESC LIMIT %(l)s OFFSET %(o)s",
            {"s": status, "l": limit, "o": offset}).fetchall()


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
