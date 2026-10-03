"""Unified Space Image Processor.

Coordinates Stage 1 (Color, Furniture/Hotspots, Vision Embedding)
and Stage 2 (Multimodal Classification & SEO generation).
Maintains sequential memory cleanup to respect 4GB GPU boundary.
"""

from pathlib import Path
import time
from typing import List, Optional
from pipeline.color_extractor import analyze_color_palette
from pipeline.furniture_detector import FurnitureDetector
from pipeline.multimodal_classifier import MultimodalClassifier
from pipeline.schemas import SpaceRecord
from pipeline.vision_embedder import VisionEmbedder


class SpaceImageProcessor:
    def __init__(
        self,
        model_yolo: str = "yolov8s.pt",
        clip_model: str = "ViT-B-32",
        device: Optional[str] = None,
    ):
        self.device = device
        self.color_engine = analyze_color_palette
        self.detector = FurnitureDetector(model_name=model_yolo, device=device)
        self.embedder = VisionEmbedder(model_name=clip_model, device=device)
        self.classifier = MultimodalClassifier()

    def process_image(self, image_path: str | Path, base_dir: Optional[Path] = None) -> SpaceRecord:
        path_obj = Path(image_path).resolve()
        if not path_obj.exists():
            raise FileNotFoundError(f"Image not found at {path_obj}")

        subfolder = path_obj.parent.name
        if base_dir:
            try:
                rel_path = str(path_obj.relative_to(base_dir)).replace("\\", "/")
            except ValueError:
                rel_path = f"{subfolder}/{path_obj.name}"
        else:
            rel_path = f"{subfolder}/{path_obj.name}"

        # 1A. Color Analysis (CPU)
        color_res = self.color_engine(path_obj, k=5)

        # 1B. Furniture Detection (GPU/CPU)
        furniture_res = self.detector.detect(path_obj)

        # 1C. Vision Embedding (GPU/CPU)
        embedding_vec = self.embedder.embed_image(path_obj)

        # Stage 2. Multimodal Classification & SEO
        classification = self.classifier.classify(
            path_obj,
            color_res=color_res,
            furniture_res=furniture_res,
        )

        return SpaceRecord(
            image_path=str(path_obj),
            image_name=path_obj.name,
            subfolder=subfolder,
            relative_path=rel_path,
            color_analysis=color_res,
            furniture_detection=furniture_res,
            classification=classification,
            llm_usage=classification.llm_usage if classification else None,
            embedding_dimension=len(embedding_vec),
            embedding=embedding_vec,
        )

    def process_directory(
        self,
        directory_path: str | Path,
        max_images: Optional[int] = None,
        recursive: bool = True,
        num_vlm_workers: int = 4,
    ) -> List[SpaceRecord]:
        from concurrent.futures import ThreadPoolExecutor, as_completed

        dir_obj = Path(directory_path).resolve()
        valid_exts = {".jpg", ".jpeg", ".png", ".webp"}

        if recursive:
            image_files = [f for f in sorted(dir_obj.rglob("*")) if f.is_file() and f.suffix.lower() in valid_exts]
        else:
            image_files = [f for f in sorted(dir_obj.iterdir()) if f.is_file() and f.suffix.lower() in valid_exts]

        if max_images:
            image_files = image_files[:max_images]

        total_imgs = len(image_files)
        print(f"[*] Found {total_imgs} images in '{dir_obj.name}' (recursive={recursive}).")
        if total_imgs == 0:
            return []

        # Order tracker to maintain correct sequence in final list
        file_order = {str(f.resolve()): i for i, f in enumerate(image_files)}
        processed_records: dict[int, SpaceRecord] = {}

        print(f"[*] Starting pipelined processing with {num_vlm_workers} VLM worker threads...")
        start_pipeline = time.perf_counter()

        with ThreadPoolExecutor(max_workers=num_vlm_workers) as executor:
            futures = {}

            # Stage 1: Sequential GPU/CPU feature extraction
            for idx, img_file in enumerate(image_files, 1):
                img_path = img_file.resolve()
                subfolder = img_path.parent.name
                try:
                    rel_path = str(img_path.relative_to(dir_obj)).replace("\\", "/")
                except ValueError:
                    rel_path = f"{subfolder}/{img_path.name}"

                t_s1 = time.perf_counter()
                color_res = self.color_engine(img_path, k=5)
                furniture_res = self.detector.detect(img_path)
                embedding_vec = self.embedder.embed_image(img_path)
                d_s1 = (time.perf_counter() - t_s1) * 1000

                order_idx = file_order[str(img_path)]
                print(f"    [{idx}/{total_imgs}] Stage 1 extracted ({d_s1:.0f}ms): {rel_path} -> Queued VLM call...")

                # Submit Stage 2 (Multimodal Classification) to worker thread pool
                future = executor.submit(
                    self.classifier.classify,
                    img_path,
                    color_res,
                    furniture_res,
                )
                futures[future] = (
                    order_idx,
                    img_path,
                    rel_path,
                    subfolder,
                    color_res,
                    furniture_res,
                    embedding_vec,
                )

            print(f"[*] All {total_imgs} images extracted through Stage 1. Waiting for VLM inference completion...")

            # Stage 2 completion listener
            completed_count = 0
            for future in as_completed(futures):
                (
                    order_idx,
                    img_path,
                    rel_path,
                    subfolder,
                    color_res,
                    furniture_res,
                    emb_vec,
                ) = futures[future]
                completed_count += 1

                try:
                    classification = future.result()
                except Exception as e:
                    print(f"[WARN] VLM failed for {rel_path}: {e}. Using heuristic fallback.")
                    classification = self.classifier._heuristic_classify(
                        img_path, color_res, furniture_res, subfolder.lower()
                    )

                u = classification.llm_usage if classification else None
                tok_str = f"{u.total_tokens} tokens (${u.estimated_cost_usd:.5f})" if u else "0 tokens"
                print(f"    [OK {completed_count}/{total_imgs}] {rel_path} -> {classification.space_type_label} | {classification.design_style} ({tok_str})")

                rec = SpaceRecord(
                    image_path=str(img_path),
                    image_name=img_path.name,
                    subfolder=subfolder,
                    relative_path=rel_path,
                    color_analysis=color_res,
                    furniture_detection=furniture_res,
                    classification=classification,
                    llm_usage=u,
                    embedding_dimension=len(emb_vec),
                    embedding=emb_vec,
                )
                processed_records[order_idx] = rec

        elapsed_total = time.perf_counter() - start_pipeline
        print(f"[+] Pipelined processing finished: {len(processed_records)}/{total_imgs} records in {elapsed_total:.1f}s")

        # Return sorted by original order
        return [processed_records[i] for i in sorted(processed_records.keys())]
