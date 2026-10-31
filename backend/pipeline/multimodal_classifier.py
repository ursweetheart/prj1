"""Multimodal Reasoning & Multi-Facet Classifier.

Integrates Vision-Language LLM (e.g., Gemini 1.5 Flash) with grounded evidence
from Stage 1 (color palette, detected furniture, luminance/temperature) to
perform taxonomy-compliant classification and generate SEO metadata.
Includes offline heuristic classifier fallback when API key is not configured.
"""

import base64
import json
import os
from pathlib import Path
from typing import Optional
from pipeline.color_extractor import ColorAnalysisResult
from pipeline.schemas import (
    FurnitureDetectionResult,
    SpaceClassificationResult,
    SpaceSEOMetadata,
)

SYSTEM_PROMPT = """Bạn là chuyên gia thẩm định và phân loại kiến trúc nội thất cao cấp của D3 Studio.
Nhiệm vụ của bạn là phân tích ảnh không gian nội thất kết hợp với các dữ liệu đặc trưng đã trích xuất (Bảng màu, Đồ vật nội thất phát hiện được) để gán nhãn đa chiều (Multi-facet) CHUẨN XÁC theo cây taxonomy của D3 Studio:

1. KHÔNG GIAN (space_type):
   - phong_khach, phong_ngu_master, phong_ngu_phu, bep_va_an, phong_lam_viec, sanh_thong_tang, ban_cong, phong_tam, lounge_thuong_mai, khac.

2. PHONG CÁCH CHÍNH (design_style):
   - Indochine: Đậm nét Á Đông, hoa văn kỷ hà, tranh sen/áo dài, gốm sứ, gỗ tự nhiên sẫm màu, mây tre đan.
   - Japandi: Kết hợp Nhật Bản và Bắc Âu, gỗ sáng, đường nét thanh mảnh, bình dị, thanh tịnh.
   - Wabi_sabi: Thô mộc tự nhiên, tường vôi/sơn hiệu ứng be/xám, đồ thủ công, bất toàn, tối giản.
   - Hien_dai: Tinh gọn, công năng, kính phẳng, kim loại, bề mặt bóng mờ, đèn led định hình.
   - Tan_co_dien: Phào chỉ tường, đèn chùm pha lê, bàn ghế uốn lượn mềm mại, sang trọng quý phái.
   - Luxury: Đá cẩm thạch bóng, kim loại mạ vàng/titan, da cao cấp, kính khói, ánh sáng đa tầng lộng lẫy.
   - Toi_gian: Hạn chế tối đa chi tiết thừa, mảng khối lớn, màu sắc trung tính nhẹ nhàng.
   - Scandinavian: Tông trắng/xám sáng, gỗ sồi sáng, ấm cúng (hygge), vải dệt thô.

3. VẬT LIỆU CHỦ ĐẠO & MÔ TẢ CHẤT LIỆU (materials & materials_description):
   - materials: Danh sách 2-5 vật liệu chính nhìn thấy trong ảnh.
   - materials_description: Đoạn văn tiếng Việt (40-80 từ) phân tích chuyên sâu về cách các chất liệu (gỗ tự nhiên, đá marble, mây tre đan, da, kim loại mạ, vải dệt, kính...) được ứng dụng, hoàn thiện bề mặt và phối hợp để tôn vinh vẻ đẹp của không gian.

4. SEO METADATA:
   - alt_text: Tiếng Việt, ngắn gọn, cấu trúc '[Không gian] phong cách [Phong cách] [Vật liệu chính] D3 Studio'.
   - caption: 15-30 từ tiếng Việt mô tả cảm xúc và điểm nhấn thiết kế của không gian.

BẮT BUỘC trả về đúng định dạng JSON tuân thủ schema, không thêm text giải thích ngoài JSON.
"""


def build_evidence_prompt(
    color_res: ColorAnalysisResult,
    furniture_res: FurnitureDetectionResult,
    folder_context: Optional[str] = None,
) -> str:
    palette_str = ", ".join([f"{c.hex_code} ({c.percentage}%)" for c in color_res.palette])
    objects_str = ", ".join(
        [f"{label}: {count}" for label, count in furniture_res.counts_by_category.items()]
    ) or "Không phát hiện rõ đồ vật lớn"

    context_hint = f"\nGợi ý ngữ cảnh thư mục: {folder_context}" if folder_context else ""

    prompt = f"""Dữ liệu định lượng trích xuất từ ảnh:
- Bảng màu chủ đạo (5 cụm K-Means): {palette_str}
- Tông màu: {color_res.temperature} (Nhiệt độ) | {color_res.brightness} (Độ sáng, L={color_res.weighted_luminance})
- Đồ nội thất phát hiện: {objects_str}{context_hint}

Hãy dựa vào ảnh và dữ liệu bằng chứng trên để phân loại không gian theo định dạng JSON sau:
{{
  "space_type": "...",
  "space_type_label": "...",
  "design_style": "...",
  "design_style_confidence": 0.95,
  "style_rationale": "Giải thích cụ thể vì sao chọn phong cách này...",
  "materials": ["gỗ óc chó", "đá cẩm thạch", "mây tre đan"],
  "materials_description": "Mô tả chi tiết và sâu sắc về các chất liệu được ứng dụng trong không gian...",
  "seo_metadata": {{
    "caption": "...",
    "alt_text": "..."
  }}
}}
"""
    return prompt


class MultimodalClassifier:
    def __init__(
        self,
        api_key: Optional[str] = None,
        sa_key_path: Optional[str | Path] = None,
        location: str = "asia-southeast1",
        model: str = "gemini-2.5-flash",
    ):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        
        # Check service account key for Vertex AI
        sa_candidate = (
            sa_key_path
            or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            or os.getenv("VERTEX_SA_KEY")
            or "sa-key.json"
        )
        self.sa_key_path = Path(sa_candidate) if sa_candidate and Path(sa_candidate).exists() else None
        self.location = location
        self.model = model
        self._credentials = None

    def _get_vertex_credentials(self):
        from google.oauth2 import service_account
        import google.auth.transport.requests

        if not self._credentials and self.sa_key_path:
            self._credentials = service_account.Credentials.from_service_account_file(
                str(self.sa_key_path),
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
        if self._credentials and not self._credentials.valid:
            self._credentials.refresh(google.auth.transport.requests.Request())
        return self._credentials

    def classify(
        self,
        image_path: str | Path,
        color_res: ColorAnalysisResult,
        furniture_res: FurnitureDetectionResult,
    ) -> SpaceClassificationResult:
        """Classify space using Vertex AI or Gemini VLM API, else fallback to grounded heuristic."""
        path_obj = Path(image_path)
        folder_name = path_obj.parent.name.lower()

        # The model sees only the photo and measured evidence. The folder name (a keyword the photos were collected
        # under) used to be passed too, which made labels echo the folder; only the offline heuristic still uses it.
        # 1. Try Vertex AI via Service Account key if available
        if self.sa_key_path:
            try:
                return self._call_vertex_ai(path_obj, color_res, furniture_res, None)
            except Exception as e:
                print(f"[WARN] Vertex AI call failed ({e}), attempting fallback.")

        # 2. Try Gemini API key if available
        if self.api_key:
            try:
                return self._call_vlm_api(path_obj, color_res, furniture_res, None)
            except Exception as e:
                print(f"[WARN] VLM API call failed ({e}), falling back to grounded heuristic.")

        # 3. Fallback grounded heuristic
        return self._heuristic_classify(path_obj, color_res, furniture_res, folder_name)
    @staticmethod
    def _prepare_image_payload(image_path: Path, max_dimension: int = 1280, quality: int = 85) -> tuple[str, str]:
        from PIL import Image
        import io

        with Image.open(image_path) as img:
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            w, h = img.size
            if max(w, h) > max_dimension:
                scale = max_dimension / max(w, h)
                new_size = (int(w * scale), int(h * scale))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality)
            b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            return b64, "image/jpeg"

    def _call_vertex_ai(
        self,
        image_path: Path,
        color_res: ColorAnalysisResult,
        furniture_res: FurnitureDetectionResult,
        folder_context: str,
    ) -> SpaceClassificationResult:
        import requests

        creds = self._get_vertex_credentials()
        b64_img, mime_type = self._prepare_image_payload(image_path)

        prompt = build_evidence_prompt(color_res, furniture_res, folder_context)
        url = f"https://{self.location}-aiplatform.googleapis.com/v1/projects/{creds.project_id}/locations/{self.location}/publishers/google/models/{self.model}:generateContent"

        headers = {
            "Authorization": f"Bearer {creds.token}",
            "Content-Type": "application/json",
        }

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": SYSTEM_PROMPT + "\n\n" + prompt},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": b64_img,
                            }
                        },
                    ],
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.2,
            },
        }

        import time
        last_ex = None
        for attempt in range(1, 4):
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=45)
                resp.raise_for_status()
                data = resp.json()
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
                result = self._clean_and_parse_json(raw_text)
                if "usageMetadata" in data:
                    result.llm_usage = self._compute_usage_cost(data["usageMetadata"], self.model)
                return result
            except Exception as ex:
                last_ex = ex
                if attempt < 3:
                    time.sleep(attempt * 2)
        raise last_ex

    def _call_vlm_api(
        self,
        image_path: Path,
        color_res: ColorAnalysisResult,
        furniture_res: FurnitureDetectionResult,
        folder_context: str,
    ) -> SpaceClassificationResult:
        import requests

        b64_img, mime_type = self._prepare_image_payload(image_path)

        prompt = build_evidence_prompt(color_res, furniture_res, folder_context)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": SYSTEM_PROMPT + "\n\n" + prompt},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": b64_img,
                            }
                        },
                    ],
                }
            ],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": 0.2,
            },
        }

        resp = requests.post(url, json=payload, timeout=25)
        resp.raise_for_status()
        data = resp.json()
        raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
        result = self._clean_and_parse_json(raw_text)
        if "usageMetadata" in data:
            result.llm_usage = self._compute_usage_cost(data["usageMetadata"], "gemini-1.5-flash")
        return result

    @staticmethod
    def _compute_usage_cost(usage_meta: dict, model_name: str = "gemini-2.5-flash"):
        from pipeline.schemas import LLMUsage

        prompt_tokens = usage_meta.get("promptTokenCount", 0)
        candidate_tokens = usage_meta.get("candidatesTokenCount", 0)
        total_tokens = usage_meta.get("totalTokenCount", prompt_tokens + candidate_tokens)
        thoughts_tokens = usage_meta.get("thoughtsTokenCount", 0)

        image_tokens = 0
        text_tokens = 0
        for detail in usage_meta.get("promptTokensDetails", []):
            if detail.get("modality") == "IMAGE":
                image_tokens += detail.get("tokenCount", 0)
            elif detail.get("modality") == "TEXT":
                text_tokens += detail.get("tokenCount", 0)

        # Standard Vertex AI Gemini Flash rate:
        # Prompt: $0.075 / 1M tokens ($0.000075 / 1k)
        # Candidate: $0.30 / 1M tokens ($0.000300 / 1k)
        cost_prompt = (prompt_tokens / 1_000_000.0) * 0.075
        cost_candidate = (candidate_tokens / 1_000_000.0) * 0.30
        total_usd = cost_prompt + cost_candidate
        total_vnd = total_usd * 25400.0

        return LLMUsage(
            model=model_name,
            prompt_tokens=prompt_tokens,
            candidate_tokens=candidate_tokens,
            total_tokens=total_tokens,
            image_tokens=image_tokens,
            text_tokens=text_tokens,
            thoughts_tokens=thoughts_tokens,
            estimated_cost_usd=round(total_usd, 6),
            estimated_cost_vnd=round(total_vnd, 2),
        )

    @staticmethod
    def _normalize_parsed_data(parsed: dict) -> dict:
        space_labels = {
            "phong_khach": "Phòng Khách",
            "phong_ngu_master": "Phòng Ngủ Master",
            "phong_ngu_phu": "Phòng Ngủ Phụ",
            "bep_va_an": "Phòng Bếp & Ăn",
            "phong_lam_viec": "Phòng Làm Việc",
            "sanh_thong_tang": "Sảnh Thông Tầng",
            "ban_cong": "Ban Công",
            "phong_tam": "Phòng Tắm",
            "lounge_thuong_mai": "Lounge Thương Mại",
            "khac": "Không gian khác",
        }
        style_map = {
            "indochine": "Indochine",
            "japandi": "Japandi",
            "wabi_sabi": "Wabi_sabi",
            "wabi-sabi": "Wabi_sabi",
            "wabisabi": "Wabi_sabi",
            "hien_dai": "Hien_dai",
            "hiendai": "Hien_dai",
            "modern": "Hien_dai",
            "tan_co_dien": "Tan_co_dien",
            "tancodien": "Tan_co_dien",
            "neo_classic": "Tan_co_dien",
            "luxury": "Luxury",
            "toi_gian": "Toi_gian",
            "toigian": "Toi_gian",
            "minimalism": "Toi_gian",
            "minimalist": "Toi_gian",
            "scandinavian": "Scandinavian",
        }
        st = str(parsed.get("space_type", "phong_khach")).lower().strip()
        if st not in space_labels:
            st = "phong_khach"
        parsed["space_type"] = st
        if not parsed.get("space_type_label"):
            parsed["space_type_label"] = space_labels.get(st, "Không gian nội thất")

        ds = str(parsed.get("design_style", "Hien_dai")).lower().strip()
        parsed["design_style"] = style_map.get(ds, "Hien_dai")

        try:
            parsed["design_style_confidence"] = float(parsed.get("design_style_confidence", 0.9))
        except Exception:
            parsed["design_style_confidence"] = 0.9

        if not isinstance(parsed.get("materials"), list):
            parsed["materials"] = ["Gỗ tự nhiên", "Vải dệt"]

        if not parsed.get("materials_description"):
            mat_str = ", ".join(parsed["materials"])
            parsed["materials_description"] = f"Không gian kết hợp hài hòa giữa các vật liệu chủ đạo gồm {mat_str}, tạo nên chiều sâu thẩm mỹ và sự tương phản tinh tế giữa các bề mặt hoàn thiện."

        if not isinstance(parsed.get("seo_metadata"), dict):
            parsed["seo_metadata"] = {
                "caption": f"Thiết kế không gian phong cách {parsed['design_style']} D3 Studio",
                "alt_text": f"Không gian nội thất phong cách {parsed['design_style']} D3 Studio",
            }
        return parsed

    def _clean_and_parse_json(self, raw_text: str) -> SpaceClassificationResult:
        clean = raw_text.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        if clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        clean = clean.strip()
        parsed = json.loads(clean)
        normalized = self._normalize_parsed_data(parsed)
        return SpaceClassificationResult(**normalized)

    def _heuristic_classify(
        self,
        image_path: Path,
        color_res: ColorAnalysisResult,
        furniture_res: FurnitureDetectionResult,
        folder_context: str,
    ) -> SpaceClassificationResult:
        """Deterministic grounded heuristic classifier based on folder name, objects, and color palette."""
        counts = furniture_res.counts_by_category

        # 1. Determine Space Type
        if "bed" in counts:
            space_type = "phong_ngu_master"
            space_label = "Phòng ngủ Master"
        elif "dining table" in counts or "chair" in counts and "sofa" not in counts:
            space_type = "bep_va_an"
            space_label = "Phòng Bếp & Ăn"
        elif "sofa" in counts or "coffee table" in counts:
            space_type = "phong_khach"
            space_label = "Phòng Khách"
        elif "desk" in counts or "working" in folder_context:
            space_type = "phong_lam_viec"
            space_label = "Phòng Làm Việc"
        else:
            space_type = "phong_khach"
            space_label = "Không gian sinh hoạt chung"

        # 2. Determine Design Style
        materials = ["Gỗ tự nhiên", "Vải dệt"]
        if "indochine" in folder_context or "chinosere" in folder_context:
            style = "Indochine"
            confidence = 0.94
            rationale = "Tông màu gỗ sẫm trầm ấm, chi tiết Á Đông kết hợp tranh nghệ thuật và nội thất hoài cổ."
            materials = ["Gỗ óc chó sẫm", "Mây tre đan", "Gốm hoa lam"]
        elif "hanjadin" in folder_context or "japandi" in folder_context:
            style = "Japandi"
            confidence = 0.91
            rationale = "Tông màu sáng ấm, đường nét tối giản thanh lịch của Bắc Âu giao thoa tinh thần mộc Nhật Bản."
            materials = ["Gỗ sồi sáng", "Vải thô linen", "Đất nung"]
        elif "wabisabi" in folder_context:
            style = "Wabi_sabi"
            confidence = 0.92
            rationale = "Màu sắc thô mộc, tường hiệu ứng và sự cân bằng tĩnh tại trong không gian tối giản."
            materials = ["Bê tông vi sinh / Sơn hiệu ứng", "Gỗ thô mộc", "Vải bố"]
        elif "luxury" in folder_context:
            style = "Luxury"
            confidence = 0.93
            rationale = "Đá cẩm thạch phản chiếu cao cấp, kính màu khói và đường viền kim loại ánh vàng sang trọng."
            materials = ["Đá Marble cao cấp", "Kính khói", "Kim loại mạ titan"]
        elif "wallnut" in folder_context:
            style = "Hien_dai"
            confidence = 0.89
            rationale = "Chủ đạo vật liệu gỗ óc chó tự nhiên phối hợp bố cục tinh gọn, ánh sáng phẳng hiện đại."
            materials = ["Gỗ óc chó tự nhiên", "Kính cường lực", "Da cao cấp"]
        else:
            style = "Hien_dai"
            confidence = 0.85
            rationale = "Đường nét vuông vắn, không gian mở và công năng hiện đại."
            materials = ["Gỗ công nghiệp cao cấp", "Kim loại sơn tĩnh điện"]

        # 3. Generate SEO Metadata
        caption = f"Thiết kế {space_label.lower()} phong cách {style} với tông {color_res.temperature} sang trọng, do D3 Studio thực hiện."
        alt_text = f"{space_label} phong cách {style} {materials[0].lower()} D3 Studio"
        mat_desc = f"Không gian sử dụng vật liệu chủ đạo gồm {', '.join(materials)}, hoàn thiện tinh tế làm nổi bật phong cách {style}."

        return SpaceClassificationResult(
            space_type=space_type,
            space_type_label=space_label,
            design_style=style,
            design_style_confidence=confidence,
            style_rationale=rationale,
            materials=materials,
            materials_description=mat_desc,
            seo_metadata=SpaceSEOMetadata(caption=caption, alt_text=alt_text),
            review_status="draft",
        )
