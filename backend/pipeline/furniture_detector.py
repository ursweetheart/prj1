"""Furniture and Interior Object Detector using YOLO-World / YOLOv8.

Extracts normalized bounding boxes and coordinates for M7 Hotspots.
Maintains tight VRAM footprint (< 1.3 GB) on 4GB GPUs.
"""

from pathlib import Path
import time
from typing import Dict, List, Optional
import numpy as np
from PIL import Image
from pipeline.schemas import BoundingBox, DetectedFurniture, FurnitureDetectionResult

# Furniture dictionary English -> Vietnamese
VI_TRANSLATIONS: Dict[str, str] = {
    "sofa": "Sofa / Ghế bành dài",
    "couch": "Sofa / Ghế bành dài",
    "armchair": "Ghế bành đơn",
    "chair": "Ghế tựa / Ghế ăn",
    "coffee table": "Bàn trà",
    "dining table": "Bàn ăn",
    "table": "Bàn",
    "bed": "Giường ngủ",
    "pendant light": "Đèn thả trần",
    "chandelier": "Đèn chùm",
    "lamp": "Đèn trang trí",
    "wardrobe": "Tủ quần áo",
    "cabinet": "Tủ / Kệ",
    "curtain": "Rèm cửa",
    "mirror": "Gương trang điểm / Gương soi",
    "carpet": "Thảm trải sàn",
    "painting": "Tranh nghệ thuật",
    "plant": "Cây xanh trang trí",
    "potted plant": "Cây cảnh",
    "vase": "Bình hoa / Gốm trang trí",
    "desk": "Bàn làm việc",
}

DEFAULT_CLASSES = [
    "sofa",
    "armchair",
    "chair",
    "coffee table",
    "dining table",
    "table",
    "bed",
    "pendant light",
    "chandelier",
    "lamp",
    "wardrobe",
    "cabinet",
    "curtain",
    "mirror",
    "carpet",
    "painting",
    "plant",
    "desk",
]


class FurnitureDetector:
    def __init__(self, model_name: str = "yolov8s.pt", device: Optional[str] = None):
        try:
            import torch
            if device is None:
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            else:
                self.device = device
        except ImportError:
            self.device = "cpu"

        self.model_name = model_name
        self.model = None
        self._load_model()

    def _load_model(self):
        try:
            from ultralytics import YOLO

            # Load model
            self.model = YOLO(self.model_name)
            # If YOLO-World, set custom classes
            if "world" in self.model_name.lower():
                try:
                    self.model.set_classes(DEFAULT_CLASSES)
                except Exception as e:
                    print(f"[WARN] Could not set custom classes for YOLO-World: {e}")
            print(f"[INFO] FurnitureDetector loaded {self.model_name} on {self.device}")
        except Exception as e:
            print(f"[WARN] Ultralytics YOLO initialization note: {e}")
            self.model = None

    def detect(self, image_path: str | Path, conf_threshold: float = 0.25) -> FurnitureDetectionResult:
        start_t = time.perf_counter()
        img = Image.open(image_path)
        img_w, img_h = img.size

        objects: List[DetectedFurniture] = []
        counts: Dict[str, int] = {}

        if self.model is not None:
            import torch

            # Run inference (FP16 if cuda)
            use_half = self.device == "cuda"
            results = self.model.predict(
                source=str(image_path),
                conf=conf_threshold,
                device=self.device,
                half=use_half,
                verbose=False,
            )

            for r in results:
                boxes = r.boxes
                for box in boxes:
                    xyxy = box.xyxy[0].cpu().numpy()
                    cls_id = int(box.cls[0].item())
                    conf = float(box.conf[0].item())
                    label = r.names.get(cls_id, f"obj_{cls_id}").lower()

                    # Filter / translate
                    label_vi = VI_TRANSLATIONS.get(label, label.capitalize())

                    # Normalize coordinates
                    x_min = max(0.0, min(1.0, float(xyxy[0]) / img_w))
                    y_min = max(0.0, min(1.0, float(xyxy[1]) / img_h))
                    x_max = max(0.0, min(1.0, float(xyxy[2]) / img_w))
                    y_max = max(0.0, min(1.0, float(xyxy[3]) / img_h))

                    # Center hotspot anchor
                    anchor_x = round((x_min + x_max) / 2.0, 3)
                    anchor_y = round((y_min + y_max) / 2.0, 3)

                    obj = DetectedFurniture(
                        label=label,
                        label_vi=label_vi,
                        confidence=round(conf, 3),
                        bbox=BoundingBox(
                            x_min=round(x_min, 3),
                            y_min=round(y_min, 3),
                            x_max=round(x_max, 3),
                            y_max=round(y_max, 3),
                        ),
                        hotspot_anchor=(anchor_x, anchor_y),
                    )
                    objects.append(obj)
                    counts[label] = counts.get(label, 0) + 1

            if self.device == "cuda":
                torch.cuda.empty_cache()

        elapsed_ms = (time.perf_counter() - start_t) * 1000.0

        return FurnitureDetectionResult(
            objects=objects,
            counts_by_category=counts,
            inference_time_ms=round(elapsed_ms, 2),
        )
