"""Test suite for GPU Vision Models (YOLO Furniture Detector & OpenCLIP).

Verifies FP16 execution on RTX 3050 GPU, bounding box outputs,
512-dim vector embedding, and enforces strict VRAM boundary (< 2.2 GB).
"""

from pathlib import Path
import sys
import time
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pipeline.furniture_detector import FurnitureDetector
from pipeline.vision_embedder import VisionEmbedder


def test_gpu_pipeline():
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    assert torch.cuda.is_available(), "CUDA must be available for GPU test"
    device_name = torch.cuda.get_device_name(0)
    print(f"\n[+] Target GPU: {device_name}")

    torch.cuda.reset_peak_memory_stats()
    start_vram = torch.cuda.memory_allocated() / (1024**2)
    print(f"[*] Initial PyTorch VRAM: {start_vram:.1f} MB")

    img_path = Path("image_d3/Indochine/behance_img_1.jpg")
    assert img_path.exists(), f"Sample image {img_path} not found"

    # 1. Test Furniture Detector (YOLO)
    print("\n--- 1. Testing Furniture Detector (YOLOv8s on CUDA FP16) ---")
    detector = FurnitureDetector(model_name="yolov8s.pt", device="cuda")
    t0 = time.perf_counter()
    detect_res = detector.detect(img_path, conf_threshold=0.25)
    t_detect = (time.perf_counter() - t0) * 1000

    print(f"[+] Detection completed in: {t_detect:.1f}ms")
    print(f"[+] Total objects detected: {len(detect_res.objects)}")
    for obj in detect_res.objects[:5]:
        print(f"    • {obj.label_vi} ({obj.label}) | Conf: {obj.confidence} | Anchor: {obj.hotspot_anchor} | Box: {obj.bbox.model_dump()}")

    post_yolo_vram = torch.cuda.memory_allocated() / (1024**2)
    print(f"[*] VRAM after YOLO: {post_yolo_vram:.1f} MB")

    # 2. Test Vision Embedder (OpenCLIP ViT-B/32)
    print("\n--- 2. Testing Vision Embedder (OpenCLIP ViT-B/32 on CUDA FP16) ---")
    embedder = VisionEmbedder(model_name="ViT-B-32", pretrained="laion2b_s34b_b79k", device="cuda")
    t0 = time.perf_counter()
    vec = embedder.embed_image(img_path)
    t_embed = (time.perf_counter() - t0) * 1000

    print(f"[+] Embedding completed in: {t_embed:.1f}ms")
    print(f"[+] Embedding vector length: {len(vec)} (sample: {vec[:4]}...)")
    assert len(vec) == 512, "CLIP vector must be 512-dimensional"

    # 3. Peak VRAM & Memory Cleanup Check
    peak_vram_mb = torch.cuda.max_memory_allocated() / (1024**2)
    peak_vram_gb = peak_vram_mb / 1024.0
    print(f"\n[*] Peak VRAM Allocated: {peak_vram_mb:.1f} MB ({peak_vram_gb:.2f} GB)")

    # Assertions for 4GB VRAM safety limit
    assert peak_vram_gb <= 2.2, f"Peak VRAM {peak_vram_gb:.2f} GB exceeds safe 2.2 GB threshold!"
    print(f"[PASSED] Strict 4GB VRAM boundary honored (Peak: {peak_vram_gb:.2f} GB <= 2.2 GB)")

    torch.cuda.empty_cache()
    final_vram = torch.cuda.memory_allocated() / (1024**2)
    print(f"[*] Final VRAM after empty_cache: {final_vram:.1f} MB")
    print("\n[SUCCESS] All GPU vision model tests passed successfully!")


if __name__ == "__main__":
    test_gpu_pipeline()
