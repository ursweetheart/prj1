"""Pydantic schemas for Interior Preprocessing and Multi-Facet Classification."""

from typing import Dict, List, Literal, Optional, Tuple
from pydantic import BaseModel, Field
from pipeline.color_extractor import ColorAnalysisResult


class BoundingBox(BaseModel):
    x_min: float = Field(description="Normalized top-left x in [0, 1]")
    y_min: float = Field(description="Normalized top-left y in [0, 1]")
    x_max: float = Field(description="Normalized bottom-right x in [0, 1]")
    y_max: float = Field(description="Normalized bottom-right y in [0, 1]")


class DetectedFurniture(BaseModel):
    label: str = Field(description="English label of detected furniture")
    label_vi: Optional[str] = Field(default=None, description="Vietnamese translation")
    confidence: float = Field(description="Detection confidence score")
    bbox: BoundingBox
    hotspot_anchor: Tuple[float, float] = Field(description="(x, y) center normalized coordinate for M7 Hotspot")


class FurnitureDetectionResult(BaseModel):
    objects: List[DetectedFurniture]
    counts_by_category: Dict[str, int]
    inference_time_ms: float


class SpaceSEOMetadata(BaseModel):
    caption: str = Field(description="Descriptive caption of the space in Vietnamese (15-30 words)")
    alt_text: str = Field(description="Search-optimized Vietnamese alt text for image tag")


class SpaceClassificationResult(BaseModel):
    space_type: Literal[
        "phong_khach",
        "phong_ngu_master",
        "phong_ngu_phu",
        "bep_va_an",
        "phong_lam_viec",
        "sanh_thong_tang",
        "ban_cong",
        "phong_tam",
        "lounge_thuong_mai",
        "khac",
    ]
    space_type_label: Optional[str] = Field(default="Không gian nội thất")
    design_style: Literal[
        "Indochine",
        "Japandi",
        "Wabi_sabi",
        "Hien_dai",
        "Tan_co_dien",
        "Luxury",
        "Toi_gian",
        "Scandinavian",
        "Khac"
    ]
    design_style_confidence: float
    style_rationale: str = Field(description="Grounded explanation citing detected objects and color palette")
    materials: List[str] = Field(description="Main identified materials e.g. walnut wood, cane webbing, marble")
    materials_description: Optional[str] = Field(default="", description="Chi tiết mô tả và ứng dụng chất liệu trong không gian")
    seo_metadata: SpaceSEOMetadata
    review_status: Literal["draft", "in_review", "approved", "published"] = "draft"
    llm_usage: Optional["LLMUsage"] = None


class LLMUsage(BaseModel):
    model: str = "gemini-2.5-flash"
    prompt_tokens: int = 0
    candidate_tokens: int = 0
    total_tokens: int = 0
    image_tokens: int = 0
    text_tokens: int = 0
    thoughts_tokens: int = 0
    estimated_cost_usd: float = 0.0
    estimated_cost_vnd: float = 0.0


class SpaceRecord(BaseModel):
    """Unified Space-Level Record aggregating Stage 1 and Stage 2 outputs."""
    image_path: str
    image_name: str
    subfolder: Optional[str] = None
    relative_path: Optional[str] = None
    color_analysis: ColorAnalysisResult
    furniture_detection: FurnitureDetectionResult
    classification: Optional[SpaceClassificationResult] = None
    llm_usage: Optional[LLMUsage] = None
    embedding_dimension: int = 768
    embedding: Optional[List[float]] = Field(default=None, description="SigLIP2 vector stored in Postgres/pgvector")
