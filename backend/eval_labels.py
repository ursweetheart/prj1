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
SELECT s.relative_path, s.space_type, s.design_style, s.space_type_ai, s.design_style_ai,
       s.space_type_confidence, s.style_confidence
FROM space s
WHERE EXISTS (SELECT 1 FROM review_log WHERE space_id = s.id AND action = 'advance')
ORDER BY s.id"""
# labelling-queue-feedback (seq-1 b21): the AI's own proposal is kept in *_ai; the corrections are in nhan_bi_sua
CORRECTIONS = """
SELECT s.relative_path, f.chieu, f.ai_gia_tri, f.do_tin_cay, f.gia_tri_dung
FROM nhan_bi_sua f JOIN space s ON s.id = f.space_id
WHERE EXISTS (SELECT 1 FROM review_log WHERE space_id = s.id AND action = 'advance')
ORDER BY f.luc"""
BANDS = ((0.0, 0.5, "dưới 0.5"), (0.5, 0.7, "0.5–0.7"), (0.7, 0.9, "0.7–0.9"), (0.9, 1.01, "0.9 trở lên"))


def compare(rows):
    """rows: (path, final_type, final_style, ai_type, ai_style[, type_conf, style_conf]) -> {facet: (correct, total)}, misses
    An AI label of None (a photo from before the AI proposal was kept) counts as accepted."""
    score = {f: [0, 0] for f in FACETS}
    misses = []
    for path, f_type, f_style, ai_type, ai_style, *_ in rows:
        for facet, final, ai in (("space_type", f_type, ai_type), ("design_style", f_style, ai_style)):
            ai = ai or final
            score[facet][1] += 1
            score[facet][0] += ai == final
            if ai != final:
                misses.append((path, facet, ai, final))
    return {f: tuple(v) for f, v in score.items()}, misses


def by_band(rows):
    """Accuracy per confidence band: {facet: [(band, correct, total)]}; photos without a confidence are left out."""
    out = {}
    for facet, final_i, ai_i, conf_i in (("space_type", 1, 3, 5), ("design_style", 2, 4, 6)):
        out[facet] = []
        for lo, hi, name in BANDS:
            hit = [(r[ai_i] or r[final_i]) == r[final_i] for r in rows if r[conf_i] is not None and lo <= r[conf_i] < hi]
            out[facet].append((name, sum(hit), len(hit)))
    return out


def folder_check(paths_styles):
    known = [(p, s) for p, s in paths_styles if p.split("/")[0] in FOLDER_STYLE]
    return sum(s in FOLDER_STYLE[p.split("/")[0]] for p, s in known), len(known)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    with psycopg.connect(DSN) as c:
        rows = c.execute(SQL).fetchall()
        fixes = c.execute(CORRECTIONS).fetchall()
        everything = c.execute("SELECT relative_path, design_style FROM space").fetchall()
    score, misses = compare(rows)
    n = len(rows)
    print(f"reviewed spaces: {n}" + (f"  (need at least {MIN_SAMPLE} for a number worth trusting)" if n < MIN_SAMPLE else ""))
    for f, (ok, total) in score.items():
        if total:
            print(f"  {f}: {ok}/{total} = {ok / total:.0%}  {'meets' if ok / total >= TARGET else 'BELOW'} the {TARGET:.0%} target")
    for f, bands in by_band(rows).items():
        print(f"  {f} by AI confidence: " + ", ".join(f"{b} {ok}/{n}" + (f" = {ok / n:.0%}" if n else "") for b, ok, n in bands))
    print(f"corrections recorded (nhan_bi_sua): {len(fixes)}")
    for path, chieu, ai, conf, final in fixes:
        print(f"  {path} {chieu}: {ai}" + (f" ({conf:.0%})" if conf is not None else "") + f" -> {final}")
    ok, total = folder_check(everything)
    print(f"\nindicative only (no human labels): {ok}/{total} = {ok / total:.0%} of images land in the style their folder name suggests")
