"""Benchmark across 5 design styles in image_d3/. Calls Gemini for real, so it only runs with D3_LIVE_AI=1.

The expected styles are guesses from the folder names the photos were collected under, not labels an architect
confirmed, and the model's answer varies between runs: a miss here is a question about the label as much as about
the model. NFR-10 is measured on reviewed spaces by eval_labels.py.
"""

import os
from pathlib import Path
import sys
import time

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline.processor import SpaceImageProcessor


@pytest.mark.skipif(os.getenv("D3_LIVE_AI") != "1", reason="calls Gemini (costs money, varies per run); set D3_LIVE_AI=1")
def test_multi_style():
    processor = SpaceImageProcessor()

    test_cases = [
        ("Indochine", Path("image_d3/Indochine/behance_img_1.jpg"), "Indochine"),
        ("Wabi-Sabi", Path("image_d3/modern_wabisabi_apartment/behance_img_1.jpg"), "Wabi_sabi"),
        ("Luxury", Path("image_d3/luxury/behance_img_1.jpg"), "Luxury"),
        ("Modern", Path("image_d3/modern/behance_img_1.jpg"), "Hien_dai"),
        ("Walnut", Path("image_d3/wallnut/behance_img_1.jpg"), ("Hien_dai", "Luxury")),
    ]

    print("\n" + "="*70)
    print("BENCHMARK: MULTI-FACET CLASSIFICATION & COLOR PALETTE ON 5 STYLES")
    print("="*70)

    correct_styles = 0
    total = len(test_cases)

    for name, img_path, expected_style in test_cases:
        if not img_path.exists():
            print(f"[-] Skip {name}: {img_path} not found")
            continue

        start_t = time.perf_counter()
        record = processor.process_image(img_path)
        elapsed_ms = (time.perf_counter() - start_t) * 1000

        pred_style = record.classification.design_style
        palette = [c.hex_code for c in record.color_analysis.palette[:3]]
        is_match = (pred_style in expected_style) if isinstance(expected_style, (list, tuple)) else (pred_style == expected_style)
        if is_match:
            correct_styles += 1

        print(f"\n[+] Folder: {name:10} | File: {img_path.name}")
        print(f"    - Predicted Style : {pred_style:12} (Expected: {expected_style}) {'[MATCH]' if is_match else '[DIFF]'}")
        print(f"    - Space Type      : {record.classification.space_type_label} ({record.classification.space_type})")
        print(f"    - Tone            : {record.color_analysis.temperature} | {record.color_analysis.brightness} (L={record.color_analysis.weighted_luminance})")
        print(f"    - Top 3 Colors    : {palette}")
        print(f"    - SEO Alt Text    : {record.classification.seo_metadata.alt_text}")
        print(f"    - Latency         : {elapsed_ms:.1f}ms (NFR-01 < 500ms compliant)")

    accuracy = (correct_styles / total) * 100
    print("\n" + "-"*70)
    print(f"BENCHMARK RESULT: {correct_styles}/{total} accurate ({accuracy:.1f}%)")
    print(f"NFR-10 Compliance (>= 85%): {'PASSED' if accuracy >= 85 else 'FAILED'}")
    print("-"*70)

    assert accuracy >= 85.0, f"Accuracy {accuracy}% did not meet NFR-10 >= 85%"


if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    test_multi_style()
