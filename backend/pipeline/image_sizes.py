"""Optimised copies of each photo (publishing-workflow; act-1 "tối ưu dung lượng, tạo các kích thước"; class-6 Anh
cac_kich_thuoc, chieu_rong, chieu_cao). WebP copies 480, 960 and 1600 px wide, never wider than the original, written
to image_d3/_kt/<width>/<relative_path>.webp so the /images mount serves them. The original is never touched.

    python -m pipeline.image_sizes --backfill     # every photo without copies
"""

import sys
from pathlib import Path

from PIL import Image, ImageOps
from psycopg.types.json import Jsonb

WIDTHS = (480, 960, 1600)
QUALITY = 80
IMG_DIR = Path("image_d3")
SUBDIR = "_kt"


def make(path: Path, relative_path: str, img_dir: Path = IMG_DIR) -> dict:
    """-> {"kich_thuoc": {"480": "_kt/480/<rel>.webp", ...}, "chieu_rong": w, "chieu_cao": h} (upright pixel size)."""
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)  # a phone photo shot upright stays upright
        w, h = im.size
        if im.mode not in ("RGB", "RGBA"):
            im = im.convert("RGB")
        out = {}
        for width in WIDTHS:
            if width >= w:
                continue
            rel = f"{SUBDIR}/{width}/{relative_path}.webp"
            dest = img_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            copy = im.copy()
            copy.thumbnail((width, 10 * width), Image.Resampling.LANCZOS)
            copy.save(dest, "WEBP", quality=QUALITY, method=4)
            out[str(width)] = rel
    return {"kich_thuoc": out, "chieu_rong": w, "chieu_cao": h}


def store(conn, space_id: int, sizes: dict):
    conn.execute("UPDATE space SET kich_thuoc = %s, chieu_rong = %s, chieu_cao = %s WHERE id = %s",
                 (Jsonb(sizes["kich_thuoc"]), sizes["chieu_rong"], sizes["chieu_cao"], space_id))


def after_photo(conn, space_id: int, path: Path):
    """Called by the upload queue once a photo is processed (pipeline/intake.py ctx['after_photo'])."""
    rel = path.relative_to(IMG_DIR).as_posix() if path.is_relative_to(IMG_DIR) else path.name
    store(conn, space_id, make(path, rel, IMG_DIR))


def backfill(conn, img_dir: Path = IMG_DIR) -> tuple[int, int]:
    done = missing = 0
    for sid, rel in conn.execute("SELECT id, relative_path FROM space WHERE kich_thuoc IS NULL ORDER BY id").fetchall():
        path = img_dir / rel
        if not path.is_file():
            missing += 1
            continue
        store(conn, sid, make(path, rel, img_dir))
        conn.commit()
        done += 1
    return done, missing


if __name__ == "__main__":
    import psycopg

    from pipeline.store import DSN
    if "--backfill" not in sys.argv:
        raise SystemExit(__doc__)
    with psycopg.connect(DSN) as c:
        done, missing = backfill(c)
    print(f"copies made for {done} photo(s); {missing} original file(s) not found")
