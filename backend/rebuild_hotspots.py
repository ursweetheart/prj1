"""Rebuild the AI hotspots of draft photos nobody has touched (change: hotspot-accuracy).

    python rebuild_hotspots.py --dry-run          # how many photos would change
    python rebuild_hotspots.py [--limit N] [--workers 4] [--include-published]
    python rebuild_hotspots.py --restore          # put back what a rebuild replaced (photos not edited since)

Untouched = draft (or published, with --include-published), no hand-made point, no point linked to an item, no hotspot edit in the review log, not rebuilt
before. The stored detector boxes are reused (no GPU); one Gemini call per photo names and points at the items, and
pipeline.hotspots.propose decides the final list. The previous objects go to review_log ('rebuild_hotspots'), so
--restore can undo it. A photo whose call fails keeps its hotspots.
"""

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

from pipeline.color_extractor import ColorAnalysisResult
from pipeline.hotspots import propose
from pipeline.schemas import DetectedFurniture, FurnitureDetectionResult
from pipeline.store import DSN

IMG_DIR = Path("image_d3")

UNTOUCHED = """
SELECT s.id, s.relative_path, s.palette, s.hotspots FROM space s
WHERE s.review_status = ANY(%(st)s) AND s.hotspots IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM jsonb_array_elements(COALESCE(s.hotspots->'objects', '[]')) o
                  WHERE o->>'nguon_tao' = 'thu_cong' OR o->>'mon_do_id' IS NOT NULL)
  AND NOT EXISTS (SELECT 1 FROM review_log l WHERE l.space_id = s.id AND (l.action = 'hotspots'
                  OR (l.action = 'rebuild_hotspots' AND NOT EXISTS (  -- a restored rebuild doesn't count
                      SELECT 1 FROM review_log m WHERE m.space_id = s.id AND m.id > l.id AND m.action = 'rebuild_hotspots_restore'))))
ORDER BY s.id"""


def untouched(conn, limit=None, statuses=("draft",)) -> list:
    rows = conn.execute(UNTOUCHED, {"st": list(statuses)}).fetchall()
    return rows[:limit] if limit else rows


def items_for(clf, row):
    """The classifier's items for a stored photo; raises when only the offline heuristic answered."""
    _, path, palette, hotspots = row
    res = clf.classify(IMG_DIR / path, ColorAnalysisResult.model_validate(palette),
                       FurnitureDetectionResult.model_validate(hotspots))
    if res.llm_usage is None:
        raise RuntimeError("model call failed (heuristic fallback)")
    return res.items


def write(conn, row, items, statuses=("draft",)) -> int:
    """Replace one draft's objects with the proposed ones and log the old ones. -> number of hotspots now."""
    sid, _, _, hotspots = row
    old = hotspots.get("objects", [])
    detected = [DetectedFurniture.model_validate(o) for o in old if o.get("bbox")]  # the stored detector boxes
    new = [o.model_dump() for o in propose(detected, items)]
    n = conn.execute("UPDATE space SET hotspots = jsonb_set(hotspots, '{objects}', %s) WHERE id = %s AND review_status = ANY(%s)",
                     (Jsonb(new), sid, list(statuses))).rowcount
    if n:
        conn.execute("INSERT INTO review_log (space_id, user_id, action, detail) VALUES (%s, NULL, 'rebuild_hotspots', %s)",
                     (sid, Jsonb({"truoc": old, "so_truoc": len(old), "so_sau": len(new)})))
    return len(new) if n else len(old)


def restore(conn, ids=None) -> int:
    """Put back the objects a rebuild replaced, for photos with no hotspot edit or restore since; only `ids` when given.
    -> photos restored."""
    rows = conn.execute("""
        SELECT l.id, l.space_id, l.detail->'truoc' FROM review_log l
        WHERE l.action = 'rebuild_hotspots' AND (%s::int[] IS NULL OR l.space_id = ANY(%s)) AND NOT EXISTS (
          SELECT 1 FROM review_log m WHERE m.space_id = l.space_id AND m.id > l.id
            AND m.action IN ('hotspots', 'rebuild_hotspots_restore'))""", (ids, ids)).fetchall()
    for log_id, sid, old in rows:
        conn.execute("UPDATE space SET hotspots = jsonb_set(hotspots, '{objects}', %s) WHERE id = %s", (Jsonb(old), sid))
        conn.execute("INSERT INTO review_log (space_id, user_id, action, detail) VALUES (%s, NULL, 'rebuild_hotspots_restore', %s)",
                     (sid, Jsonb({"tu_log": log_id})))
    return len(rows)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--restore", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--include-published", action="store_true", help="also untouched published photos (visitors see the change)")
    args = ap.parse_args()

    with psycopg.connect(DSN) as conn:
        if args.restore:
            print(f"restored {restore(conn)} photo(s)")
            return
        statuses = ("draft", "published") if args.include_published else ("draft",)
        rows = untouched(conn, args.limit, statuses)
        before = sum(len(r[3].get("objects", [])) for r in rows)
        print(f"{len(rows)} untouched photo(s), {before} hotspots now")
        if args.dry_run or not rows:
            return
        from pipeline.multimodal_classifier import MultimodalClassifier
        clf = MultimodalClassifier()
        if not clf.sa_key_path:
            sys.exit("no Vertex service-account key: set GOOGLE_APPLICATION_CREDENTIALS or put sa-key.json in backend/")

        def work(row):
            try:
                return row, items_for(clf, row), None
            except Exception as e:  # one bad photo must not lose the rest
                return row, None, f"{row[1]}: {e}"

        done, after, failed = 0, 0, []
        with ThreadPoolExecutor(args.workers) as pool:
            for row, items, err in pool.map(work, rows):
                if err:
                    failed.append(err)
                    continue
                after += write(conn, row, items, statuses)
                conn.commit()  # one photo per transaction
                done += 1
    print(f"rebuilt {done}, failed {len(failed)}; hotspots on rebuilt photos now {after}")
    for f in failed:
        print("FAILED", f)


if __name__ == "__main__":
    main()
