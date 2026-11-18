"""Cost estimate (UC10, seq-9, act-6): plain arithmetic on the price table D8 (`don_gia`), never a model call,
so the same input always gives the same range.

    item range = area x the item's VND/m² range for (building type, package)
    furniture  x (1 + ROOM_UPLIFT x (bedrooms - 2)) when there are more than 2 bedrooms
    total      = sum of the items

While any row used is a sample (`nguon = 'mau'`, D3 has no price list yet) the result says so (`mau: true`)."""

ITEMS = (("thiet_ke", "Thiết kế"), ("phan_tho", "Phần thô & cải tạo"), ("hoan_thien", "Hoàn thiện"), ("noi_that", "Nội thất"))
HOUSE_VI = {"can_ho": "Căn hộ / Chung cư", "nha_pho": "Nhà phố", "biet_thu": "Biệt thự", "van_phong": "Văn phòng",
            "thuong_mai": "Thương mại / Showroom"}
PACKAGE_VI = {"co_ban": "Cơ bản", "tieu_chuan": "Tiêu chuẩn", "cao_cap": "Cao cấp"}
ROOM_UPLIFT, BASE_ROOMS = 0.08, 2  # each bedroom above 2 adds 8% to furniture (a stated assumption, see the spec)
NOTICE = "Ước tính tham khảo, chưa phải báo giá."
SAMPLE_NOTICE = "Đơn giá mẫu, chưa phải báo giá của D3 Studio."


def compute(prices: dict, dien_tich: float, so_phong_ngu: int = 2) -> dict:
    """prices: {hang_muc: (gia_min, gia_max, nguon)} for one building type and package -> the estimate, VND as int."""
    uplift = 1 + ROOM_UPLIFT * max(0, so_phong_ngu - BASE_ROOMS)
    lines = []
    for code, name in ITEMS:
        lo, hi, _ = prices[code]
        k = uplift if code == "noi_that" else 1
        lines.append({"ma": code, "ten": name, "min": round(dien_tich * lo * k), "max": round(dien_tich * hi * k)})
    return {"tong": {"min": sum(l["min"] for l in lines), "max": sum(l["max"] for l in lines)},
            "hang_muc": lines, "mau": any(p[2] == "mau" for p in prices.values())}


def estimate(conn, loai_nha: str, dien_tich: float, so_phong_ngu: int, goi: str) -> dict:
    """Load the 4 rows for (building type, package) and compute. Works with tuple or dict rows."""
    rows = conn.execute("SELECT hang_muc, gia_min, gia_max, nguon FROM don_gia WHERE loai_nha = %s AND goi = %s",
                        (loai_nha, goi)).fetchall()
    prices = {}
    for r in rows:
        r = tuple(r.values()) if isinstance(r, dict) else r
        prices[r[0]] = (r[1], r[2], r[3])
    if len(prices) != len(ITEMS):
        raise LookupError(f"price table incomplete for {loai_nha}/{goi}")
    return compute(prices, dien_tich, so_phong_ngu)


def _num(x: float, decimals: int) -> str:
    s = f"{x:.{decimals}f}".rstrip("0").rstrip(".")
    return s.replace(".", ",")


def vnd(amount: int) -> str:
    """478_800_000 -> '478,8 triệu', 1_250_000_000 -> '1,25 tỷ' (Vietnamese decimal comma)."""
    if amount >= 1_000_000_000:
        return f"{_num(amount / 1_000_000_000, 2)} tỷ"
    if amount >= 1_000_000:
        return f"{_num(amount / 1_000_000, 1)} triệu"
    return f"{amount:,}".replace(",", ".") + " đồng"


def vnd_range(r: dict) -> str:
    return f"{vnd(r['min'])} – {vnd(r['max'])}"


def describe(dau_vao: dict) -> str:
    """'Căn hộ / Chung cư · 70 m² · 3 phòng ngủ · Tiêu chuẩn'"""
    return " · ".join([HOUSE_VI.get(dau_vao["loai_nha"], dau_vao["loai_nha"]), f"{dau_vao['dien_tich_m2']:g} m²",
                       f"{dau_vao['so_phong_ngu']} phòng ngủ", PACKAGE_VI.get(dau_vao["goi"], dau_vao["goi"])])


def text_lines(dau_vao: dict, ket_qua: dict) -> list[str]:
    """The estimate as plain-text lines for the emails."""
    lines = [describe(dau_vao), f"Tổng: {vnd_range(ket_qua['tong'])}"]
    lines += [f"  - {l['ten']}: {vnd_range(l)}" for l in ket_qua["hang_muc"]]
    lines.append(NOTICE)
    if ket_qua.get("mau"):
        lines.append(SAMPLE_NOTICE)
    return lines


# ── seq-9 b6-b7 / act-6 (visitor-touchpoints): real projects in the same budget range ─────────────────────────────
import re as _re

from psycopg.rows import dict_row as _dict_row

BUDGET_LABEL, FALLBACK_LABEL = "Dự án trong cùng khoảng ngân sách", "Cùng loại công trình (chưa có dữ liệu ngân sách)"
MILLION = 1_000_000


def budget_range(code: str | None) -> tuple[float, float] | None:
    """'duoi_300tr' -> (0, 300e6), '300tr_700tr' -> (300e6, 700e6), 'tren_1500tr' -> (1500e6, inf); else None."""
    if not code:
        return None
    if m := _re.fullmatch(r"duoi_(\d+)tr", code):
        return 0.0, int(m[1]) * MILLION
    if m := _re.fullmatch(r"(\d+)tr_(\d+)tr", code):
        return int(m[1]) * MILLION, int(m[2]) * MILLION
    if m := _re.fullmatch(r"tren_(\d+)tr", code):
        return int(m[1]) * MILLION, float("inf")
    return None


def budget_projects(conn, loai_nha: str, tong: dict, k: int = 3) -> dict:
    """Up to k published projects whose investment level overlaps [tong.min, tong.max], same building type first;
    when none overlaps, published projects of the same type under the fallback label."""
    from pipeline.project_filter import TYPE_TO_BUILDING
    rows = conn.cursor(row_factory=_dict_row).execute("""
        SELECT d.slug, d.ten, d.co_trang, d.loai, d.muc_dau_tu,
               (array_agg(s.id ORDER BY s.anh_trang COLLATE "C" NULLS LAST, s.id))[1] AS anh_id,
               (array_agg(s.relative_path ORDER BY s.anh_trang COLLATE "C" NULLS LAST, s.id))[1] AS anh_path
          FROM du_an d JOIN space s ON s.du_an_slug = d.slug AND s.review_status = 'published'
         GROUP BY d.slug ORDER BY d.thu_tu NULLS LAST, d.slug""").fetchall()
    card = lambda r: {"slug": r["slug"], "ten": r["ten"], "co_trang": r["co_trang"],  # noqa: E731
                      "anh": {"id": r["anh_id"], "relative_path": r["anh_path"]}}
    same = lambda r: TYPE_TO_BUILDING.get(r["loai"]) == loai_nha  # noqa: E731
    lo, hi = tong["min"], tong["max"]
    fits = [r for r in rows if (b := budget_range(r["muc_dau_tu"])) and b[0] <= hi and lo <= b[1]]
    if fits:
        return {"nhan": BUDGET_LABEL, "ds": [card(r) for r in sorted(fits, key=lambda r: not same(r))[:k]]}
    return {"nhan": FALLBACK_LABEL, "ds": [card(r) for r in rows if same(r)][:k]}
