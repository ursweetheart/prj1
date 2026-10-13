"""D3 Studio AI API.  Run: uvicorn api:app --reload"""

import shutil
from functools import lru_cache
from pathlib import Path
from typing import Optional

import psycopg
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from psycopg.types.json import Jsonb
from starlette.middleware.sessions import SessionMiddleware
from psycopg.rows import dict_row
from pydantic import BaseModel, Field

import auth
from pipeline.assistant import respond, with_services
from auth import APPROVERS, STAFF, optional_user, require
from pipeline.schemas import SpaceClassificationResult
from pipeline.search import by_text, similar_to
from pipeline.store import DSN, save_records
from ratelimit import limit

IMG_DIR = Path("image_d3")
UPLOAD_DIR = IMG_DIR / "uploads"
FIELDS = "id, relative_path, space_type, design_style, style_confidence, materials, caption, alt_text, review_status"
# QT-01 order; an architect confirms AI tags before anything is published
NEXT = {"draft": "in_review", "in_review": "approved", "approved": "published"}
SPACE_TYPES = SpaceClassificationResult.model_fields["space_type"].annotation.__args__
STYLES = SpaceClassificationResult.model_fields["design_style"].annotation.__args__

app = FastAPI(title="D3 Studio AI")
app.add_middleware(SessionMiddleware, secret_key=auth.SECRET)  # only holds the OAuth state during Google sign-in
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
            f"SELECT {FIELDS} FROM space WHERE (%(t)s::text IS NULL OR space_type=%(t)s) "
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


@app.post("/spaces/ingest", status_code=201)
def ingest(file: UploadFile = File(...), user=Depends(require(*STAFF))):
    if Path(file.filename or "").suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(415, "image only (jpg/png/webp)")
    UPLOAD_DIR.mkdir(exist_ok=True)
    dest = UPLOAD_DIR / Path(file.filename).name  # .name strips any path component
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
