"""Seed the taxonomy tables from kb/taxonomy_seed.json (idempotent).

    python seed_taxonomy.py            # load the default seed
    python seed_taxonomy.py other.json

Captures the taxonomy that used to live as Literal enums in pipeline/schemas.py and
the synonym dicts in pipeline/assistant.py, as data (change: discover-taxonomy-dimensions).
Safe to re-run: upserts by stable ma_dinh_danh.
"""

import json
import sys
from pathlib import Path

SEED = Path(__file__).with_name("kb") / "taxonomy_seed.json"


def load(path=SEED) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def check(data: dict) -> list[str]:
    """Internal consistency of the seed (no DB). Empty list = ok."""
    errors = []
    dims = {d["ma_dinh_danh"] for d in data["chieu"]}
    if len(dims) != len(data["chieu"]):
        errors.append("duplicate dimension ma_dinh_danh")
    seen = set()
    for v in data["gia_tri"]:
        key = (v["chieu"], v["ma_dinh_danh"])
        if v["chieu"] not in dims:
            errors.append(f"{key}: references unknown dimension")
        if key in seen:
            errors.append(f"{key}: duplicate value")
        seen.add(key)
        if not isinstance(v.get("tu_dong_nghia", []), list):
            errors.append(f"{key}: tu_dong_nghia must be a list")
    return errors


def seed(path=SEED) -> tuple[int, int]:
    import psycopg
    from psycopg.types.json import Jsonb
    from pipeline.store import DSN

    data = load(path)
    if errors := check(data):
        raise ValueError("taxonomy seed not loaded:\n  " + "\n  ".join(errors))
    with psycopg.connect(DSN) as c:
        for d in data["chieu"]:
            c.execute(
                "INSERT INTO chieu_phan_loai (ma_dinh_danh, ten, bat_buoc, cho_phep_nhieu_gia_tri, hien_thi_cho_khach, thu_tu) "
                "VALUES (%(ma_dinh_danh)s,%(ten)s,%(bat_buoc)s,%(cho_phep_nhieu_gia_tri)s,%(hien_thi_cho_khach)s,%(thu_tu)s) "
                "ON CONFLICT (ma_dinh_danh) DO UPDATE SET ten=EXCLUDED.ten, bat_buoc=EXCLUDED.bat_buoc, "
                "cho_phep_nhieu_gia_tri=EXCLUDED.cho_phep_nhieu_gia_tri, hien_thi_cho_khach=EXCLUDED.hien_thi_cho_khach, thu_tu=EXCLUDED.thu_tu",
                d)
        for v in data["gia_tri"]:
            c.execute(
                "INSERT INTO gia_tri_phan_loai (chieu_id, ma_dinh_danh, ten, tu_dong_nghia) "
                "SELECT id, %(ma)s, %(ten)s, %(syn)s FROM chieu_phan_loai WHERE ma_dinh_danh=%(chieu)s "
                "ON CONFLICT (chieu_id, ma_dinh_danh) DO UPDATE SET ten=EXCLUDED.ten, tu_dong_nghia=EXCLUDED.tu_dong_nghia",
                {"chieu": v["chieu"], "ma": v["ma_dinh_danh"], "ten": v["ten"], "syn": Jsonb(v.get("tu_dong_nghia", []))})
    return len(data["chieu"]), len(data["gia_tri"])


if __name__ == "__main__":
    dims, vals = seed(sys.argv[1] if len(sys.argv) > 1 else SEED)
    print(f"seeded {dims} dimensions, {vals} values")
