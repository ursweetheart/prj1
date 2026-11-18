"""publishing-workflow 5.1: optimised copies (act-1). Works on a temporary folder; the /images mount check uses one
real photo's copies made by the backfill."""
from pathlib import Path

from PIL import Image

from pipeline import image_sizes


def _photo(tmp_path, w, h, rotate=False):
    p = tmp_path / "p" / "a.jpg"
    p.parent.mkdir(parents=True, exist_ok=True)
    im = Image.new("RGB", (w, h), (200, 150, 100))
    exif = Image.Exif()
    if rotate:
        exif[0x0112] = 6  # shot rotated: the upright photo is h x w
    im.save(p, "JPEG", exif=exif.tobytes())
    return p


def test_widths_only_below_the_original(tmp_path):
    out = image_sizes.make(_photo(tmp_path, 4000, 3000), "p/a.jpg", tmp_path)
    assert (out["chieu_rong"], out["chieu_cao"]) == (4000, 3000) and sorted(out["kich_thuoc"], key=int) == ["480", "960", "1600"]
    with Image.open(tmp_path / out["kich_thuoc"]["960"]) as im:
        assert im.size == (960, 720) and im.format == "WEBP"
    small = image_sizes.make(_photo(tmp_path, 800, 600), "p/a.jpg", tmp_path)
    assert list(small["kich_thuoc"]) == ["480"]


def test_exif_rotation_is_respected(tmp_path):
    out = image_sizes.make(_photo(tmp_path, 3000, 2000, rotate=True), "p/a.jpg", tmp_path)
    assert (out["chieu_rong"], out["chieu_cao"]) == (2000, 3000)
    with Image.open(tmp_path / out["kich_thuoc"]["480"]) as im:
        assert im.size == (480, 720)


def test_original_untouched(tmp_path):
    p = _photo(tmp_path, 2000, 1000)
    before = p.read_bytes()
    image_sizes.make(p, "p/a.jpg", tmp_path)
    assert p.read_bytes() == before and Path(tmp_path / "_kt/480/p/a.jpg.webp").is_file()
