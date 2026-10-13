"""Color Extraction Engine for Interior Design Spaces.

Implements K-Means clustering in CIE-Lab color space with ICC profile preservation,
outputting hex palette, percentage distribution, brightness, and color temperature.
Runs entirely on CPU with 0 MB VRAM footprint.
"""

from pathlib import Path
from typing import List, Literal, Tuple
import cv2
import numpy as np
from PIL import Image, ImageCms
from pydantic import BaseModel, Field
from sklearn.cluster import MiniBatchKMeans


class ColorCluster(BaseModel):
    hex_code: str = Field(description="Hex color code, e.g., '#A48261'")
    percentage: float = Field(description="Percentage of pixels in this cluster (0-100)")
    rgb: Tuple[int, int, int]
    lab: Tuple[float, float, float]


class ColorAnalysisResult(BaseModel):
    palette: List[ColorCluster]
    dominant_hex: str
    brightness: Literal["light", "dark", "balanced"]
    temperature: Literal["warm", "cool", "neutral"]
    weighted_luminance: float


def load_image_srgb(image_path: str | Path, max_size: int = 400) -> np.ndarray:
    """Load image preserving ICC profile converted to standard sRGB, resized for fast processing."""
    img = Image.open(image_path)
    
    # Handle ICC Profile conversion if present
    if "icc_profile" in img.info:
        try:
            import io
            icc = io.BytesIO(img.info["icc_profile"])
            src_profile = ImageCms.ImageCmsProfile(icc)
            srgb_profile = ImageCms.createProfile("sRGB")
            img = ImageCms.profileToProfile(img, src_profile, srgb_profile, outputMode="RGB")
        except Exception:
            img = img.convert("RGB")
    else:
        img = img.convert("RGB")
    
    # Thumbnail resize for fast K-Means
    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    return np.array(img)


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Format RGB to #RRGGBB."""
    return f"#{int(r):02X}{int(g):02X}{int(b):02X}"


def analyze_color_palette(image_path: str | Path, k: int = 5) -> ColorAnalysisResult:
    """Extract dominant palette and lighting characteristics via K-Means in CIE-Lab."""
    rgb_arr = load_image_srgb(image_path)
    h, w, c = rgb_arr.shape
    pixels_rgb = rgb_arr.reshape(-1, 3)

    # Convert to CIE-Lab (OpenCV scales L: 0-255, a: 0-255, b: 0-255)
    lab_arr = cv2.cvtColor(rgb_arr, cv2.COLOR_RGB2LAB)
    pixels_lab = lab_arr.reshape(-1, 3)

    # Fit K-Means on CIE-Lab
    kmeans = MiniBatchKMeans(n_clusters=k, random_state=42, batch_size=2048, n_init=3)
    labels = kmeans.fit_predict(pixels_lab)
    cluster_centers_lab = kmeans.cluster_centers_

    # Calculate cluster percentages
    counts = np.bincount(labels, minlength=k)
    total_pixels = len(labels)
    percentages = (counts / total_pixels) * 100.0

    # Sort clusters by percentage descending
    sorted_indices = np.argsort(percentages)[::-1]

    clusters: List[ColorCluster] = []
    weighted_l_sum = 0.0
    weighted_b_sum = 0.0
    weighted_a_sum = 0.0

    for idx in sorted_indices:
        lab_val = cluster_centers_lab[idx]
        pct = float(percentages[idx])

        # Convert single LAB center back to RGB
        lab_pixel = np.uint8([[lab_val]])
        rgb_pixel = cv2.cvtColor(lab_pixel, cv2.COLOR_LAB2RGB)[0][0]
        r, g, b = int(rgb_pixel[0]), int(rgb_pixel[1]), int(rgb_pixel[2])
        hex_code = rgb_to_hex(r, g, b)

        # Standard CIE-Lab ranges: L in [0, 100], a, b roughly [-128, 127]
        # In OpenCV uint8: L_std = L_cv * 100 / 255; a_std = a_cv - 128; b_std = b_cv - 128
        l_std = float(lab_val[0] * 100.0 / 255.0)
        a_std = float(lab_val[1] - 128.0)
        b_std = float(lab_val[2] - 128.0)

        clusters.append(
            ColorCluster(
                hex_code=hex_code,
                percentage=round(pct, 2),
                rgb=(r, g, b),
                lab=(round(l_std, 2), round(a_std, 2), round(b_std, 2)),
            )
        )

        weighted_l_sum += l_std * (pct / 100.0)
        weighted_a_sum += a_std * (pct / 100.0)
        weighted_b_sum += b_std * (pct / 100.0)

    # 1. Determine brightness based on weighted Luminance (0-100)
    if weighted_l_sum >= 58.0:
        brightness: Literal["light", "dark", "balanced"] = "light"
    elif weighted_l_sum <= 38.0:
        brightness = "dark"
    else:
        brightness = "balanced"

    # 2. Determine color temperature based on weighted a* and b*
    # Warm: warm woods, creams, terracotta (positive b* yellow and positive a* red/warm)
    # Cool: bluish, slate grey, icy tones (negative b*)
    if weighted_b_sum > 6.0 or (weighted_a_sum > 4.0 and weighted_b_sum > 2.0):
        temperature: Literal["warm", "cool", "neutral"] = "warm"
    elif weighted_b_sum < -4.0:
        temperature = "cool"
    else:
        temperature = "neutral"

    return ColorAnalysisResult(
        palette=clusters,
        dominant_hex=clusters[0].hex_code,
        brightness=brightness,
        temperature=temperature,
        weighted_luminance=round(weighted_l_sum, 2),
    )
