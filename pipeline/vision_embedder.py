"""Vision Embedder using OpenCLIP SigLIP2 ViT-B/16 (multilingual, understands Vietnamese queries).

Extracts normalized 768-dimensional semantic feature vectors for M3 and M10.
Runs in FP16 on GPU keeping VRAM < 0.9 GB.
"""

from pathlib import Path
import time
from typing import List, Optional
from PIL import Image


class VisionEmbedder:
    def __init__(
        self,
        model_name: str = "hf-hub:timm/ViT-B-16-SigLIP2",
        pretrained: Optional[str] = None,
        device: Optional[str] = None,
    ):
        try:
            import torch
            if device is None:
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            else:
                self.device = device
        except ImportError:
            self.device = "cpu"

        self.model_name = model_name
        self.pretrained = pretrained
        self.model = None
        self.preprocess = None
        self._load_model()

    def _load_model(self):
        # No silent fallback: a failed load must fail ingest, never store fake vectors.
        import open_clip

        model, _, preprocess = open_clip.create_model_and_transforms(
            self.model_name,
            pretrained=self.pretrained,
            device=self.device,
        )
        model.eval()

        # Convert to FP16 on GPU
        if self.device == "cuda":
            model = model.half()

        self.model = model
        self.preprocess = preprocess
        print(f"[INFO] VisionEmbedder loaded {self.model_name} ({self.pretrained}) on {self.device}")

    def embed_image(self, image_path: str | Path) -> List[float]:
        """Generate a 768-dim normalized feature vector from image."""
        import torch

        img = Image.open(image_path).convert("RGB")
        image_tensor = self.preprocess(img).unsqueeze(0).to(self.device)
        if self.device == "cuda":
            image_tensor = image_tensor.half()

        with torch.no_grad():
            features = self.model.encode_image(image_tensor)
            features /= features.norm(dim=-1, keepdim=True)  # L2 normalize
            vector = features.squeeze(0).cpu().float().numpy().tolist()

        if self.device == "cuda":
            torch.cuda.empty_cache()

        return vector

    def embed_text(self, text: str) -> List[float]:
        """768-dim normalized text vector, same space as embed_image. Vietnamese works."""
        import open_clip
        import torch

        tokens = open_clip.get_tokenizer(self.model_name)([text]).to(self.device)
        with torch.no_grad():
            f = self.model.encode_text(tokens).float()
            f /= f.norm(dim=-1, keepdim=True)
        return f.squeeze(0).cpu().tolist()
