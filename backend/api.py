"""D3 Studio AI API.  Run: uvicorn api:app --reload"""

import asyncio
from collections import Counter
import io
import mimetypes
import os
import random
import re
import shutil
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal, Optional

import psycopg
from pgvector.psycopg import register_vector
from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, Query, Request, Response, UploadFile
from fastapi import Path as PathParam
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from PIL import Image
from psycopg.types.json import Jsonb
from starlette.middleware.sessions import SessionMiddleware
from psycopg.rows import dict_row
from psycopg.errors import UniqueViolation
from pydantic import BaseModel, Field, StringConstraints, field_validator, model_validator

import auth
from pipeline import (behaviour, explain, home_suggestions, project_filter, image_sizes, intake, space_knowledge, label_feedback, rollup, bo_suu_tap, conversations, discovery, estimate, items, knowledge, leads, notify, project_stats, quiz, taxonomy, taxonomy_admin,
                      topic_guard, trends, value_suggest, vertex, weekly_report)
from pipeline.assistant import KB_KINDS, respond, with_services
from auth import APPROVERS, ROLES, STAFF, optional_user, require
from pipeline.search import MIN_IMAGE_SCORE, by_image, by_text, embed_photo, similar_to
from pipeline.store import DSN, save_records
from ratelimit import check as rate_check, limit

IMG_DIR = Path("image_d3")
UPLOAD_DIR = IMG_DIR / "uploads"
IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".webp"}
MAX_UPLOAD = 8 * 1024 * 1024  # photo search; nginx allows 50 MB, so this is the limit users hit
AI_FIELDS = "space_type_ai, design_style_ai, space_type_confidence"  # seq-1 b17: the AI's proposal with its confidence
FIELDS = ("id, relative_path, space_type, design_style, style_confidence, materials, caption, alt_text, review_status, "
          "ngay_xuat_ban, kich_thuoc, chieu_rong, chieu_cao")
# taxonomy values of each space as {dimension: [value, ...]}; the portfolio filters on these
TAGS = ("(SELECT COALESCE(jsonb_object_agg(dim, vals), '{}') FROM (SELECT d.ma_dinh_danh AS dim, jsonb_agg(v.ma_dinh_danh) AS vals "
        "FROM space_gia_tri sg JOIN gia_tri_phan_loai v ON v.id = sg.gia_tri_id JOIN chieu_phan_loai d ON d.id = v.chieu_id "
        "WHERE sg.space_id = space.id GROUP BY d.ma_dinh_danh) t) AS tags")
# review-tag-autocomplete: the new values a space waits on, {dimension: word}, while an approver hasn't decided
PENDING_VALUE = ("(SELECT COALESCE(jsonb_object_agg(u.bang_chung->>'chieu', u.ten_de_xuat), '{}') FROM ung_vien_phan_loai u "
                 "WHERE u.loai = 'gia_tri' AND u.trang_thai = 'cho_duyet' AND u.bang_chung->'space_ids' @> to_jsonb(space.id)) "
                 "AS cho_duyet_gia_tri")
# QT-01 order; an architect confirms AI tags before anything is published
# QT-01 / seq-6 (publishing-workflow): draft -> "Chờ biên tập" (content edits, SEO) -> "Chờ duyệt" -> ... -> published
NEXT = {"draft": "editing", "editing": "in_review", "in_review": "approved", "approved": "cleared", "cleared": "published"}
ADVANCE_ROLES = {"draft": STAFF, "editing": {"content", *APPROVERS}}  # every later step: APPROVERS only


def _check_value(dim: str, field: str, code: Optional[str]):
    """Room type / style must be a value stored for that dimension now (staff add them at /quan-tri/phan-loai)."""
    if code and code not in (allowed := taxonomy.values(dim)):
        raise HTTPException(422, f"{field} must be one of {allowed}")


# ── Weekly report scheduler (UC23; seq-18 b1): checks 30 s after start, then every 10 minutes ─────────────
WEEKLY_FIRST, WEEKLY_EVERY = 30, 600


_last_purge = None


def _on(var: str) -> bool:
    return os.getenv(var, "on").lower() not in ("off", "0", "false", "no")


def _weekly_once():
    """The maintenance check: the weekly report when due, and once a day the 90-day conversation purge."""
    global _last_purge
    now = datetime.now(timezone.utc)
    if _last_purge is None or (now - _last_purge).total_seconds() >= 86400:
        with _db() as c:
            n = conversations.purge(c)
        _last_purge = now
        if n:
            weekly_report.log.info("purged %d conversations older than %d days", n, conversations.KEEP_DAYS)
    if _on("D3_NIGHTLY"):  # seq-4 loop "Hằng đêm": from 01:00 UTC+7, once yesterday is missing from the analytics store
        rollup.due_and_run(now)
    if _on("D3_WEEKLY_REPORT") and weekly_report.due(now):
        with _db() as c:
            weekly_report.send_week(c, now)


async def _weekly_loop():
    await asyncio.sleep(WEEKLY_FIRST)
    while True:
        try:
            await asyncio.to_thread(_weekly_once)
        except Exception:
            weekly_report.log.exception("weekly report check failed")
        await asyncio.sleep(WEEKLY_EVERY)


@asynccontextmanager
async def lifespan(_app):
    task = None
    if "pytest" not in sys.modules:  # tests call the modules directly and must never send or roll up
        weekly_report.log.info("weekly report: %s (Monday from 08:00 UTC+7); nightly analytics: %s (from 01:00 UTC+7)",
                               "on" if _on("D3_WEEKLY_REPORT") else "off", "on" if _on("D3_NIGHTLY") else "off")
        task = asyncio.create_task(_weekly_loop())  # also the daily conversation purge
    worker = None
    if os.getenv("D3_INTAKE_WORKER", "on").lower() in ("off", "0", "false", "no"):
        intake.log.info("upload queue worker: off (D3_INTAKE_WORKER)")
    elif "pytest" not in sys.modules:  # tests drive intake.process_next directly
        worker = intake.Worker({"processor": _processor, "img_dir": IMG_DIR,
                                "after_photo": [image_sizes.after_photo]})  # act-1: optimised sizes (publishing-workflow)
        worker.start()
    yield
    if task:
        task.cancel()
    if worker:
        worker.stop.set()


app = FastAPI(title="D3 Studio AI", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=auth.SECRET)  # only holds the OAuth state during Google sign-in
if origins := [o.strip() for o in os.getenv("D3_CORS_ORIGINS", "").split(",") if o.strip()]:
    # the site on GitHub Pages calls this API from another origin; tokens travel in the Authorization header, so no cookies
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["*"], allow_headers=["Authorization", "Content-Type"])
app.include_router(auth.router)
IMG_DIR.mkdir(exist_ok=True)
mimetypes.add_type("image/webp", ".webp")  # the optimised copies (publishing-workflow); slim images lack the entry
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


def _hits(rows) -> list[dict]:
    """Search / similar results with their optimised copies (publishing-workflow), in one lookup."""
    out = [_hit(r) for r in rows]
    if out:
        with _db() as c:
            sizes = {r["id"]: r for r in c.execute("SELECT id, kich_thuoc, chieu_rong FROM space WHERE id = ANY(%s)",
                                                   ([h["id"] for h in out],)).fetchall()}
        for h in out:
            h.update({k: sizes.get(h["id"], {}).get(k) for k in ("kich_thuoc", "chieu_rong")})
    return out


@lru_cache(maxsize=1)
def _processor():  # loads YOLO + SigLIP2 on first ingest only
    from pipeline.processor import SpaceImageProcessor
    return SpaceImageProcessor()


@app.get("/spaces")
def list_spaces(space_type: Optional[str] = None, design_style: Optional[str] = None,
                review_status: Optional[str] = None, limit: int = 50, offset: int = 0,
                ids: Optional[str] = Query(default=None, pattern=r"^\d+(,\d+)*$", description="comma list, ≤ 60"),
                tra_ve: bool = Query(default=False, description="staff: only drafts returned with a reason"),
                user=Depends(optional_user)):
    id_list = [int(i) for i in ids.split(",")] if ids else None  # the browser collection shows its photos in one call
    if id_list and len(id_list) > bo_suu_tap.MAX_ITEMS:
        raise HTTPException(422, f"at most {bo_suu_tap.MAX_ITEMS} ids")
    staff = _is_staff(user)
    if not staff:
        review_status = "published" if review_status in (None, "published") else "none"  # no such status: matches nothing
    with _db() as c:
        return c.execute(  # hang_xem: rank by views in the last 30 processed days, for sorting (search-explanations)
            "WITH hx AS (SELECT k.space_id, rank() OVER (ORDER BY sum(k.so_xem) DESC) AS hang_xem FROM tk_khong_gian_ngay k "
            "            WHERE k.ngay > (SELECT max(ngay) FROM tk_ngay) - 30 GROUP BY k.space_id HAVING sum(k.so_xem) > 0) "
            f"SELECT {FIELDS}, palette->>'brightness' AS brightness, palette->>'temperature' AS temperature, {TAGS}, hx.hang_xem"
            + (", ly_do_duyet, " + AI_FIELDS + ", " + PENDING_VALUE if staff else "") + " "  # staff-only: review reason, AI proposal, suggestions
            "FROM space LEFT JOIN hx ON hx.space_id = space.id WHERE (%(t)s::text IS NULL OR space_type=%(t)s) "
            "AND (NOT %(rv)s OR ly_do_duyet->>'loai' IN ('tra_ve', 'mo_lai', 'go_xuong')) "
            "AND (%(s)s::text IS NULL OR design_style=%(s)s) AND (%(r)s::text IS NULL OR review_status=%(r)s) "
            "AND (%(i)s::int[] IS NULL OR id = ANY(%(i)s)) ORDER BY id LIMIT %(l)s OFFSET %(o)s",
            {"t": space_type, "s": design_style, "r": review_status, "i": id_list, "rv": tra_ve and staff,
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
    hits = _hits(similar_to(row["relative_path"], min(k, 24), published_only=not staff))
    with _db() as c:  # seq-2 b9-b10: why each one is similar, from the labels it shares with this photo
        why = explain.shared_reasons(c, space_id, [h["id"] for h in hits])
    return [{**h, "ly_do": why.get(h["id"], [])} for h in hits]


@app.get("/projects/{folder}/spaces")
def project_spaces(folder: str = PathParam(pattern=r"^[a-z0-9_]{1,60}$"), user=Depends(optional_user)):
    """Spaces of one project folder (the site's slug with '-' -> '_'), by file name; visitors get published ones only.
    project-catalog: also the spaces matched to that site project from other folders; anh_trang names the site file."""
    with _db() as c:
        return c.execute(
            f"SELECT {FIELDS}, du_an_slug, anh_trang FROM space WHERE (split_part(relative_path, '/', 1) = %(f)s "
            "OR du_an_slug = replace(%(f)s, '_', '-')) AND (%(all)s OR review_status = 'published') "
            "ORDER BY relative_path COLLATE \"C\"", {"f": folder, "all": _is_staff(user)}).fetchall()


# ── Project catalog (change: project-catalog; roadmap 0.1, UC02) ─────────────────────────────────────────────
SLUG = r"^[a-z0-9-]{1,60}$"
PROJECT_STAFF_FIELDS = ("dien_tich_m2", "so_phong_ngu", "thoi_gian_thi_cong", "muc_dau_tu", "thuyet_minh")
PROJECT_FIELDS = "slug, ten, loai, nam, mo_ta_ngan, co_trang, " + ", ".join(PROJECT_STAFF_FIELDS) + ", cap_nhat_luc"
PHOTO_ORDER = 'anh_trang COLLATE "C" NULLS LAST, relative_path COLLATE "C"'  # the site's photo order, then file name


@app.get("/projects", dependencies=[Depends(limit("projects", 120, 60))])
def list_projects(user=Depends(optional_user)):
    """Visitors: projects with a published photo. Staff: every site project and every folder project with photos."""
    staff = _is_staff(user)
    with _db() as c:
        rows = c.execute(f"""
            SELECT d.slug, d.ten, d.loai, d.nam, d.mo_ta_ngan, d.co_trang,
                   count(s.id) FILTER (WHERE s.review_status = 'published') AS so_anh_da_dang,
                   count(s.id) FILTER (WHERE s.review_status <> 'published') AS so_anh_chua_dang,
                   (SELECT json_build_object('id', p.id, 'relative_path', p.relative_path, 'anh_trang', p.anh_trang,
                                             'alt_text', p.alt_text)
                      FROM space p WHERE p.du_an_slug = d.slug AND p.review_status = 'published'
                     ORDER BY {PHOTO_ORDER} LIMIT 1) AS anh_dai_dien
              FROM du_an d LEFT JOIN space s ON s.du_an_slug = d.slug
             GROUP BY d.slug
            HAVING count(s.id) FILTER (WHERE s.review_status = 'published') > 0
                OR (%(staff)s AND (d.thu_tu IS NOT NULL OR count(s.id) > 0))
             ORDER BY d.thu_tu NULLS LAST, d.ten""", {"staff": staff}).fetchall()
    if not staff:
        for r in rows:
            del r["so_anh_chua_dang"]
    return rows


@app.get("/projects/filter", dependencies=[Depends(limit("projects", 120, 60))])
def projects_filter(phong_cach: list[str] = Query(default=[]), loai_cong_trinh: list[str] = Query(default=[]),
                    muc_dau_tu: list[str] = Query(default=[]), dien_tich_tu: Optional[float] = Query(default=None, ge=0),
                    dien_tich_den: Optional[float] = Query(default=None, ge=0),
                    sap_xep: Literal["moi_nhat", "dien_tich", "xem_nhieu"] = "moi_nhat", limit: int = Query(default=60, ge=1, le=60)):
    """seq-10, BFD 1.1-1.2: published projects matching every filter, counts per value, a loosening suggestion when
    nothing matches, sorted. Public."""
    with _db() as c:
        return project_filter.filter_projects(c, {"phong_cach": phong_cach, "loai_cong_trinh": loai_cong_trinh,
                                                   "muc_dau_tu": muc_dau_tu}, (dien_tich_tu, dien_tich_den), sap_xep, limit)


@app.get("/projects/{slug}", dependencies=[Depends(limit("projects", 120, 60))])
def get_project(slug: str = PathParam(pattern=SLUG), user=Depends(optional_user)):
    staff = _is_staff(user)
    with _db() as c:
        project = c.execute(f"SELECT {PROJECT_FIELDS} FROM du_an WHERE slug = %s", (slug,)).fetchone()
        spaces = c.execute(f"SELECT {FIELDS}, anh_trang FROM space WHERE du_an_slug = %(s)s "
                           f"AND (%(all)s OR review_status = 'published') ORDER BY {PHOTO_ORDER}",
                           {"s": slug, "all": staff}).fetchall() if project else []
    if not project or not (staff or spaces):
        raise HTTPException(404, "no such project")
    return {**project, "spaces": spaces}


class ProjectDetailsIn(BaseModel):
    model_config = {"extra": "forbid"}  # the site fields come from projects.js only
    dien_tich_m2: Optional[float] = Field(default=None, gt=0, le=100000)
    so_phong_ngu: Optional[int] = Field(default=None, gt=0, le=100)
    thoi_gian_thi_cong: Optional[str] = Field(default=None, max_length=80)
    muc_dau_tu: Optional[str] = None
    thuyet_minh: Optional[str] = Field(default=None, max_length=4000)


@app.put("/projects/{slug}")
def save_project(body: ProjectDetailsIn, slug: str = PathParam(pattern=SLUG), user=Depends(require(*APPROVERS))):
    """UC02 project details, by the lead architect or admin; every change is logged with the old and new values."""
    _check_value("muc_dau_tu", "muc_dau_tu", body.muc_dau_tu)
    new = body.model_dump()
    with _db() as c:
        old = c.execute(f"SELECT {', '.join(PROJECT_STAFF_FIELDS)} FROM du_an WHERE slug = %s FOR UPDATE", (slug,)).fetchone()
        if not old:
            raise HTTPException(404, "no such project")
        old = {k: float(v) if k == "dien_tich_m2" and v is not None else v for k, v in old.items()}
        changed = {k: new[k] for k in PROJECT_STAFF_FIELDS if new[k] != old[k]}
        if changed:
            c.execute(f"UPDATE du_an SET {', '.join(f'{k} = %({k})s' for k in changed)}, cap_nhat_luc = now() "
                      "WHERE slug = %(slug)s", {**changed, "slug": slug})
            c.execute("INSERT INTO nhat_ky_du_an (du_an_slug, user_id, hanh_dong, chi_tiet) VALUES (%s, %s, 'sua', %s)",
                      (slug, user["id"], Jsonb({"truoc": {k: old[k] for k in changed}, "sau": changed})))
        return c.execute(f"SELECT {PROJECT_FIELDS} FROM du_an WHERE slug = %s", (slug,)).fetchone()


WEAK_TEXT_SCORE = 0.10  # calibrated on 11 queries (search-explanations/tasks.md): vague / unrelated ones scored 0.03-0.09
INTERIOR_MIN = 0.5      # zero-shot interior share: library photos >= 0.92, logo / text / grey / noise <= 0.012
NOT_INTERIOR = "Ảnh này có vẻ không phải ảnh nội thất. Bạn thử một ảnh chụp căn phòng khác nhé."
WEAK_HINT = "Ít kết quả thật sát. Bạn thử mô tả cụ thể hơn: loại phòng, phong cách, vật liệu hoặc màu sắc."


@app.get("/search")
def search(q: str, space_type: Optional[str] = None, k: int = 6, user=Depends(optional_user)):
    """seq-11: room type / style named in the description become hard filters (an explicit space_type wins), the rest
    is compared by meaning; each result says which of its labels the description named; weak matches get a hint."""
    _check_value("khong_gian", "space_type", space_type)
    found, rest = explain.parse_query(q)
    cons = [c for c in found if not (space_type and c["chieu"] == "khong_gian")]
    room = space_type or next((c["ma"] for c in cons if c["chieu"] == "khong_gian"), None)
    style = next((c["ma"] for c in cons if c["chieu"] == "phong_cach"), None)
    rows = by_text(rest or q, room, min(k, 24), published_only=not _is_staff(user), design_style=style)
    hits = _hits(rows)
    with _db() as c:
        why = explain.text_reasons(c, q, cons, [h["id"] for h in hits])
    weak = not rows or (not cons and rows[0][3] < WEAK_TEXT_SCORE)
    return {"ket_qua": [{**h, "ly_do": why.get(h["id"], [])} for h in hits], "rang_buoc": cons,
            "goi_y": WEAK_HINT if weak else None}


@app.post("/search/image", dependencies=[Depends(limit("search_image", 10, 60))])
def search_image(file: UploadFile = File(...), space_type: Optional[str] = Form(None), k: int = 6,
                 user=Depends(optional_user)):
    """seq-8: the photo is embedded in memory and never stored. Not an interior -> a polite refusal and no results;
    otherwise its likely style and tone (from the closest library photos) and the results with reasons."""
    if Path(file.filename or "").suffix.lower() not in IMAGE_TYPES:
        raise HTTPException(415, "Chỉ nhận ảnh JPG, PNG hoặc WEBP.")
    _check_value("khong_gian", "space_type", space_type)
    data = file.file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "Ảnh quá lớn, tối đa 8 MB.")
    staff = _is_staff(user)
    try:
        vec = embed_photo(io.BytesIO(data))
    except (OSError, Image.DecompressionBombError):  # not an image, truncated, or a decompression bomb
        raise HTTPException(415, "Không đọc được ảnh này, hãy thử một ảnh JPG, PNG hoặc WEBP khác.")
    with _db() as c:
        register_vector(c)
        best = c.execute("SELECT 1 - (embedding <=> %s) AS s FROM space WHERE embedding IS NOT NULL "
                         "ORDER BY embedding <=> %s LIMIT 1", (vec, vec)).fetchone()
        if explain.interior_score(vec) < INTERIOR_MIN or not best or best["s"] < MIN_IMAGE_SCORE:
            return {"noi_that": False, "thong_bao": NOT_INTERIOR, "dac_diem": {}, "ket_qua": []}
        traits = explain.traits(c, vec, published_only=not staff)
    hits = _hits(by_image(None, space_type, k, published_only=not staff, vec=vec))
    with _db() as c:  # a result's labels that match the photo's traits
        labs = explain.labels(c, [h["id"] for h in hits])
    want = {(d, t["ma"]) for d, t in traits.items()}
    for h in hits:
        h["ly_do"] = ["Cùng " + explain.phrase(d, dn, vn) for d, dn, v, vn in labs.get(h["id"], []) if (d, v) in want]
    return {"noi_that": True, "dac_diem": traits, "ket_qua": hits}


def project_folder(name: str) -> str:
    """'Biệt thự Thảo Điền' -> 'biet_thu_thao_dien': the folder doubles as the project name, keep it URL- and path-safe."""
    return taxonomy_admin.slug(name)


MAX_BATCH = 50
INGEST_KIND = "xu_ly_anh"  # tests swap in a kind the live worker does not run


@app.post("/spaces/ingest", status_code=202)
def ingest(files: list[UploadFile] = File(...), project: str = Form(""), user=Depends(require(*STAFF))):
    """seq-1 steps 2-5: store the originals, queue one processing task per photo and answer at once.
    A file of the wrong type or size is refused alone; the rest are queued."""
    if len(files) > MAX_BATCH:
        raise HTTPException(422, f"tối đa {MAX_BATCH} ảnh mỗi lần tải lên")
    folder = IMG_DIR / (project_folder(project) or UPLOAD_DIR.name)
    tasks, refused = [], []
    with _db() as c:
        for file in files:
            name = Path(file.filename or "").name  # .name strips any path component; same name in a project = re-upload
            if Path(name).suffix.lower() not in IMAGE_TYPES:
                refused.append({"name": name, "ly_do": "Chỉ nhận ảnh JPG, PNG hoặc WEBP."})
                continue
            data = file.file.read(MAX_UPLOAD + 1)
            if len(data) > MAX_UPLOAD:
                refused.append({"name": name, "ly_do": "Ảnh quá lớn, tối đa 8 MB."})
                continue
            folder.mkdir(exist_ok=True)
            (folder / name).write_bytes(data)
            rel = (folder / name).relative_to(IMG_DIR).as_posix()
            tid = intake.enqueue(c, INGEST_KIND, {"relative_path": rel}, user["id"])
            tasks.append({"id": tid, "relative_path": rel, "trang_thai": "dang_xu_ly"})
    return {"tasks": tasks, "refused": refused}


@app.get("/spaces/ingest/tasks", dependencies=[Depends(require(*STAFF))])
def ingest_tasks(ids: str = Query(pattern=r"^\d+(,\d+){0,199}$")):
    """Progress of queued uploads (seq-1 b6, b16): dang_xu_ly | xong (with space_id) | loi (with the reason)."""
    with _db() as c:
        return intake.status(c, [int(i) for i in ids.split(",")])


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


def _missing_required(c, space_id: int) -> list[str]:
    """act-1 "Đủ các features bắt buộc?": names of required dimensions the photo has no value in."""
    return [r["ten"] for r in c.execute(
        "SELECT d.ten FROM chieu_phan_loai d JOIN space s ON s.id = %(s)s WHERE d.bat_buoc AND CASE d.ma_dinh_danh "
        "  WHEN 'khong_gian' THEN COALESCE(s.space_type, '') = '' WHEN 'phong_cach' THEN COALESCE(s.design_style, '') = '' "
        "  ELSE NOT EXISTS (SELECT 1 FROM space_gia_tri sg JOIN gia_tri_phan_loai g ON g.id = sg.gia_tri_id "
        "                   WHERE sg.space_id = s.id AND g.chieu_id = d.id) END ORDER BY d.thu_tu, d.id", {"s": space_id}).fetchall()]


def _advance(c, space_id: int, status: str, user, rights_confirmed: bool) -> str:
    """One QT-01 step with its role and rights rules. Raising inside `with _db()` rolls the transaction back."""
    if status not in NEXT:
        raise HTTPException(409, f"space {space_id}: '{status}' is the final state")
    if user["role"] not in ADVANCE_ROLES.get(status, APPROVERS):
        raise HTTPException(403, f"space {space_id}: «{STATUS_VI.get(status, status)}» cannot be moved on by {user['role']}")
    if status == "draft" and (missing := _missing_required(c, space_id)):
        raise HTTPException(422, {"space_id": space_id, "thieu": missing, "msg": "Thiếu: " + ", ".join(missing)})
    new = NEXT[status]
    if new == "cleared" and not rights_confirmed:
        raise HTTPException(422, f"space {space_id}: confirm the client allowed publishing these photos (rights_confirmed)")
    c.execute("UPDATE space SET review_status=%s, ly_do_duyet=NULL" + (", ngay_xuat_ban = now()" if new == "published" else "")
              + " WHERE id=%s", (new, space_id))  # moved on: reason done; seq-6 b17: the publish date
    _log(c, space_id, user, "advance", {"from": status, "to": new, **({"rights_confirmed": True} if new == "cleared" else {})})
    if new == "published":  # seq-6 b18: the photo joins the assistant's knowledge (queued, no Gemini call)
        intake.enqueue(c, "nap_tri_thuc", {"space_id": space_id}, user["id"])
    return new


def _handover(tasks: BackgroundTasks, moved: dict, rows_by_id: dict, user):
    """seq-6 b4 / b7: tell the content staff (-> editing) and the lead architects (-> in review), once per action."""
    for kind, status in (("bien_tap", "editing"), ("duyet", "in_review")):
        items = [(sid, rows_by_id[sid]) for sid, st in moved.items() if st == status]
        if items:
            tasks.add_task(notify.notify_handover, kind, items, user["email"])


@app.patch("/spaces/{space_id}")
def review(space_id: int, body: Review, tasks: BackgroundTasks, user=Depends(require(*STAFF, "content"))):
    _check_value("khong_gian", "space_type", body.space_type)
    _check_value("phong_cach", "design_style", body.design_style)
    sent = {k: v for k, v in body.model_dump(include=set(EDITABLE)).items() if v is not None}
    if "materials" in sent:
        sent["materials"] = [m.strip() for m in sent["materials"] if m.strip()]
    with _db() as c:
        row = c.execute("SELECT review_status, space_type, design_style, caption, alt_text, materials, hotspots "
                        "FROM space WHERE id=%s FOR UPDATE", (space_id,)).fetchone()
        if not row:
            raise HTTPException(404, "space not found")
        if user["role"] == "content" and (body.hotspots is not None or set(sent) - TEXT
                                          or row["review_status"] not in ("editing", "in_review")
                                          or (body.advance and row["review_status"] != "editing")):
            raise HTTPException(403, "content editors may only edit the caption and alt text of spaces being edited or in "
                                     "review, and send edited ones to review")
        if changes := {k: v for k, v in sent.items() if v != row[k]}:
            c.execute(f"UPDATE space SET {', '.join(k + '=%s' for k in changes)} WHERE id=%s", (*changes.values(), space_id))
            _log(c, space_id, user, "edit", {"from": {k: row[k] for k in changes}, "to": changes})
            if {"space_type", "design_style"} & set(changes):
                label_feedback.record(c, space_id, user["id"])  # seq-1 b21: corrected labels, for model evaluation
        if body.hotspots is not None:
            objs = (row["hotspots"] or {}).get("objects", [])
            if bad := [h.index for h in body.hotspots if h.index >= len(objs)]:
                raise HTTPException(422, f"no detected object at index {bad[0]}")
            kept = [{**objs[h.index], "label_vi": h.label_vi} for h in body.hotspots]  # coordinates stay as detected
            c.execute("UPDATE space SET hotspots = jsonb_set(hotspots, '{objects}', %s) WHERE id=%s", (Jsonb(kept), space_id))
            _log(c, space_id, user, "hotspots", {"kept": [h.index for h in body.hotspots], "of": len(objs)})
        if body.advance:
            new = _advance(c, space_id, row["review_status"], user, body.rights_confirmed)
            path = c.execute("SELECT relative_path FROM space WHERE id=%s", (space_id,)).fetchone()["relative_path"]
            _handover(tasks, {space_id: new}, {space_id: path}, user)
        return c.execute(f"SELECT {FIELDS} FROM space WHERE id=%s", (space_id,)).fetchone()


class SuggestValue(BaseModel):
    chieu: Literal["khong_gian", "phong_cach"]
    text: str = Field(min_length=1, max_length=60)
    force: bool = False  # the reviewer saw "Did you mean …?" and still wants the new word


SUGGEST_FIELDS = "id, relative_path, caption, materials, palette, hotspots, space_type, design_style"


def _wait_on_suggestion(c, space, dim, text, user, draft) -> int:
    """Save / join the suggestion and set the photo to "Other" through the same log as a manual edit."""
    cid = value_suggest.upsert(c, dim, text, space["id"], user["id"], draft, space)
    col, other = value_suggest.DIMS[dim], taxonomy.OTHER[dim]
    if space[col] != other:
        c.execute(f"UPDATE space SET {col} = %s WHERE id = %s", (other, space["id"]))
        _log(c, space["id"], user, "edit", {"from": {col: space[col]}, "to": {col: other}, "goi_y": cid})
        label_feedback.record(c, space["id"], user["id"])
    return cid


@app.post("/spaces/{space_id}/suggest-value")
def suggest_value(space_id: int, body: SuggestValue, user=Depends(require(*STAFF))):
    """A reviewer typed a room type / style the list doesn't have (review-tag-autocomplete). In order: an exact match,
    an undecided suggestion of the same word, a near spelling, Gemini's opinion; only then a new suggestion. The photo
    waits on "Other" until an approver decides."""
    text, dim = " ".join(body.text.split()), body.chieu
    if not text:
        raise HTTPException(422, "text is empty")
    if ma := value_suggest.exact(dim, text):
        return {"kind": "existing", "ma": ma, "source": "exact"}

    def space_row(c):
        row = c.execute(f"SELECT {SUGGEST_FIELDS} FROM space WHERE id = %s FOR UPDATE", (space_id,)).fetchone()
        if not row:
            raise HTTPException(404, "space not found")
        return row

    with _db() as c:
        space = space_row(c)
        if value_suggest.pending(c, dim, text):  # someone already suggested it: join, no second AI call
            return {"kind": "suggested", "id": _wait_on_suggestion(c, space, dim, text, user, None)}
    if not body.force and (ma := value_suggest.spelling(dim, text)):
        return {"kind": "existing", "ma": ma, "source": "spelling"}
    rate_check("suggest_value", user["id"], 10, 60)  # only the calls that reach Gemini count
    draft = value_suggest.ai_check(space, dim, text)  # slow (seconds): outside the transaction
    if draft and draft["trung_voi"] and not body.force:
        return {"kind": "existing", "ma": draft["trung_voi"], "source": "ai", "ly_do": draft["ly_do"]}
    with _db() as c:
        space = space_row(c)  # re-read: it may have been edited while Gemini answered
        out = {"kind": "suggested", "id": _wait_on_suggestion(c, space, dim, text, user, draft)}
    if draft and draft["anh_khop"] is False:  # the photo doesn't show the word's features: tell the reviewer now
        out["canh_bao"] = draft["nhan_xet_anh"] or f"Ảnh này có vẻ không thể hiện «{text}»."
        out["gan_nhat"] = draft["gan_nhat"]
    elif draft and draft["caption"]:  # same Gemini call: a caption / alt text for the new value, unsaved until Lưu
        out["caption"], out["alt_text"] = draft["caption"], draft["alt_text"]
    return out


class AdvanceMany(BaseModel):
    space_ids: list[int] = Field(min_length=1, max_length=500)
    rights_confirmed: bool = False


@app.post("/spaces/advance")
def advance_many(body: AdvanceMany, tasks: BackgroundTasks, user=Depends(require(*STAFF, "content"))):
    """All or nothing: one space that cannot move rolls the whole selection back, and the error names it."""
    with _db() as c:
        rows = c.execute("SELECT id, review_status, relative_path FROM space WHERE id = ANY(%s) ORDER BY id FOR UPDATE",
                         (body.space_ids,)).fetchall()
        if missing := set(body.space_ids) - {r["id"] for r in rows}:
            raise HTTPException(404, f"space {min(missing)} not found")
        moved = {r["id"]: _advance(c, r["id"], r["review_status"], user, body.rights_confirmed) for r in rows}
    _handover(tasks, moved, {r["id"]: r["relative_path"] for r in rows}, user)
    return {"advanced": sorted(moved), "status": sorted(set(moved.values()))}


# ── Backward paths (change: review-return-reject; act-1, seq-6 b9-12) ─────────────────────────────────────
RETURNABLE = {"editing", "in_review", "approved", "cleared"}  # -> draft ("Trả về nháp")
BACK = {  # action: (allowed source statuses, target status, reason kind, log action)
    "return": (RETURNABLE, "draft", "tra_ve", "return"),
    "keep_internal": ({"approved", "cleared"}, "noi_bo", "noi_bo", "keep_internal"),  # client refused publishing
    "reopen": ({"noi_bo"}, "draft", "mo_lai", "reopen"),
    # unpublish-photos: a published photo taken down, to fix it (draft) or because the client withdrew consent (noi_bo)
    "unpublish": ({"published"}, "draft", "go_xuong", "unpublish"),
    "unpublish_internal": ({"published"}, "noi_bo", "go_noi_bo", "unpublish"),
}
STATUS_VI = {"draft": "Nháp", "editing": "Chờ biên tập", "in_review": "Chờ duyệt", "approved": "Đã duyệt", "cleared": "Đã xác nhận quyền",
             "published": "Đã đăng", "noi_bo": "Lưu nội bộ"}


class MoveBack(BaseModel):
    space_ids: list[int] = Field(min_length=1, max_length=500)
    ly_do: str = Field(max_length=500)

    @field_validator("ly_do")
    @classmethod
    def _reason(cls, v):
        v = " ".join(v.split())
        if len(v) < 5:
            raise ValueError("lý do cần ít nhất 5 ký tự")
        return v


def _move_back(action: str, body: MoveBack, user, tasks: BackgroundTasks) -> dict:
    """All or nothing, like /spaces/advance: one photo in the wrong status rolls the whole selection back."""
    sources, target, kind, log_action = BACK[action]
    with _db() as c:
        rows = c.execute("SELECT id, relative_path, review_status FROM space WHERE id = ANY(%s) ORDER BY id FOR UPDATE",
                         (body.space_ids,)).fetchall()
        if missing := set(body.space_ids) - {r["id"] for r in rows}:
            raise HTTPException(404, f"space {min(missing)} not found")
        if bad := next((r for r in rows if r["review_status"] not in sources), None):
            raise HTTPException(409, f"space {bad['id']}: không thể từ «{STATUS_VI.get(bad['review_status'], bad['review_status'])}»")
        shown = {"loai": kind, "ly_do": body.ly_do, "boi": user["email"], "luc": c.execute("SELECT now()").fetchone()["now"].isoformat()}
        for r in rows:
            c.execute("UPDATE space SET review_status=%s, ly_do_duyet=%s WHERE id=%s", (target, Jsonb(shown), r["id"]))
            _log(c, r["id"], user, log_action, {"from": r["review_status"], "to": target, "reason": body.ly_do})
            if r["review_status"] == "published":  # taken down: out of the assistant's knowledge too (publishing-workflow)
                c.execute("DELETE FROM space_text WHERE space_id = %s", (r["id"],))
    tasks.add_task(notify.notify_returned, [(r["id"], r["relative_path"], kind, body.ly_do) for r in rows], user["email"])
    return {"moved": [r["id"] for r in rows], "status": target}


@app.post("/spaces/return")
def return_spaces(body: MoveBack, tasks: BackgroundTasks, user=Depends(require(*APPROVERS))):
    """"Trả về nháp": in review / approved / cleared -> draft, with a reason the uploader is told about."""
    return _move_back("return", body, user, tasks)


@app.post("/spaces/keep-internal")
def keep_internal(body: MoveBack, tasks: BackgroundTasks, user=Depends(require(*APPROVERS))):
    """"Lưu nội bộ": approved / cleared -> noi_bo, a final status never shown publicly (act-1)."""
    return _move_back("keep_internal", body, user, tasks)


@app.post("/spaces/reopen")
def reopen_spaces(body: MoveBack, tasks: BackgroundTasks, user=Depends(require(*APPROVERS))):
    """"Mở lại": noi_bo -> draft."""
    return _move_back("reopen", body, user, tasks)


class Unpublish(MoveBack):
    giu_noi_bo: bool = False  # True: the client withdrew consent -> "Lưu nội bộ"; False: back to draft to fix


@app.post("/spaces/unpublish")
def unpublish_spaces(body: Unpublish, tasks: BackgroundTasks, user=Depends(require(*APPROVERS))):
    """"Gỡ khỏi website": published -> draft or noi_bo, with a reason; separate from "Trả về nháp" on purpose."""
    return _move_back("unpublish_internal" if body.giu_noi_bo else "unpublish", body, user, tasks)


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


# about one published photo: stored with that photo's taxonomy values at that moment (class-4 note)
PHOTO_EVENTS = ("xem_khong_gian", "luu_anh", "chon_trac_nghiem", "xem_goi_y_tuong_tu", "chon_goi_y")
EVENT_TYPES = Literal["xem_khong_gian", "luu_anh", "chon_trac_nghiem", "xem_trang", "xem_du_an", "bam_CTA", "gui_form",
                      "nhan_chatbot", "chia_se", "ap_dung_bo_loc", "tim_kiem", "xem_goi_y_tuong_tu", "chon_goi_y"]
OBJECT_KIND = {"xem_du_an": "du_an", "xem_trang": "trang", "bam_CTA": "lien_ket", "gui_form": "form", "tim_kiem": "tim_kiem",
               "chia_se": "bo_suu_tap", "ap_dung_bo_loc": "bo_loc", "nhan_chatbot": "tro_ly",
               **{k: "khong_gian" for k in PHOTO_EVENTS}}  # class-4 SuKien.loai_doi_tuong
SESSION_ID = Field(default=None, pattern=r"^[A-Za-z0-9_-]{16,64}$")  # random browser tokens, never tied to an account
VN_DAY = "(now() AT TIME ZONE 'Asia/Ho_Chi_Minh')::date"  # analytics days are UTC+7 dates (tracking-pipeline)


class EventItem(BaseModel):
    """One behaviour event (UC21; class-4 SuKien). In a batch, cach_ms says how long before sending it happened."""
    loai: EVENT_TYPES
    space_id: Optional[int] = None
    trang: Optional[str] = Field(default=None, pattern=r"^/[a-z0-9/:_-]{0,99}$")  # route pattern, never a real path
    doi_tuong: Optional[str] = Field(default=None, pattern=r"^[A-Za-z0-9_/-]{1,100}$")  # slug, photo id, CTA target, form
    gia_tri: Optional[list[Annotated[str, StringConstraints(pattern=r"^[a-z0-9_]+:[A-Za-z0-9_]+$")]]] = Field(
        default=None, max_length=20)                 # filter values of ap_dung_bo_loc
    thoi_gian_dung_ms: Optional[int] = Field(default=None, ge=0, le=86_400_000)
    do_sau_cuon: Optional[float] = Field(default=None, ge=0, le=1)
    so_ket_qua: Optional[int] = Field(default=None, ge=0, le=1000)  # tim_kiem: number of results, never the query
    cach_ms: int = Field(default=0, ge=0, le=600_000)


def _not_demo(v):  # 'demo-' is reserved for pipeline/demo_activity.py, so demo data stays identifiable
    if v and v.startswith("demo-"):
        raise ValueError("phien_id_du_tru")
    return v


class Event(EventItem):
    """The earlier one-event body, still accepted."""
    dong_y: bool                                     # the visitor's answer on the consent banner
    phien_id: Optional[str] = SESSION_ID

    @field_validator("phien_id")
    @classmethod
    def _demo(cls, v):
        return _not_demo(v)


class EventBatch(BaseModel):
    """seq-4 b2-b3: the browser's buffer, sent every 5 s and when the page is left (at most 50 events)."""
    dong_y: bool
    phien_id: Optional[str] = SESSION_ID
    ma_thiet_bi: Optional[str] = SESSION_ID          # class-4: anonymous device id, only under analytics consent
    nguon: Optional[str] = Field(default=None, pattern=r"^[a-z0-9_]{1,40}$")  # truc_tiep | tim_kiem | ... | utm name
    thiet_bi: Optional[Literal["di_dong", "may_tinh_bang", "may_tinh"]] = None
    ca_nhan_hoa: bool = False                        # act-7: personalisation allowed too
    su_kien: list[EventItem] = Field(min_length=1, max_length=50)

    @field_validator("phien_id")
    @classmethod
    def _demo(cls, v):
        return _not_demo(v)


@app.post("/events", status_code=204, dependencies=[Depends(limit("events", 120, 60))])
def track(body: EventBatch | Event):
    """Behaviour signals (UC21; seq-4 b3-b5). The whole batch is validated first (one bad event refuses it). Only a
    consented session is stored, each event at the time it happened; otherwise only the day's anonymous count per
    type grows (NFR-09) and no session detail may be sent."""
    batch = body if hasattr(body, "su_kien") else EventBatch(  # not isinstance: a test may reload this module
        dong_y=body.dong_y, phien_id=body.phien_id, su_kien=[EventItem(**body.model_dump(exclude={"dong_y", "phien_id"}))])
    with _db() as c:
        if not (batch.dong_y and batch.phien_id):
            if batch.ma_thiet_bi or batch.nguon or batch.thiet_bi or batch.ca_nhan_hoa:
                raise HTTPException(422, "session details are only sent with consent")
            for loai, n in Counter(e.loai for e in batch.su_kien).items():
                c.execute(f"INSERT INTO su_kien_an_danh (ngay, loai, so_luong) VALUES ({VN_DAY}, %s, %s) "
                          "ON CONFLICT (ngay, loai) DO UPDATE SET so_luong = su_kien_an_danh.so_luong + EXCLUDED.so_luong",
                          (loai, n))
            return
        oldest, newest = max(e.cach_ms for e in batch.su_kien), min(e.cach_ms for e in batch.su_kien)
        c.execute(
            "INSERT INTO phien_truy_cap (id, da_dong_y_thu_thap, ma_thiet_bi, nguon, thiet_bi, ca_nhan_hoa, bat_dau, ket_thuc) "
            "VALUES (%(p)s, true, %(d)s, %(n)s, %(t)s, %(c)s, now() - %(o)s * interval '1 millisecond', "
            "        now() - %(w)s * interval '1 millisecond') "
            "ON CONFLICT (id) DO UPDATE SET ma_thiet_bi = COALESCE(EXCLUDED.ma_thiet_bi, phien_truy_cap.ma_thiet_bi), "
            "  nguon = COALESCE(phien_truy_cap.nguon, EXCLUDED.nguon), thiet_bi = COALESCE(EXCLUDED.thiet_bi, phien_truy_cap.thiet_bi), "
            "  ca_nhan_hoa = EXCLUDED.ca_nhan_hoa, bat_dau = LEAST(COALESCE(phien_truy_cap.bat_dau, EXCLUDED.bat_dau), EXCLUDED.bat_dau), "
            "  ket_thuc = GREATEST(COALESCE(phien_truy_cap.ket_thuc, EXCLUDED.ket_thuc), EXCLUDED.ket_thuc)",
            {"p": batch.phien_id, "d": batch.ma_thiet_bi, "n": batch.nguon, "t": batch.thiet_bi, "c": batch.ca_nhan_hoa,
             "o": oldest, "w": newest})
        for e in batch.su_kien:
            at = {"p": batch.phien_id, "l": e.loai, "k": OBJECT_KIND[e.loai], "ms": e.cach_ms, "s": e.space_id,
                  "o": e.doi_tuong}
            if e.loai not in PHOTO_EVENTS:  # no photo: stored as sent (every field validated)
                c.execute("INSERT INTO su_kien (phien_id, loai, loai_doi_tuong, trang, doi_tuong, gia_tri, thoi_gian_dung_ms, "
                          "do_sau_cuon, so_ket_qua, created_at) VALUES (%(p)s, %(l)s, %(k)s, %(t)s, %(o)s, %(g)s, %(d)s, %(c)s, "
                          "%(r)s, now() - %(ms)s * interval '1 millisecond')",
                          {**at, "t": e.trang, "g": e.gia_tri or [], "d": e.thoi_gian_dung_ms, "c": e.do_sau_cuon,
                           "r": e.so_ket_qua})
                continue
            c.execute("INSERT INTO su_kien (phien_id, loai, loai_doi_tuong, space_id, doi_tuong, gia_tri, created_at) "
                      "SELECT %(p)s, %(l)s, %(k)s, s.id, %(o)s, COALESCE((SELECT array_agg(d.ma_dinh_danh || ':' || v.ma_dinh_danh) "
                      "  FROM space_gia_tri sg JOIN gia_tri_phan_loai v ON v.id = sg.gia_tri_id "
                      "  JOIN chieu_phan_loai d ON d.id = v.chieu_id WHERE sg.space_id = s.id), '{}'), "
                      "  now() - %(ms)s * interval '1 millisecond' "
                      "FROM space s WHERE s.id = %(s)s AND s.review_status = 'published'", at)


class ForgetMe(BaseModel):
    phien_id: Optional[str] = SESSION_ID
    ma_thiet_bi: Optional[str] = SESSION_ID


@app.post("/privacy/xoa-du-lieu", dependencies=[Depends(limit("privacy", 5, 60))])
def forget_me(body: ForgetMe):
    """act-7 "Gửi yêu cầu xóa dữ liệu cá nhân": delete this browser's sessions (the current one and every one carrying
    its device id) with their events. Both ids are random values only that browser holds. Conversations and leads stay,
    detached (their FKs are ON DELETE SET NULL); figures already aggregated hold no session data and stay too.
    Only the counts and the time are logged."""
    if not (body.phien_id or body.ma_thiet_bi):
        raise HTTPException(422, "phien_id or ma_thiet_bi is required")
    with _db() as c:
        ids = [r["id"] for r in c.execute("SELECT id FROM phien_truy_cap WHERE id = %s OR (%s::text IS NOT NULL AND ma_thiet_bi = %s)",
                                           (body.phien_id, body.ma_thiet_bi, body.ma_thiet_bi)).fetchall()]
        events = c.execute("SELECT count(*) AS n FROM su_kien WHERE phien_id = ANY(%s)", (ids,)).fetchone()["n"]
        if ids:
            c.execute("DELETE FROM phien_truy_cap WHERE id = ANY(%s)", (ids,))
            c.execute("INSERT INTO yeu_cau_xoa_du_lieu (so_phien, so_su_kien) VALUES (%s, %s)", (len(ids), events))
    return {"so_phien": len(ids), "so_su_kien": events}


PHIEN = r"^[A-Za-z0-9_-]{16,64}$"  # the random browser session token of /events


class Chat(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    history: list[dict] = Field(default_factory=list, max_length=40)  # earlier turns, kept by the client
    contact: Optional[str] = Field(default=None, max_length=200)
    phien_id: Optional[str] = Field(default=None, pattern=PHIEN)
    gui_ho_so: bool = False                          # "gửi kèm những không gian tôi đã xem", ticked in the chat
    hoi_thoai_id: Optional[str] = Field(default=None, max_length=64)  # the stored conversation (chat-history)


@app.post("/chat", dependencies=[Depends(limit("chat", 20, 60))])
def chat(body: Chat, tasks: BackgroundTasks):
    """Public. Answers only from the knowledge base; otherwise says so and hands off to an architect.
    Every turn is stored (masked, anonymous unless the session is a consented one) and the constraints the visitor
    gave earlier in the conversation carry over (chat-history)."""
    with _db() as c:
        hid, rang_buoc, stored = conversations.start_or_get(c, body.hoi_thoai_id, body.phien_id)
        # the server's own turns once there are any; the lead keeps what the visitor saw, unmasked
        out = respond(body.message, stored or body.history, body.contact, body.phien_id, body.gui_ho_so,
                      rang_buoc=rang_buoc, lead_history=body.history or stored)
        blocked = out.pop("chu_de_cam", None)  # staff only: never in the public reply
        conversations.add_turn(c, hid, body.message, out["answer"], out["sources"], out.get("diem_cao_nhat"),
                               out["answered"], out["rang_buoc"], blocked)
        if out.get("lead_id"):
            conversations.link_lead(c, hid, out["lead_id"], handoff=not out["answered"])
    if out.get("lead_id"):
        tasks.add_task(notify.notify_new_lead, out["lead_id"])
    return {**out, "hoi_thoai_id": hid}


@app.get("/chat/{hid}", dependencies=[Depends(limit("chat", 20, 60))])
def chat_read(hid: str):
    """A visitor's own conversation; the random id is the only key. Masked text, no photos."""
    with _db() as c:
        out = conversations.read(c, hid)
    if out is None:
        raise HTTPException(404, "no such conversation")
    return out


@app.delete("/chat/{hid}", status_code=204, dependencies=[Depends(limit("chat", 20, 60))])
def chat_delete(hid: str):
    """"Bắt đầu cuộc mới": the old conversation is removed from the server."""
    with _db() as c:
        conversations.delete(c, hid)
    return Response(status_code=204)



# ── Conversations for staff (chat-history): how the assistant answers ─────────
CONVERSATION_ROLES = ("content", "sales", *APPROVERS)


@app.get("/conversations")
def conversations_list(loc: str = "tat_ca", days: int = 30, offset: int = Query(0, ge=0),
                       user=Depends(require(*CONVERSATION_ROLES))):
    """Newest first, 50 a page. loc: tat_ca | chua_tra_loi | lead. Masked text, no session id, no contact."""
    if loc not in conversations.FILTERS:
        raise HTTPException(422, [{"loc": ["query", "loc"], "msg": "loc must be tat_ca, chua_tra_loi or lead", "type": "value_error"}])
    if days not in (7, 30, 90):
        raise HTTPException(422, [{"loc": ["query", "days"], "msg": "days must be 7, 30 or 90", "type": "value_error"}])
    with _db() as c:
        return conversations.list_for_staff(c, loc, days, offset)


@app.get("/conversations/{hid}")
def conversation_detail(hid: str, user=Depends(require(*CONVERSATION_ROLES))):
    """Messages with each answer's sources and score, the collected constraints, the handoff flag and the lead id."""
    with _db() as c:
        out = conversations.detail_for_staff(c, hid)
    if out is None:
        raise HTTPException(404, "no such conversation")
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


# ── Style quiz (change: style-quiz; UC06, seq-12) ──────────────────────────────────────────────────────────
class QuizAnswers(BaseModel):
    cap: list[tuple[int, int]] = Field(min_length=1, max_length=quiz.QUESTIONS)  # the pairs shown, as GET /quiz gave them
    chon: list[int] = Field(max_length=quiz.QUESTIONS)                          # the photo chosen in each answered pair


def _quiz_result(c, body: QuizAnswers) -> dict:
    try:
        return quiz.result(c, [list(p) for p in body.cap], body.chon)
    except quiz.Invalid as e:
        raise HTTPException(422, [{"loc": ["body"], "msg": str(e), "type": "value_error"}])


@app.get("/quiz", dependencies=[Depends(limit("quiz", 30, 60))])
def quiz_pairs():
    """A new set of photo pairs, random each time; 409 'chua_du_anh' when the published photos allow < 4 pairs."""
    with _db() as c:
        pairs = quiz.build_pairs(quiz.eligible(c), random.Random(os.urandom(8)))
        if not pairs:
            raise HTTPException(409, "chua_du_anh")
        tiles = {t["id"]: t for t in quiz.tiles(c, [i for p in pairs for i in p])}
    return {"cau_hoi": [{"a": tiles[a], "b": tiles[b]} for a, b in pairs]}


@app.post("/quiz/result", dependencies=[Depends(limit("quiz", 30, 60))])
def quiz_result(body: QuizAnswers):
    """Scored here from the pairs and picks, never from client scores (one bucket with GET /quiz)."""
    with _db() as c:
        return _quiz_result(c, body)


@app.get("/quiz/me", dependencies=SIGNED_IN)
def my_quiz(user=Depends(require(*ROLES))):
    with _db() as c:
        row = c.execute("SELECT phong_cach, goi_y, updated_at FROM ket_qua_trac_nghiem WHERE nguoi_dung_id=%s",
                        (user["id"],)).fetchone()
        if not row:
            return Response(status_code=204)
        return {"phong_cach": row["phong_cach"], "goi_y": quiz.tiles(c, row["goi_y"]), "luu_luc": row["updated_at"]}


@app.put("/quiz/me", dependencies=SIGNED_IN)
def save_my_quiz(body: QuizAnswers, user=Depends(require(*ROLES))):
    """Re-scores the answers, so a saved result is never invented either; one result per account, replaced on save."""
    with _db() as c:
        out = _quiz_result(c, body)
        row = c.execute("INSERT INTO ket_qua_trac_nghiem (nguoi_dung_id, phong_cach, goi_y) VALUES (%s, %s, %s) "
                        "ON CONFLICT (nguoi_dung_id) DO UPDATE SET phong_cach = EXCLUDED.phong_cach, "
                        "goi_y = EXCLUDED.goi_y, updated_at = now() RETURNING updated_at",
                        (user["id"], Jsonb(out["phong_cach"]), [t["id"] for t in out["goi_y"]])).fetchone()
    return {**out, "luu_luc": row["updated_at"]}


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



# ── Hotspots by hand and the item library (seq-14; class-1 Hotspot / MonDo; roadmap 1.9) ──────────────
class HotspotIn(BaseModel):
    index: Optional[int] = None          # position of the detected object it comes from; None = made by hand
    x: float
    y: float
    label_vi: str = Field(max_length=120)
    mon_do_id: Optional[int] = None


class HotspotsIn(BaseModel):
    hotspots: list[HotspotIn] = Field(max_length=items.MAX_POINTS + 1)  # the exact limit is checked with a row-free message


def _item_error(e):
    if isinstance(e, items.Invalid):
        loc = ["body", "hotspots", e.row] if e.row is not None else ["body", e.field] if e.field else ["body"]
        return HTTPException(422, [{"loc": loc, "msg": e.msg, "type": "value_error"}])
    if isinstance(e, items.Conflict):
        return HTTPException(409, {"msg": str(e), "existing": e.existing})
    if isinstance(e, items.InUse):
        return HTTPException(409, {"msg": str(e), "so_anh": e.n})
    return HTTPException(404, "no such item")


@app.put("/spaces/{space_id}/hotspots")
def save_hotspots(space_id: int, body: HotspotsIn, user=Depends(require(*STAFF))):
    """Replace a photo's hotspots with the editor's list: add, move, delete, rename, link to an item (seq-14 b13-14)."""
    with _db() as c:
        row = c.execute("SELECT hotspots FROM space WHERE id = %s FOR UPDATE", (space_id,)).fetchone()
        if not row:
            raise HTTPException(404, "no such space")
        try:
            doc = items.validate_hotspots(c, row["hotspots"], [h.model_dump() for h in body.hotspots])
        except items.Invalid as e:
            raise _item_error(e)
        c.execute("UPDATE space SET hotspots = %s WHERE id = %s", (Jsonb(doc), space_id))
        objs = doc["objects"]
        _log(c, space_id, user, "hotspots", {"truoc": len((row["hotspots"] or {}).get("objects", [])), "sau": len(objs),
                                             "thu_cong": sum(o.get("nguon_tao") == "thu_cong" for o in objs),
                                             "lien_ket": sum(o.get("mon_do_id") is not None for o in objs)})
        out = with_services(doc, c)
    return {"hotspots": out}


class ItemIn(BaseModel):
    ten: Optional[str] = Field(default=None, max_length=120)
    phan_loai: Optional[str] = Field(default=None, max_length=60)
    kieu_dang: Optional[str] = Field(default=None, max_length=60)
    vat_lieu: Optional[str] = Field(default=None, max_length=60)
    mau_sac: Optional[str] = Field(default=None, max_length=40)
    nha_cung_cap: Optional[str] = Field(default=None, max_length=120)
    ghi_chu: Optional[str] = Field(default=None, max_length=500)
    dich_vu_id: Optional[int] = None  # a knowledge entry of kind 'service'; null unlinks


@app.get("/items/services")
def items_services(user=Depends(require(*STAFF))):
    """Service packages an item may point to (architects cannot open the knowledge screens)."""
    with _db() as c:
        return items.services(c)


@app.get("/items")
def items_list(q: str = "", limit: int = Query(200, ge=1, le=500), user=Depends(require(*STAFF))):
    """The library with how many photos use each item; q searches name, type and material."""
    with _db() as c:
        return items.search(c, q, limit)


@app.post("/items", status_code=201)
def items_create(body: ItemIn, user=Depends(require(*STAFF))):
    try:
        with _db() as c:
            return items.create(c, body.model_dump(exclude_unset=True), user["id"])
    except (items.Invalid, items.Conflict) as e:
        raise _item_error(e)


@app.patch("/items/{item_id}")
def items_update(item_id: int, body: ItemIn, user=Depends(require(*STAFF))):
    try:
        with _db() as c:
            return items.update(c, item_id, body.model_dump(exclude_unset=True), user["id"])
    except (items.Invalid, items.Conflict, items.NotFound) as e:
        raise _item_error(e)


@app.delete("/items/{item_id}", status_code=204)
def items_delete(item_id: int, user=Depends(require(*STAFF))):
    """Refused while any photo links to the item (409 with the photo count)."""
    try:
        with _db() as c:
            items.delete(c, item_id)
    except (items.InUse, items.NotFound) as e:
        raise _item_error(e)
    return Response(status_code=204)


@app.get("/items/{item_id}/spaces")
def items_spaces(item_id: int, user=Depends(optional_user)):
    """Photos whose hotspots link to the item. Visitors: published photos, the item's name and type only."""
    with _db() as c:
        out = items.spaces_for(c, item_id, staff=bool(user) and user["role"] in STAFF)
    if out is None:
        raise HTTPException(404, "no such item")
    return out

# ── Trend dashboard (UC22; act-3, seq-18) ──────────────────────────────────────
@app.get("/analytics/overview")
def analytics_overview(days: int = 30, user=Depends(require("sales", *APPROVERS))):
    """Interest score per taxonomy value, trends vs the 4-week average, totals, leads per week, top spaces.
    Aggregates only: no session id, account or contact data."""
    if days not in (7, 30, 90):  # a query string is text, so a Literal of ints would refuse "7"
        raise HTTPException(422, [{"loc": ["query", "days"], "msg": "days must be 7, 30 or 90", "type": "value_error"}])
    with _db() as c:
        return trends.overview(c, days)




# ── Homepage suggestions (tracking-pipeline; act-3 "Điều chỉnh gợi ý trên trang chủ") ─────────────────────────────
@app.get("/home/suggestions", dependencies=[Depends(limit("home_suggestions", 60, 60))])
def home_suggestions_public(phien_id: Optional[str] = Query(default=None, pattern=r"^[A-Za-z0-9_-]{16,64}$")):
    """Public. Up to 8 published spaces for "Đang được quan tâm"; the session id is used only when that session
    allowed personalisation (act-7), otherwise ignored."""
    with _db() as c:
        return home_suggestions.suggestions(c, phien_id)


@app.get("/analytics/home-suggestions")
def home_suggestions_admin(user=Depends(require("sales", *APPROVERS))):
    with _db() as c:
        return home_suggestions.admin_view(c)


class HomeSetting(BaseModel):
    gia_tri: str = Field(pattern=r"^[a-z0-9_]+:[A-Za-z0-9_]+$")
    che_do: Literal["tu_dong", "uu_tien", "an"]


@app.put("/analytics/home-suggestions")
def home_suggestions_set(body: HomeSetting, user=Depends(require("sales", *APPROVERS))):
    with _db() as c:
        try:
            return home_suggestions.set_mode(c, body.gia_tri, body.che_do, user["id"])
        except KeyError:
            raise HTTPException(404, "no such visitor-facing value")


@app.get("/analytics/behaviour")
def analytics_behaviour(days: int = 30, user=Depends(require("sales", *APPROVERS))):
    """Pages (time, scroll), projects, CTAs, forms, chat, shares, filters (behaviour-events). Counts and averages only."""
    if days not in (7, 30, 90):
        raise HTTPException(422, [{"loc": ["query", "days"], "msg": "days must be 7, 30 or 90", "type": "value_error"}])
    with _db() as c:
        return behaviour.overview(c, days)

# ── Project results (BFD 5.4; act-1 30-day check; roadmap 3.5) ────────────────
PROJECT_STATS_ROLES = ("sales", *STAFF)


def _stats_days(days: int) -> int:
    if days not in (30, 90):
        raise HTTPException(422, [{"loc": ["query", "days"], "msg": "days must be 30 or 90", "type": "value_error"}])
    return days


@app.get("/analytics/projects")
def analytics_projects(days: int = 30, cua_toi: bool = False, user=Depends(require(*PROJECT_STATS_ROLES))):
    """One row per project with published photos: views, saves, leads and the 30-day status. Counts only."""
    with _db() as c:
        return project_stats.overview(c, _stats_days(days), user["id"] if cua_toi else None)


@app.get("/analytics/projects/{folder}")
def analytics_project(folder: str, days: int = 30, user=Depends(require(*PROJECT_STATS_ROLES))):
    """One project's photos (most viewed first) and the suggestions that apply."""
    days = _stats_days(days)
    with _db() as c:
        out = project_stats.detail(c, folder, days)
    if out is None:
        raise HTTPException(404, "no published photo in this project")
    return out


# ── Weekly report (UC23; seq-18): opt-out, log, preview, test send ─────────────
REPORT_ROLES = ("sales", *APPROVERS)


class WeeklyOptIn(BaseModel):
    nhan: bool


@app.get("/me/weekly-report")
def weekly_opt_in(user=Depends(require(*REPORT_ROLES))):
    with _db() as c:
        return {"nhan": c.execute("SELECT nhan_bao_cao_tuan FROM app_user WHERE id=%s", (user["id"],)).fetchone()["nhan_bao_cao_tuan"]}


@app.put("/me/weekly-report")
def set_weekly_opt_in(body: WeeklyOptIn, user=Depends(require(*REPORT_ROLES))):
    with _db() as c:
        c.execute("UPDATE app_user SET nhan_bao_cao_tuan=%s WHERE id=%s", (body.nhan, user["id"]))
    return {"nhan": body.nhan}


@app.get("/reports/weekly")
def weekly_history(user=Depends(require(*APPROVERS))):
    """The last 8 weekly reports, newest first, without their text."""
    with _db() as c:
        return weekly_report.history(c)


@app.get("/reports/weekly/preview")
def weekly_preview(user=Depends(require(*APPROVERS))):
    """This week's report (the last full week), built now, not sent."""
    with _db() as c:
        r = weekly_report.build(c, datetime.now(timezone.utc))
        return {"tuan_bat_dau": r["tuan_bat_dau"], "tieu_de": r["tieu_de"], "noi_dung": r["noi_dung"],
                "nguoi_nhan": len(weekly_report.recipients(c))}


@app.post("/reports/weekly/test")
def weekly_test(user=Depends(require(*APPROVERS))):
    """A copy to the caller only; it does not count as the week's report."""
    if not notify._smtp_ready():
        raise HTTPException(409, "Chưa cấu hình email (D3_SMTP_HOST)")
    try:
        with _db() as c:
            return weekly_report.send_week(c, datetime.now(timezone.utc), force_to=user["email"])
    except Exception:
        weekly_report.log.exception("weekly report: test send failed")
        raise HTTPException(502, "Không gửi được email thử")

# ── Taxonomy admin (UC15) — data-driven dimensions/values; seq-15 flow ────────
@app.get("/taxonomy")
def taxonomy_list(user=Depends(optional_user)):
    """Dimensions with their values. Public: the portfolio filters read this too. Staff also get so_anh (spaces carrying
    each value, drafts included) to rank the review page's suggestions; visitors never see draft counts."""
    count = ", (SELECT count(*) FROM space_gia_tri sg WHERE sg.gia_tri_id = v.id) AS so_anh" if _is_staff(user) else ""
    with _db() as c:
        dims = c.execute("SELECT id, ma_dinh_danh, ten, bat_buoc, cho_phep_nhieu_gia_tri, hien_thi_cho_khach, thu_tu "
                         "FROM chieu_phan_loai ORDER BY thu_tu, id").fetchall()
        vals = c.execute(f"SELECT v.id, v.chieu_id, v.ma_dinh_danh, v.ten, v.tu_dong_nghia{count} "
                         "FROM gia_tri_phan_loai v ORDER BY v.id").fetchall()
    by_dim: dict = {}
    for v in vals:
        by_dim.setdefault(v["chieu_id"], []).append(v)
    for d in dims:
        d["values"] = by_dim.get(d["id"], [])
    return dims


def _tax_write(call):
    """Run one taxonomy_admin write in a transaction, map its errors, refresh the taxonomy cache."""
    try:
        with _db() as c:
            out = call(c)
    except taxonomy_admin.NotFound as e:
        raise HTTPException(404, str(e))
    except taxonomy_admin.Conflict as e:
        raise HTTPException(409, str(e))
    except taxonomy_admin.Invalid as e:
        raise HTTPException(422, str(e))
    taxonomy.reload()
    return out


@app.get("/taxonomy/admin")
def taxonomy_admin_tree(user=Depends(require(*APPROVERS))):
    """Every dimension and value with usage counts, and the 20 latest changes (seq-15 b1-6)."""
    with _db() as c:
        return taxonomy_admin.tree(c)


class NewDimension(BaseModel):
    ten: str = Field(min_length=1, max_length=80)
    cho_phep_nhieu_gia_tri: bool = False
    hien_thi_cho_khach: bool = True


@app.post("/taxonomy", status_code=201)
def add_dimension(body: NewDimension, user=Depends(require(*APPROVERS))):
    return _tax_write(lambda c: taxonomy_admin.add_dimension(c, user, body.ten, body.cho_phep_nhieu_gia_tri,
                                                             body.hien_thi_cho_khach))


class EditDimension(BaseModel):
    ten: Optional[str] = Field(default=None, max_length=80)
    hien_thi_cho_khach: Optional[bool] = None
    move: Optional[Literal["up", "down"]] = None


@app.patch("/taxonomy/{dim_id}")
def edit_dimension(dim_id: int, body: EditDimension, user=Depends(require(*APPROVERS))):
    """Rename, show/hide for visitors, move up/down; the code never changes."""
    return _tax_write(lambda c: taxonomy_admin.edit_dimension(c, user, dim_id, body.ten, body.hien_thi_cho_khach, body.move))


class NewValue(BaseModel):
    ten: str = Field(min_length=1, max_length=120)
    ma_dinh_danh: Optional[str] = Field(default=None, min_length=1, max_length=64)  # derived from ten when omitted
    mo_ta: Optional[str] = Field(default=None, max_length=500)
    tu_dong_nghia: list[str] = Field(default_factory=list)


@app.post("/taxonomy/{dim_id}/values", status_code=201)
def add_value(dim_id: int, body: NewValue, user=Depends(require(*APPROVERS))):
    return _tax_write(lambda c: taxonomy_admin.add_value(c, user, dim_id, body.ten, body.mo_ta, body.tu_dong_nghia,
                                                         body.ma_dinh_danh))


class EditValue(BaseModel):
    ten: Optional[str] = Field(default=None, max_length=120)
    mo_ta: Optional[str] = Field(default=None, max_length=500)
    tu_dong_nghia: Optional[list[str]] = None


@app.patch("/taxonomy/values/{value_id}")
def edit_value(value_id: int, body: EditValue, user=Depends(require(*APPROVERS))):
    """Rename keeps ma_dinh_danh, so facet URLs stay valid (seq-15 b13); also description and synonyms."""
    return _tax_write(lambda c: taxonomy_admin.edit_value(c, user, value_id, body.ten, body.mo_ta, body.tu_dong_nghia))


class MergeValue(BaseModel):
    target_id: int


@app.post("/taxonomy/values/{value_id}/merge")
def merge_value(value_id: int, body: MergeValue, user=Depends(require(*APPROVERS))):
    """Same dimension only; mirrored space columns move too; tong_mau never (seq-15 b16-22)."""
    return _tax_write(lambda c: taxonomy_admin.merge(c, user, value_id, body.target_id))


# ── Assistant knowledge (change: assistant-knowledge-admin; UC16, seq-16) ─────────────────────────────────────
KNOWLEDGE = ("content", *APPROVERS)


def _kn(call):
    """Run one knowledge write in a transaction and map its errors."""
    try:
        with _db() as c:
            return call(c)
    except knowledge.NotFound as e:
        raise HTTPException(404, str(e))
    except knowledge.Conflict as e:
        raise HTTPException(409, str(e))
    except knowledge.Forbidden as e:
        raise HTTPException(403, str(e))
    except knowledge.Invalid as e:
        raise HTTPException(422, str(e))


@app.get("/knowledge")
def knowledge_list(q: Optional[str] = Query(default=None, max_length=200),
                   trang_thai: Optional[Literal[knowledge.STATUSES]] = None, user=Depends(require(*KNOWLEDGE))):
    with _db() as c:
        return knowledge.list_entries(c, q, trang_thai)


@app.get("/knowledge/gaps")
def knowledge_gaps(user=Depends(require(*KNOWLEDGE))):
    """Questions the chatbot could not answer, still open, grouped and most asked first (seq-16 b1-6)."""
    with _db() as c:
        return knowledge.gaps(c)


class GapIds(BaseModel):
    ids: list[int] = Field(min_length=1, max_length=500)


@app.post("/knowledge/gaps/dismiss")
def knowledge_dismiss(body: GapIds, user=Depends(require(*KNOWLEDGE))):
    return {"bo_qua": _kn(lambda c: knowledge.dismiss_gaps(c, user, body.ids))}


@app.get("/knowledge/{entry_id}")
def knowledge_get(entry_id: int, user=Depends(require(*KNOWLEDGE))):
    return _kn(lambda c: knowledge.get(c, entry_id))


class NewEntry(BaseModel):
    kind: Literal[KB_KINDS]
    title: str = Field(min_length=1, max_length=200)
    cum_tu_khop: str = Field(min_length=1, max_length=500)
    content: str = Field(min_length=1, max_length=4000)
    trang_thai: Literal["nhap", "cho_duyet"] = "nhap"
    tu_cau_hoi: list[int] = Field(default_factory=list, max_length=500)  # the unanswered questions it answers


@app.post("/knowledge", status_code=201)
def knowledge_create(body: NewEntry, user=Depends(require(*KNOWLEDGE))):
    return _kn(lambda c: knowledge.create(c, user, body.kind, body.title, body.cum_tu_khop, body.content,
                                          body.trang_thai, body.tu_cau_hoi))


class EditEntry(BaseModel):
    kind: Optional[Literal[KB_KINDS]] = None
    title: Optional[str] = Field(default=None, max_length=200)
    cum_tu_khop: Optional[str] = Field(default=None, max_length=500)
    content: Optional[str] = Field(default=None, max_length=4000)


@app.patch("/knowledge/{entry_id}")
def knowledge_update(entry_id: int, body: EditEntry, user=Depends(require(*KNOWLEDGE))):
    """Re-embeds title and match phrases; a content editor's change to a live price entry sends it back for approval."""
    return _kn(lambda c: knowledge.update(c, user, entry_id, body.kind, body.title, body.cum_tu_khop, body.content))


class EntryStatus(BaseModel):
    trang_thai: Literal[knowledge.STATUSES]


@app.post("/knowledge/{entry_id}/status")
def knowledge_status(entry_id: int, body: EntryStatus, user=Depends(require(*KNOWLEDGE))):
    """Only the lead architect / admin switch on an entry that states prices (seq-16: price only after approval)."""
    return _kn(lambda c: knowledge.set_status(c, user, entry_id, body.trang_thai))


@app.delete("/knowledge/{entry_id}", status_code=204)
def knowledge_delete(entry_id: int, user=Depends(require(*APPROVERS))):
    _kn(lambda c: knowledge.delete(c, user, entry_id))


# ── Sitemap (seq-6 b18, roadmap 4.5; change topic-guard-sitemap-item-services) ─
SITEMAP_PAGES = ("", "du-an", "khong-gian", "uoc-tinh", "trac-nghiem", "lien-he", "ve-chung-toi")
SITEMAP_FOLDER = re.compile(r"^[a-z0-9_]{1,60}$")


@app.get("/sitemap.xml")
def sitemap(request: Request):
    """Public. Built from the database on every read, so a publish or a take-down shows at once: the public pages,
    each project with at least one published photo (its folder, '_' -> '-'), and each published photo. lastmod: the
    photo's latest review_log entry (space has no timestamp of its own; a photo with no log entry gets today)."""
    from xml.sax.saxutils import escape
    base = os.getenv("D3_FRONTEND_URL") or f"{request.url.scheme}://{request.headers.get('host', 'localhost')}/prj1/"
    base = base.rstrip("/") + "/"
    with _db() as c:
        rows = c.execute("SELECT s.id, s.relative_path, coalesce(max(r.at), now()) AS lastmod FROM space s "
                         "LEFT JOIN review_log r ON r.space_id = s.id WHERE s.review_status = 'published' "
                         "GROUP BY s.id ORDER BY s.id").fetchall()
    projects = {}
    for r in rows:
        folder = r["relative_path"].split("/")[0] if "/" in r["relative_path"] else None
        if folder and SITEMAP_FOLDER.match(folder):
            projects[folder] = max(projects.get(folder, r["lastmod"]), r["lastmod"])

    def url(path, lastmod=None):
        mod = f"<lastmod>{lastmod.date().isoformat()}</lastmod>" if lastmod else ""
        return f"<url><loc>{escape(base + path)}</loc>{mod}</url>"
    body = ([url(p) for p in SITEMAP_PAGES] + [url("du-an/" + f.replace("_", "-"), m) for f, m in sorted(projects.items())]
            + [url(f"khong-gian/{r['id']}", r["lastmod"]) for r in rows])
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + "\n".join(body) + "\n</urlset>\n")
    return Response(xml, media_type="application/xml", headers={"Cache-Control": "public, max-age=300"})


# ── Forbidden topics (seq-3 b15; change topic-guard-sitemap-item-services) ─────
class TopicIn(BaseModel):
    ten: Optional[str] = Field(default=None, max_length=200)
    tu_khoa: Optional[list[str]] = Field(default=None, max_length=100)
    ghi_chu: Optional[str] = Field(default=None, max_length=1000)
    bat: Optional[bool] = None


class TopicTry(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


def _tg(call):
    try:
        with _db() as c:
            return call(c)
    except topic_guard.Invalid as e:
        raise HTTPException(422, [{"loc": ["body", e.field], "msg": e.msg, "type": "value_error"}])
    except topic_guard.Conflict as e:
        raise HTTPException(409, {"msg": str(e), "existing": e.existing})
    except topic_guard.NotFound:
        raise HTTPException(404, "no such topic")


@app.get("/forbidden-topics")
def topics_list(user=Depends(require(*KNOWLEDGE))):
    return _tg(topic_guard.list_all)


@app.post("/forbidden-topics/try")
def topics_try(body: TopicTry, user=Depends(require(*KNOWLEDGE))):
    """Which switched-on topic a sample sentence hits, and through which keyword; the assistant is not asked."""
    return {"trung": _tg(lambda c: topic_guard.check(c, body.text))}


@app.post("/forbidden-topics", status_code=201)
def topics_create(body: TopicIn, user=Depends(require(*KNOWLEDGE))):
    return _tg(lambda c: topic_guard.create(c, body.model_dump(exclude_unset=True), user["id"]))


@app.patch("/forbidden-topics/{topic_id}")
def topics_update(topic_id: int, body: TopicIn, user=Depends(require(*KNOWLEDGE))):
    return _tg(lambda c: topic_guard.update(c, topic_id, body.model_dump(exclude_unset=True), user["id"]))


@app.delete("/forbidden-topics/{topic_id}", status_code=204)
def topics_delete(topic_id: int, user=Depends(require(*APPROVERS))):
    """Content staff switch a topic off instead."""
    _tg(lambda c: topic_guard.delete(c, topic_id))


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
        # review-tag-autocomplete: words reviewers typed that no value covers, with the photos waiting on "Other"
        values = c.execute("SELECT id, ten_de_xuat, bang_chung, created_at, updated_at FROM ung_vien_phan_loai "
                           "WHERE loai = 'gia_tri' AND trang_thai = 'cho_duyet' ORDER BY created_at").fetchall()
        for v in values:
            v["cho"] = c.execute("SELECT id, relative_path, space_type, design_style, caption FROM space WHERE id = ANY(%s) ORDER BY id",
                                 (v["bang_chung"].get("space_ids", []),)).fetchall()
    return {"candidates": rows, "cho_bang_chung": waiting, "gia_tri": values}


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


class AcceptValue(BaseModel):
    ten: str = Field(min_length=1, max_length=80)
    mo_ta: Optional[str] = Field(default=None, max_length=1000)
    tu_dong_nghia: list[str] = Field(default_factory=list, max_length=30)


class MapValue(BaseModel):
    gia_tri_id: int


@app.post("/taxonomy/value-candidates/{cid}/accept", status_code=201)
def accept_value_candidate(cid: int, body: AcceptValue, user=Depends(require(*APPROVERS))):
    """A reviewer's word becomes a value; the photos waiting on "Other" for it move to it (review-tag-autocomplete)."""
    return _tax_write(lambda c: value_suggest.accept(c, user, cid, body.ten, body.mo_ta, body.tu_dong_nghia))


@app.post("/taxonomy/value-candidates/{cid}/map")
def map_value_candidate(cid: int, body: MapValue, user=Depends(require(*APPROVERS))):
    """The word means an existing value: it is added as that value's synonym and the waiting photos get the value."""
    return _tax_write(lambda c: value_suggest.map_to(c, user, cid, body.gia_tri_id))


@app.post("/taxonomy/value-candidates/{cid}/reject")
def reject_value_candidate(cid: int, user=Depends(require(*APPROVERS))):
    """No value; the waiting photos stay on "Other"."""
    return _tax_write(lambda c: value_suggest.reject(c, user, cid))


@app.post("/taxonomy/candidates/{cid}/reject")
def reject_candidate(cid: int, user=Depends(require(*APPROVERS))):
    with _db() as c:
        _pending(c, cid)
        c.execute("UPDATE ung_vien_phan_loai SET trang_thai='tu_choi', updated_at=now(), bang_chung = "
                  "COALESCE(bang_chung, '{}') || %s WHERE id=%s", (Jsonb({"nguoi_duyet": user["id"]}), cid))
    return {"id": cid, "trang_thai": "tu_choi"}
