"""Test suite for Color Extraction Engine."""

from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline.color_extractor import analyze_color_palette


def test_color_extraction():
    img_path = Path("D:/prj1/image_d3/Indochine/behance_img_1.jpg")
    assert img_path.exists(), f"Image not found at {img_path}"

    start_t = time.perf_counter()
    result = analyze_color_palette(img_path, k=5)
    elapsed = time.perf_counter() - start_t

    print("=== COLOR EXTRACTION RESULT ===")
    print(f"Processed in: {elapsed*1000:.1f}ms")
    print(f"Dominant Hex: {result.dominant_hex}")
    print(f"Brightness: {result.brightness} (Weighted Luminance: {result.weighted_luminance})")
    print(f"Temperature: {result.temperature}")
    print("Palette:")
    for cluster in result.palette:
        print(f"  • {cluster.hex_code} : {cluster.percentage}% | RGB: {cluster.rgb} | Lab: {cluster.lab}")

    # Assertions
    assert len(result.palette) == 5
    assert sum(c.percentage for c in result.palette) >= 99.0
    assert result.brightness in ["light", "dark", "balanced"]
    assert result.temperature in ["warm", "cool", "neutral"]
    print("\n[SUCCESS] Color extraction test passed!")


if __name__ == "__main__":
    test_color_extraction()
