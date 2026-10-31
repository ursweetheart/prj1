"""Accuracy of the AI facet labels, measured on spaces a human has reviewed (advanced out of draft in /quan-tri).

The AI label is what ingest wrote: the `from` side of the first 'edit' in review_log, or the current label when
nobody edited it. The human label is the current one.   python eval_labels.py
"""
import sys

import psycopg

from pipeline.store import DSN

TARGET = 0.85  # NFR-10
MIN_SAMPLE = 30
FACETS = ("space_type", "design_style")

# Weak signal only: the folder names come from the search keywords the images were collected with.
FOLDER_STYLE = {"Indochine": {"Indochine"}, "indochine_chinosere_villa": {"Indochine"}, "luxury": {"Luxury"},
                "modern": {"Hien_dai"}, "modern_wabisabi_apartment": {"Wabi_sabi"}, "wallnut": {"Hien_dai", "Luxury"}}

SQL = """
SELECT s.relative_path, s.space_type, s.design_style,
       first_edit.detail->'from'->>'space_type', first_edit.detail->'from'->>'design_style'
FROM space s
LEFT JOIN LATERAL (SELECT detail FROM review_log WHERE space_id = s.id AND action = 'edit' ORDER BY id LIMIT 1) first_edit ON true
WHERE EXISTS (SELECT 1 FROM review_log WHERE space_id = s.id AND action = 'advance')
ORDER BY s.id"""


def compare(rows):
    """rows: (path, final_type, final_style, ai_type_if_edited, ai_style_if_edited) -> {facet: (correct, total)}, misses"""
    score = {f: [0, 0] for f in FACETS}
    misses = []
    for path, f_type, f_style, ai_type, ai_style in rows:
        for facet, final, ai in (("space_type", f_type, ai_type), ("design_style", f_style, ai_style)):
            ai = ai or final  # never edited: the reviewer accepted the AI label
            score[facet][1] += 1
            score[facet][0] += ai == final
            if ai != final:
                misses.append((path, facet, ai, final))
    return {f: tuple(v) for f, v in score.items()}, misses


def folder_check(paths_styles):
    known = [(p, s) for p, s in paths_styles if p.split("/")[0] in FOLDER_STYLE]
    return sum(s in FOLDER_STYLE[p.split("/")[0]] for p, s in known), len(known)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    with psycopg.connect(DSN) as c:
        rows = c.execute(SQL).fetchall()
        everything = c.execute("SELECT relative_path, design_style FROM space").fetchall()
    score, misses = compare(rows)
    n = len(rows)
    print(f"reviewed spaces: {n}" + (f"  (need at least {MIN_SAMPLE} for a number worth trusting)" if n < MIN_SAMPLE else ""))
    for f, (ok, total) in score.items():
        if total:
            print(f"  {f}: {ok}/{total} = {ok / total:.0%}  {'meets' if ok / total >= TARGET else 'BELOW'} the {TARGET:.0%} target")
    for path, facet, ai, final in misses:
        print(f"  fixed by a human: {path} {facet}: {ai} -> {final}")
    ok, total = folder_check(everything)
    print(f"\nindicative only (no human labels): {ok}/{total} = {ok / total:.0%} of images land in the style their folder name suggests")
