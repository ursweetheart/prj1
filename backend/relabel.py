"""Re-run the AI classification on stored spaces without the GPU stages (palette and detections come from the DB).

    python relabel.py --dry-run
    python relabel.py [--limit N] [--workers 4]

Only drafts are touched: a label a human has reviewed is never overwritten. Every change is written to review_log
(action 'relabel', no user) so the previous AI label stays on record. A photo whose call fails, or that falls back to
the offline heuristic, keeps its old label.
"""

import argparse
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

from pipeline.color_extractor import ColorAnalysisResult
from pipeline.multimodal_classifier import MultimodalClassifier
from pipeline.schemas import FurnitureDetectionResult
from pipeline.store import DSN

IMG_DIR = Path("image_d3")
FIELDS = ("space_type", "design_style")


def classify(clf, row):
    sid, path, palette, hotspots = row[:4]
    res = clf.classify(IMG_DIR / path, ColorAnalysisResult.model_validate(palette),
                       FurnitureDetectionResult.model_validate(hotspots))
    if res.llm_usage is None:  # the heuristic fallback answered: it guesses from the folder name, so don't use it
        raise RuntimeError("model call failed (heuristic fallback)")
    return res


def summarize(pairs):
    """pairs: [(old: dict, new: dict)] -> {field: (unchanged, total)} and the most common changes."""
    same = {f: sum(o[f] == n[f] for o, n in pairs) for f in FIELDS}
    moves = Counter((f, o[f], n[f]) for o, n in pairs for f in FIELDS if o[f] != n[f])
    return {f: (same[f], len(pairs)) for f in FIELDS}, moves.most_common(8)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    with psycopg.connect(DSN) as conn:
        rows = conn.execute("SELECT id, relative_path, palette, hotspots, space_type, design_style FROM space "
                            "WHERE review_status = 'draft' ORDER BY id").fetchall()[: args.limit]
        print(f"{len(rows)} draft spaces to relabel")
        if args.dry_run:
            return
        clf = MultimodalClassifier()
        if not clf.sa_key_path:
            sys.exit("no Vertex service-account key: set GOOGLE_APPLICATION_CREDENTIALS or put sa-key.json in backend/")

        def work(row):
            try:
                return row, classify(clf, row), None
            except Exception as e:  # one bad photo must not lose the rest
                return row, None, f"{row[1]}: {e}"

        pairs, failed, tokens = [], [], [0, 0]
        with ThreadPoolExecutor(args.workers) as pool:
            for row, res, err in pool.map(work, rows):
                if err:
                    failed.append(err)
                    continue
                old = {"space_type": row[4], "design_style": row[5]}
                new = {"space_type": res.space_type, "design_style": res.design_style}
                conn.execute("UPDATE space SET space_type=%s, design_style=%s, style_confidence=%s, materials=%s, "
                             "caption=%s, alt_text=%s WHERE id=%s AND review_status='draft'",
                             (res.space_type, res.design_style, res.design_style_confidence, res.materials,
                              res.seo_metadata.caption, res.seo_metadata.alt_text, row[0]))
                if old != new:
                    conn.execute("INSERT INTO review_log (space_id, user_id, action, detail) VALUES (%s, NULL, 'relabel', %s)",
                                 (row[0], Jsonb({"from": old, "to": new})))
                conn.commit()
                pairs.append((old, new))
                tokens[0] += res.llm_usage.prompt_tokens
                tokens[1] += res.llm_usage.candidate_tokens

    kept, moves = summarize(pairs)
    print(f"relabelled {len(pairs)}, failed {len(failed)}; tokens {tokens[0]} in, {tokens[1]} out")
    for f, (same, total) in kept.items():
        print(f"  {f}: unchanged {same}/{total}")
    for (f, a, b), n in moves:
        print(f"  {n:3d} x {f}: {a} -> {b}")
    for f in failed:
        print("FAILED", f)


if __name__ == "__main__":
    main()
