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
    # hotspot-accuracy: an item only the AI named has no detection box or confidence
    confidence: Optional[float] = Field(default=None, description="Detection confidence score")
    bbox: Optional[BoundingBox] = None
    hotspot_anchor: Tuple[float, float] = Field(description="(x, y) normalized point for M7 Hotspot")
    nguon_ai: Optional[Literal["yolo", "gemini", "ca_hai"]] = None  # which AI proposed it (absent: before hotspot-accuracy)


class AiItem(BaseModel):
    """An interior item the classifier named and pointed at (hotspot-accuracy)."""
    ten: str
    loai: str
    x: float  # 0-1, from the left
    y: float  # 0-1, from the top


class FurnitureDetectionResult(BaseModel):
    objects: List[DetectedFurniture]
    counts_by_category: Dict[str, int]
    inference_time_ms: float


class SpaceSEOMetadata(BaseModel):
    caption: str = Field(description="Descriptive caption of the space in Vietnamese (15-30 words)")
    alt_text: str = Field(description="Search-optimized Vietnamese alt text for image tag")


class SpaceClassificationResult(BaseModel):
    space_type: str = Field(description="khong_gian value code from the taxonomy tables")
    space_type_label: Optional[str] = Field(default="Không gian nội thất")
    design_style: str = Field(description="phong_cach value code from the taxonomy tables")
    design_style_confidence: float
    style_rationale: str = Field(description="Grounded explanation citing detected objects and color palette")
    materials: List[str] = Field(description="Main identified materials e.g. walnut wood, cane webbing, marble")
    materials_description: Optional[str] = Field(default="", description="Chi tiết mô tả và ứng dụng chất liệu trong không gian")
    seo_metadata: SpaceSEOMetadata
    review_status: Literal["draft", "in_review", "approved", "published"] = "draft"
    items: List[AiItem] = Field(default_factory=list)  # main interior items with a point on each (hotspot-accuracy)
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
