"""D3 Studio AI API.  Run: uvicorn api:app --reload"""

import shutil
from functools import lru_cache
from pathlib import Path
from typing import Optional

import psycopg
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from psycopg.rows import dict_row
from pydantic import BaseModel

from pipeline.schemas import SpaceClassificationResult
from pipeline.search import by_text, similar_to
from pipeline.store import DSN, save_records

IMG_DIR = Path("image_d3")
UPLOAD_DIR = IMG_DIR / "uploads"
FIELDS = "id, relative_path, space_type, design_style, style_confidence, materials, caption, alt_text, review_status"
# QT-01 order; an architect confirms AI tags before anything is published
NEXT = {"draft": "in_review", "in_review": "approved", "approved": "published"}
SPACE_TYPES = SpaceClassificationResult.model_fields["space_type"].annotation.__args__
STYLES = SpaceClassificationResult.model_fields["design_style"].annotation.__args__

app = FastAPI(title="D3 Studio AI")
IMG_DIR.mkdir(exist_ok=True)
app.mount("/images", StaticFiles(directory=IMG_DIR), name="images")


def _db():
    return psycopg.connect(DSN, row_factory=dict_row)


def _hit(r):  # tuple from pipeline.search -> dict
    return {"relative_path": r[0], "space_type": r[1], "design_style": r[2], "score": round(float(r[3]), 4), "id": r[4]}


@lru_cache(maxsize=1)
def _processor():  # loads YOLO + SigLIP2 on first ingest only
    from pipeline.processor import SpaceImageProcessor
    return SpaceImageProcessor()


@app.get("/spaces")
def list_spaces(space_type: Optional[str] = None, design_style: Optional[str] = None,
                review_status: Optional[str] = None, limit: int = 50, offset: int = 0):
    with _db() as c:
        return c.execute(
            f"SELECT {FIELDS} FROM space WHERE (%(t)s::text IS NULL OR space_type=%(t)s) "
            "AND (%(s)s::text IS NULL OR design_style=%(s)s) AND (%(r)s::text IS NULL OR review_status=%(r)s) "
            "ORDER BY id LIMIT %(l)s OFFSET %(o)s",
            {"t": space_type, "s": design_style, "r": review_status, "l": min(limit, 200), "o": offset}).fetchall()


@app.get("/spaces/{space_id}")
def get_space(space_id: int):
    with _db() as c:
        row = c.execute(f"SELECT {FIELDS}, palette, hotspots FROM space WHERE id=%s", (space_id,)).fetchone()
    if not row:
        raise HTTPException(404, "space not found")
    return row


@app.get("/spaces/{space_id}/similar")
def similar(space_id: int, k: int = 6):
    with _db() as c:
        row = c.execute("SELECT relative_path FROM space WHERE id=%s", (space_id,)).fetchone()
    if not row:
        raise HTTPException(404, "space not found")
    return [_hit(r) for r in similar_to(row["relative_path"], min(k, 24))]


@app.get("/search")
def search(q: str, space_type: Optional[str] = None, k: int = 6):
    if space_type and space_type not in SPACE_TYPES:
        raise HTTPException(422, f"space_type must be one of {SPACE_TYPES}")
    return [_hit(r) for r in by_text(q, space_type, min(k, 24))]


@app.post("/spaces/ingest", status_code=201)
def ingest(file: UploadFile = File(...)):
    if Path(file.filename or "").suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(415, "image only (jpg/png/webp)")
    UPLOAD_DIR.mkdir(exist_ok=True)
    dest = UPLOAD_DIR / Path(file.filename).name  # .name strips any path component
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    rec = _processor().process_image(dest, base_dir=IMG_DIR)  # sync on purpose: GPU is a single resource
    save_records([rec])
    with _db() as c:
        return c.execute(f"SELECT {FIELDS} FROM space WHERE relative_path=%s", (rec.relative_path,)).fetchone()


class Review(BaseModel):
    space_type: Optional[str] = None
    design_style: Optional[str] = None
    advance: bool = False  # move to the next review state


@app.patch("/spaces/{space_id}")
def review(space_id: int, body: Review):
    if body.space_type and body.space_type not in SPACE_TYPES:
        raise HTTPException(422, f"space_type must be one of {SPACE_TYPES}")
    if body.design_style and body.design_style not in STYLES:
        raise HTTPException(422, f"design_style must be one of {STYLES}")
    with _db() as c:
        row = c.execute("SELECT review_status FROM space WHERE id=%s FOR UPDATE", (space_id,)).fetchone()
        if not row:
            raise HTTPException(404, "space not found")
        status = row["review_status"]
        if body.advance:
            if status not in NEXT:
                raise HTTPException(409, f"'{status}' is the final state")
            status = NEXT[status]
        return c.execute(
            f"UPDATE space SET space_type=COALESCE(%s,space_type), design_style=COALESCE(%s,design_style), "
            f"review_status=%s WHERE id=%s RETURNING {FIELDS}",
            (body.space_type, body.design_style, status, space_id)).fetchone()
