"""python ingest_projects.py [--dry-run] [slug ...] -> the site's project photos become draft spaces.

Reads ../src/assets/projects/<slug>/, copies each photo to image_d3/<folder>/ (folder = slug with '-' -> '_',
the rule the frontend uses to find a photo's space) and processes it. Photos already in the database are
skipped, so re-running never overwrites what staff edited. Nothing is published: do that in /quan-tri.
"""
import shutil
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src" / "assets" / "projects"
IMG_DIR = Path("image_d3")
IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".webp"}


def folder_of(slug: str) -> str:
    return slug.replace("-", "_")


def photos(slugs):
    dirs = [SRC / s for s in slugs] if slugs else sorted(p for p in SRC.iterdir() if p.is_dir())
    for d in dirs:
        if not d.is_dir():
            sys.exit(f"[!] no project folder {d}")
        for f in sorted(d.iterdir()):
            if f.suffix.lower() in IMAGE_TYPES:
                yield f, f"{folder_of(d.name)}/{f.name}"


def main(args):
    dry = "--dry-run" in args
    todo = list(photos([a for a in args if a != "--dry-run"]))
    if dry:
        print(f"[=] {len(todo)} photos in {len({rel.split('/')[0] for _, rel in todo})} folders")
        return

    import psycopg
    from pipeline.processor import SpaceImageProcessor
    from pipeline.store import DSN, save_records

    with psycopg.connect(DSN) as c:
        have = {r[0] for r in c.execute("SELECT relative_path FROM space").fetchall()}
    todo = [(f, rel) for f, rel in todo if rel not in have]
    print(f"[=] {len(todo)} new photos to process")
    if not todo:
        return
    processor = SpaceImageProcessor()  # loads YOLO + SigLIP2 once
    for i, (f, rel) in enumerate(todo, 1):
        dest = IMG_DIR / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, dest)
        save_records([processor.process_image(dest, base_dir=IMG_DIR)])  # one by one: an interrupted run resumes
        print(f"[{i}/{len(todo)}] {rel}")


if __name__ == "__main__":
    main(sys.argv[1:])
