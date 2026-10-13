#!/usr/bin/env python
"""CLI tool to process interior design images through the preprocessing and classification pipeline.

Usage:
    python process_space_image.py --image path/to/image.jpg [--output output.json]
    python process_space_image.py --dir path/to/folder [--output-dir outputs/] [--max 10]
"""

import argparse
import json
from pathlib import Path
import sys
import time

# Ensure project root is in sys.path and UTF-8 stdout
sys.path.insert(0, str(Path(__file__).resolve().parent))
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from pipeline.processor import SpaceImageProcessor


def main():
    parser = argparse.ArgumentParser(description="D3 Studio Space Image Preprocessor & Classifier")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--image", type=str, help="Path to a single interior image")
    group.add_argument("--dir", type=str, help="Path to a folder of interior images")

    parser.add_argument("--output", type=str, default=None, help="Output JSON path for single image")
    parser.add_argument("--output-dir", type=str, default="outputs", help="Output directory for batch processing")
    parser.add_argument("--max", type=int, default=None, help="Maximum images to process in directory")
    parser.add_argument("--workers", type=int, default=4, help="Concurrent VLM inference workers (default: 4)")
    parser.add_argument("--clean-output", action="store_true", help="Clean files in output directory before processing")

    args = parser.parse_args()
    processor = SpaceImageProcessor()

    if args.image:
        img_path = Path(args.image)
        print(f"[*] Processing image: {img_path.name}...")
        start_t = time.perf_counter()
        record = processor.process_image(img_path)
        elapsed = time.perf_counter() - start_t

        print(f"[+] Done in {elapsed*1000:.1f}ms")
        if record.classification:
            print(f"    - Space Type: {record.classification.space_type_label} ({record.classification.space_type})")
            print(f"    - Style: {record.classification.design_style} (Confidence: {record.classification.design_style_confidence})")
            print(f"    - Tone: {record.color_analysis.temperature} | {record.color_analysis.brightness}")
            print(f"    - Dominant Palette: {[c.hex_code for c in record.color_analysis.palette]}")
            print(f"    - Materials: {', '.join(record.classification.materials)}")
            print(f"    - Material Details: {record.classification.materials_description}")
            print(f"    - SEO Alt: {record.classification.seo_metadata.alt_text}")
            print(f"    - SEO Caption: {record.classification.seo_metadata.caption}")
            if record.llm_usage:
                u = record.llm_usage
                print(f"    - Quota/Usage: {u.total_tokens} tokens (Prompt: {u.prompt_tokens} [Img: {u.image_tokens}, Txt: {u.text_tokens}], Candidate: {u.candidate_tokens})")
                print(f"    - Cost: ${u.estimated_cost_usd:.6f} (~{u.estimated_cost_vnd:.1f} VND)")

        out_data = record.model_dump()
        if args.output:
            out_file = Path(args.output)
            out_file.parent.mkdir(parents=True, exist_ok=True)
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(out_data, f, ensure_ascii=False, indent=2)
            print(f"[*] Saved output to: {out_file}")

            # Also save dedicated cost JSON for single image if usage exists
            if record.llm_usage:
                cost_file = out_file.parent / f"{out_file.stem}_cost.json"
                with open(cost_file, "w", encoding="utf-8") as f:
                    json.dump(record.llm_usage.model_dump(), f, ensure_ascii=False, indent=2)
                print(f"[*] Saved cost report to: {cost_file}")
        else:
            print("\n--- JSON OUTPUT ---")
            print(json.dumps(out_data, ensure_ascii=False, indent=2))

    elif args.dir:
        dir_path = Path(args.dir)
        out_dir = Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        if args.clean_output:
            print(f"[*] Cleaning old files in {out_dir}...")
            for f in out_dir.iterdir():
                if f.is_file():
                    try:
                        f.unlink()
                    except PermissionError:
                        print(f"[WARN] Cannot delete locked file: {f.name}")

        print(f"[*] Processing directory: {dir_path} (max: {args.max}, workers: {args.workers})...")
        start_t = time.perf_counter()
        records = processor.process_directory(
            dir_path,
            max_images=args.max,
            recursive=True,
            num_vlm_workers=args.workers,
        )
        elapsed = time.perf_counter() - start_t

        export_batch_reports(records, out_dir, dir_path.name)

        print(f"\n[+] Batch complete: Processed {len(records)} images in {elapsed:.2f}s ({elapsed/max(1, len(records))*1000:.1f}ms/img)")
        print(f"[*] Outputs exported to: {out_dir}/")
        print(f"    - JSON database:    {dir_path.name}_summary.json")
        print(f"    - Excel/CSV:        {dir_path.name}_summary.csv")
        print(f"    - Markdown Doc:     {dir_path.name}_summary.md")
        print(f"    - Cost Report CSV:  {dir_path.name}_cost_report.csv")
        print(f"    - Cost Summary JSON:{dir_path.name}_cost_summary.json")


def safe_open_write(file_path: Path, encoding="utf-8", newline=None):
    try:
        return open(file_path, "w", encoding=encoding, newline=newline), file_path
    except PermissionError:
        import time
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        alt_path = file_path.with_name(f"{file_path.stem}_{timestamp}{file_path.suffix}")
        print(f"[WARN] File '{file_path.name}' is currently locked (e.g., opened in Excel). Writing to '{alt_path.name}' instead.")
        return open(alt_path, "w", encoding=encoding, newline=newline), alt_path


def export_batch_reports(records, out_dir: Path, folder_name: str):
    import csv

    # 1. JSON (Structured database format)
    json_path = out_dir / f"{folder_name}_summary.json"
    f, json_path = safe_open_write(json_path, encoding="utf-8")
    with f:
        json.dump([r.model_dump() for r in records], f, ensure_ascii=False, indent=2)

    # 2. Comprehensive CSV (Excel compatible with UTF-8 BOM)
    csv_path = out_dir / f"{folder_name}_summary.csv"
    f, csv_path = safe_open_write(csv_path, encoding="utf-8-sig", newline="")
    with f:
        writer = csv.writer(f)
        writer.writerow([
            "STT",
            "Dự Án / Thư Mục",
            "Tên File",
            "Đường Dẫn Tương Đối",
            "Không Gian (Phân Loại)",
            "Mã Không Gian",
            "Phong Cách",
            "Độ Tin Cậy",
            "Nhiệt Độ Màu",
            "Độ Sáng",
            "Màu Chủ Đạo",
            "Bảng Màu (Top 3)",
            "Đồ Nội Thất Phát Hiện",
            "Vật Liệu Chủ Đạo",
            "Mô Tả Chi Tiết Chất Liệu",
            "Prompt Tokens",
            "Candidate Tokens",
            "Total Tokens",
            "Chi Phí USD ($)",
            "Chi Phí VND (đ)",
            "SEO Alt Text",
            "SEO Caption",
            "Lý Do Phân Loại"
        ])
        for idx, r in enumerate(records, 1):
            top3 = ", ".join([f"{c.hex_code} ({c.percentage:.1f}%)" for c in r.color_analysis.palette[:3]])
            objs = ", ".join([f"{k}: {v}" for k, v in r.furniture_detection.counts_by_category.items()]) or "Không rõ"
            cls = r.classification
            u = r.llm_usage or (cls.llm_usage if cls else None)

            writer.writerow([
                idx,
                r.subfolder or "",
                r.image_name,
                r.relative_path or r.image_name,
                cls.space_type_label if cls else "",
                cls.space_type if cls else "",
                cls.design_style if cls else "",
                f"{cls.design_style_confidence:.2f}" if cls else "",
                r.color_analysis.temperature,
                r.color_analysis.brightness,
                r.color_analysis.dominant_hex,
                top3,
                objs,
                ", ".join(cls.materials) if cls else "",
                cls.materials_description if cls else "",
                u.prompt_tokens if u else 0,
                u.candidate_tokens if u else 0,
                u.total_tokens if u else 0,
                f"{u.estimated_cost_usd:.6f}" if u else "0.000000",
                f"{u.estimated_cost_vnd:.2f}" if u else "0.00",
                cls.seo_metadata.alt_text if cls else "",
                cls.seo_metadata.caption if cls else "",
                cls.style_rationale if cls else "",
            ])

    # 3. Dedicated Cost Report CSV
    cost_csv_path = out_dir / f"{folder_name}_cost_report.csv"
    f, cost_csv_path = safe_open_write(cost_csv_path, encoding="utf-8-sig", newline="")
    with f:
        writer = csv.writer(f)
        writer.writerow([
            "STT",
            "Dự Án / Thư Mục",
            "Tên File",
            "Đường Dẫn Tương Đối",
            "Model",
            "Image Tokens",
            "Text Tokens",
            "Prompt Tokens (Input)",
            "Candidate Tokens (Output)",
            "Total Tokens",
            "Chi Phí USD ($)",
            "Chi Phí VND (đ)"
        ])
        for idx, r in enumerate(records, 1):
            cls = r.classification
            u = r.llm_usage or (cls.llm_usage if cls else None)
            writer.writerow([
                idx,
                r.subfolder or "",
                r.image_name,
                r.relative_path or r.image_name,
                u.model if u else "N/A",
                u.image_tokens if u else 0,
                u.text_tokens if u else 0,
                u.prompt_tokens if u else 0,
                u.candidate_tokens if u else 0,
                u.total_tokens if u else 0,
                f"{u.estimated_cost_usd:.6f}" if u else "0.000000",
                f"{u.estimated_cost_vnd:.2f}" if u else "0.00",
            ])

    # 4. Dedicated Cost Summary JSON with Subfolder Breakdown
    total_prompt = sum((r.llm_usage.prompt_tokens if r.llm_usage else 0) for r in records)
    total_candidate = sum((r.llm_usage.candidate_tokens if r.llm_usage else 0) for r in records)
    total_tokens = sum((r.llm_usage.total_tokens if r.llm_usage else 0) for r in records)
    total_cost_usd = sum((r.llm_usage.estimated_cost_usd if r.llm_usage else 0.0) for r in records)
    total_cost_vnd = sum((r.llm_usage.estimated_cost_vnd if r.llm_usage else 0.0) for r in records)
    n = max(1, len(records))

    subfolder_stats = {}
    for r in records:
        sf = r.subfolder or "root"
        if sf not in subfolder_stats:
            subfolder_stats[sf] = {
                "count": 0,
                "prompt_tokens": 0,
                "candidate_tokens": 0,
                "total_tokens": 0,
                "cost_usd": 0.0,
                "cost_vnd": 0.0,
            }
        u = r.llm_usage
        subfolder_stats[sf]["count"] += 1
        if u:
            subfolder_stats[sf]["prompt_tokens"] += u.prompt_tokens
            subfolder_stats[sf]["candidate_tokens"] += u.candidate_tokens
            subfolder_stats[sf]["total_tokens"] += u.total_tokens
            subfolder_stats[sf]["cost_usd"] = round(subfolder_stats[sf]["cost_usd"] + u.estimated_cost_usd, 6)
            subfolder_stats[sf]["cost_vnd"] = round(subfolder_stats[sf]["cost_vnd"] + u.estimated_cost_vnd, 2)

    cost_summary = {
        "folder_name": folder_name,
        "total_images": len(records),
        "model": "gemini-2.5-flash",
        "pricing_basis": {
            "input_rate_per_1m_tokens_usd": 0.075,
            "output_rate_per_1m_tokens_usd": 0.30,
            "usd_to_vnd_exchange_rate": 25400
        },
        "totals": {
            "prompt_tokens": total_prompt,
            "candidate_tokens": total_candidate,
            "total_tokens": total_tokens,
            "total_cost_usd": round(total_cost_usd, 6),
            "total_cost_vnd": round(total_cost_vnd, 2),
        },
        "averages_per_image": {
            "prompt_tokens": round(total_prompt / n, 1),
            "candidate_tokens": round(total_candidate / n, 1),
            "total_tokens": round(total_tokens / n, 1),
            "cost_usd": round(total_cost_usd / n, 6),
            "cost_vnd": round(total_cost_vnd / n, 2),
        },
        "subfolder_breakdown": subfolder_stats,
        "per_image_costs": [
            {
                "subfolder": r.subfolder,
                "image_name": r.image_name,
                "relative_path": r.relative_path,
                "prompt_tokens": r.llm_usage.prompt_tokens if r.llm_usage else 0,
                "candidate_tokens": r.llm_usage.candidate_tokens if r.llm_usage else 0,
                "total_tokens": r.llm_usage.total_tokens if r.llm_usage else 0,
                "cost_usd": r.llm_usage.estimated_cost_usd if r.llm_usage else 0.0,
                "cost_vnd": r.llm_usage.estimated_cost_vnd if r.llm_usage else 0.0,
            }
            for r in records
        ]
    }
    cost_json_path = out_dir / f"{folder_name}_cost_summary.json"
    f, cost_json_path = safe_open_write(cost_json_path, encoding="utf-8")
    with f:
        json.dump(cost_summary, f, ensure_ascii=False, indent=2)

    # 5. Markdown Report
    md_path = out_dir / f"{folder_name}_summary.md"
    f, md_path = safe_open_write(md_path, encoding="utf-8")
    with f:
        f.write(f"# Báo Cáo Phân Tích Toàn Bộ Không Gian & Quota Chi Phí: `{folder_name}`\n\n")
        f.write(f"- **Tổng số ảnh đã xử lý**: **{len(records)} ảnh**\n")
        f.write(f"- **Số lượng thư mục / dự án con**: **{len(subfolder_stats)} dự án**\n")
        f.write(f"- **Mô hình VLM**: Vertex AI `gemini-2.5-flash` (Region: `asia-southeast1`)\n")
        f.write(f"- **Tổng Tokens tiêu thụ**: **{total_tokens:,} tokens**\n")
        f.write(f"- **Tổng Chi Phí Ước Tính**: **${total_cost_usd:.6f} USD** (~**{total_cost_vnd:.2f} VNĐ**)\n\n")

        f.write("## 1. Tổng Kết Chi Phí Theo Từng Thư Mục / Dự Án Con\n\n")
        f.write("| STT | Dự Án / Thư Mục | Số Lượng Ảnh | Prompt Tokens | Output Tokens | Tổng Tokens | Chi Phí (USD) | Chi Phí (VNĐ) |\n")
        f.write("| :-: | :--- | :-: | :-: | :-: | :-: | :-: | :-: |\n")
        for s_idx, (sf_name, sf_data) in enumerate(subfolder_stats.items(), 1):
            f.write(f"| {s_idx} | **{sf_name}** | {sf_data['count']} | {sf_data['prompt_tokens']:,} | {sf_data['candidate_tokens']:,} | {sf_data['total_tokens']:,} | ${sf_data['cost_usd']:.6f} | {sf_data['cost_vnd']:.2f} đ |\n")
        f.write(f"| **Tổng** | **{len(subfolder_stats)} dự án** | **{len(records)}** | **{total_prompt:,}** | **{total_candidate:,}** | **{total_tokens:,}** | **${total_cost_usd:.6f}** | **{total_cost_vnd:.2f} đ** |\n\n")

        f.write("## 2. Bảng Thống Kê Quota, Usage & Chi Phí Chi Tiết Từng Ảnh\n\n")
        f.write("| STT | Dự Án | Đường Dẫn Ảnh | Prompt Tokens | Output Tokens | Tổng Tokens | Chi Phí (USD) | Chi Phí (VNĐ) |\n")
        f.write("| :-: | :--- | :--- | :-: | :-: | :-: | :-: | :-: |\n")
        for idx, r in enumerate(records, 1):
            u = r.llm_usage or (r.classification.llm_usage if r.classification else None)
            p_tok = u.prompt_tokens if u else 0
            c_tok = u.candidate_tokens if u else 0
            t_tok = u.total_tokens if u else 0
            c_usd = f"${u.estimated_cost_usd:.6f}" if u else "$0.000000"
            c_vnd = f"{u.estimated_cost_vnd:.2f} đ" if u else "0.00 đ"
            r_path = r.relative_path or r.image_name
            f.write(f"| {idx} | `{r.subfolder}` | `{r_path}` | {p_tok:,} | {c_tok:,} | {t_tok:,} | {c_usd} | {c_vnd} |\n")
        f.write("\n")

        f.write("## 3. Bảng Tổng Hợp Nhận Diện Không Gian & Vật Liệu\n\n")
        f.write("| STT | Dự Án | Ảnh | Không Gian | Phong Cách | Bảng Màu (Top 3) | Vật Liệu Chính |\n")
        f.write("| :-: | :--- | :--- | :--- | :--- | :--- | :--- |\n")
        for idx, r in enumerate(records, 1):
            palette_str = " ".join([f"`{c.hex_code}`" for c in r.color_analysis.palette[:3]])
            cls = r.classification
            mat_str = ", ".join(cls.materials[:3]) if cls else "-"
            f.write(f"| {idx} | `{r.subfolder}` | `{r.image_name}` | **{cls.space_type_label}** | {cls.design_style} ({cls.design_style_confidence:.0%}) | {palette_str} | {mat_str} |\n")

        f.write("\n## 4. Chi Tiết Từng Không Gian & Mô Tả Chất Liệu Chuyên Sâu\n\n")
        current_sf = None
        for idx, r in enumerate(records, 1):
            if r.subfolder != current_sf:
                current_sf = r.subfolder
                f.write(f"\n### === Dự Án: `{current_sf}` ===\n\n")

            cls = r.classification
            u = r.llm_usage or (cls.llm_usage if cls else None)
            f.write(f"#### {idx}. `{r.relative_path}` - {cls.space_type_label}\n\n")
            f.write(f"- **Phong cách**: **{cls.design_style}** (Độ tin cậy: {cls.design_style_confidence:.0%})\n")
            f.write(f"- **Tông màu**: {r.color_analysis.temperature} | {r.color_analysis.brightness} (Độ sáng L={r.color_analysis.weighted_luminance})\n")
            f.write(f"- **Mã màu chính**: `{r.color_analysis.dominant_hex}` | Top 3: {', '.join([c.hex_code for c in r.color_analysis.palette[:3]])}\n")
            f.write(f"- **Danh sách vật liệu**: {', '.join(cls.materials)}\n")
            f.write(f"- **Mô tả chất liệu chi tiết**: {cls.materials_description}\n")
            f.write(f"- **Lý do chuyên gia**: {cls.style_rationale}\n")
            f.write(f"- **SEO Caption**: *\"{cls.seo_metadata.caption}\"*\n")
            f.write(f"- **SEO Alt Text**: `{cls.seo_metadata.alt_text}`\n")
            if u:
                f.write(f"- **Usage & Quota**: {u.total_tokens:,} tokens (Input: {u.prompt_tokens:,} [Image: {u.image_tokens:,}, Text: {u.text_tokens:,}], Output: {u.candidate_tokens:,}) | Chi phí: **${u.estimated_cost_usd:.6f}** (~**{u.estimated_cost_vnd:.2f} đ**)\n\n")
            else:
                f.write("\n")


if __name__ == "__main__":
    main()
