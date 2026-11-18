"""Task queue and its single worker (labelling-queue-feedback; seq-1 "Hàng đợi xử lí ảnh").

Uploads are queued as one task per photo and answered at once; one worker thread takes the tasks in order, so the
GPU models are never used by two jobs at the same time (GPU_LOCK is shared with anything else that runs them).
The queue lives in Postgres (hang_doi_tac_vu), so a restart resumes it. Each `loai` has a handler in HANDLERS:
other changes register theirs (e.g. loading a published photo into the assistant's knowledge).
"""

import logging
import threading
from pathlib import Path

import psycopg
from psycopg.rows import dict_row, tuple_row
from psycopg.types.json import Jsonb

from pipeline.store import DSN

log = logging.getLogger("d3.intake")
GPU_LOCK = threading.Lock()
IMG_DIR = Path("image_d3")
MAX_TRIES = 2  # a task interrupted twice (the server died while running it) is marked failed, so it can't loop
IDLE_SECONDS = 2
HANDLERS = {}  # loai -> fn(conn, task, ctx) -> space_id | None; raising marks the task failed with the message


def handler(loai):
    def register(fn):
        HANDLERS[loai] = fn
        return fn
    return register


def enqueue(conn, loai: str, du_lieu: dict, nguoi_id: int | None = None) -> int:
    if loai not in HANDLERS:
        raise ValueError(f"no handler for task kind {loai!r}")
    return conn.cursor(row_factory=tuple_row).execute(  # callers may hand over a dict_row connection
        "INSERT INTO hang_doi_tac_vu (loai, du_lieu, nguoi_id) VALUES (%s, %s, %s) RETURNING id",
        (loai, Jsonb(du_lieu), nguoi_id)).fetchone()[0]


CLAIM = """
UPDATE hang_doi_tac_vu SET trang_thai = 'dang_xu_ly', so_lan = so_lan + 1, bat_dau_luc = now()
 WHERE id = (SELECT id FROM hang_doi_tac_vu WHERE trang_thai = 'cho' AND loai = ANY(%s)
               ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED)
RETURNING id, loai, du_lieu, nguoi_id, so_lan"""


def claim(conn) -> dict | None:
    """The oldest waiting task of a kind this process can run, marked running. Two workers never get the same one
    (SKIP LOCKED), and a worker never takes a kind it has no handler for (e.g. the tests' own kinds)."""
    return conn.cursor(row_factory=dict_row).execute(CLAIM, (list(HANDLERS),)).fetchone()


def process_next(ctx: dict) -> int | None:
    """Claim and run one task; returns its id, or None when the queue is empty. ctx is handed to the handler."""
    with psycopg.connect(DSN, autocommit=True) as conn:
        task = claim(conn)
        if task is None:
            return None
        try:
            fn = HANDLERS.get(task["loai"])
            if fn is None:
                raise RuntimeError(f"không có bộ xử lý cho loại tác vụ {task['loai']}")
            space_id = fn(conn, task, ctx)
            conn.execute("UPDATE hang_doi_tac_vu SET trang_thai = 'xong', space_id = %s, xong_luc = now(), loi = NULL "
                         "WHERE id = %s", (space_id, task["id"]))
        except Exception as e:  # one bad photo must not stop the queue
            log.exception("task %s (%s) failed", task["id"], task["loai"])
            conn.execute("UPDATE hang_doi_tac_vu SET trang_thai = 'loi', loi = %s, xong_luc = now() WHERE id = %s",
                         (f"{type(e).__name__}: {e}"[:300], task["id"]))
        return task["id"]


def recover(conn) -> tuple[int, int]:
    """At startup: tasks left running by a dead server go back to the queue once; a second interruption fails them."""
    again = conn.cursor().execute("UPDATE hang_doi_tac_vu SET trang_thai = 'cho' WHERE trang_thai = 'dang_xu_ly' "
                         "AND so_lan < %s", (MAX_TRIES,)).rowcount
    failed = conn.execute("UPDATE hang_doi_tac_vu SET trang_thai = 'loi', loi = 'bị gián đoạn hai lần', "
                          "xong_luc = now() WHERE trang_thai = 'dang_xu_ly'").rowcount
    return again, failed


def status(conn, ids: list[int]) -> list[dict]:
    rows = conn.cursor(row_factory=dict_row).execute(
        "SELECT id, trang_thai, space_id, loi, du_lieu->>'relative_path' AS relative_path FROM hang_doi_tac_vu "
        "WHERE id = ANY(%s) ORDER BY id", (ids,)).fetchall()
    return [{**r, "trang_thai": "dang_xu_ly" if r["trang_thai"] == "cho" else r["trang_thai"]} for r in rows]


@handler("xu_ly_anh")
def process_photo(conn, task, ctx):
    """seq-1 steps 7-15: classify, palette, detect, embed, save the draft with its proposed labels, index the vector."""
    from pipeline.store import save_records
    rel = task["du_lieu"]["relative_path"]
    path = ctx.get("img_dir", IMG_DIR) / rel
    if not path.is_file():
        raise FileNotFoundError(f"không thấy tệp {rel}")
    with GPU_LOCK:
        rec = ctx["processor"]().process_image(path, base_dir=ctx.get("img_dir", IMG_DIR))
    save_records([rec])
    space_id = conn.cursor(row_factory=tuple_row).execute("SELECT id FROM space WHERE relative_path = %s",
                                                          (rec.relative_path,)).fetchone()[0]
    conn.execute("INSERT INTO review_log (space_id, user_id, action, detail) VALUES (%s, %s, 'ingest', %s)",
                 (space_id, task["nguoi_id"], Jsonb({"relative_path": rec.relative_path, "tac_vu": task["id"]})))
    for after in ctx.get("after_photo", ()):  # e.g. image sizes (publishing-workflow)
        after(conn, space_id, path)
    return space_id


class Worker(threading.Thread):
    """The single queue worker. Started in the API lifespan (never under pytest)."""

    def __init__(self, ctx: dict):
        super().__init__(name="d3-intake", daemon=True)
        self.ctx, self.stop = ctx, threading.Event()

    def run(self):
        try:
            with psycopg.connect(DSN, autocommit=True) as conn:
                again, failed = recover(conn)
            if again or failed:
                log.info("queue recovered: %d task(s) requeued, %d failed", again, failed)
        except Exception:
            log.exception("queue recovery failed")
        while not self.stop.is_set():
            try:
                if process_next(self.ctx) is None:
                    self.stop.wait(IDLE_SECONDS)
            except Exception:  # e.g. the database restarting: wait and try again
                log.exception("queue worker error")
                self.stop.wait(5)
