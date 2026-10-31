## Context

D3 Studio sở hữu thư viện hình ảnh công trình và thiết kế lớn (đang lưu trữ tại `image_d3/` với các thư mục như `Indochine`, `hanjadin`, `luxury`, `modern`, `wallnut`, `working_space`). Theo Slide 05 và Slide 10, để website hoạt động như một cảm biến thu thập thị hiếu khách hàng (Trục 3) và cung cấp bộ lọc đa chiều (Trục 2), toàn bộ dữ liệu ảnh phải được cấu trúc hoá ở cấp độ **`Space` (Không gian)** chứ không thể gán phẳng ở cấp độ `Project` (Dự án).

Về mặt hạ tầng, máy trạm phát triển sở hữu card đồ họa **NVIDIA GeForce RTX 3050 Laptop (4GB VRAM)** chạy trên Windows. Do Desktop Window Manager (DWM) của Windows chiếm trước ~500MB VRAM, dung lượng khả dụng cho mô hình Deep Learning chỉ còn khoảng 3.3GB – 3.5GB. Thiết kế kiến trúc bắt buộc phải tính toán chuẩn xác footprint bộ nhớ để đảm bảo tính ổn định tuyệt đối.

## Goals / Non-Goals

**Goals:**
- Thiết kế luồng tiền xử lý (Stage 1) kết hợp giữa CPU và GPU, giữ mức đỉnh VRAM $\le 2.2$ GB.
- Trích xuất định lượng 5 màu chủ đạo (Hex palette) trong không gian CIE-Lab, tính toán nhiệt độ màu và độ sáng mà không tốn VRAM.
- Phát hiện đồ vật nội thất bằng `YOLO-World-S` để tự động đề xuất Hotspots (`M7`) với thời gian phản hồi $< 30$ms/ảnh.
- Sinh vector đặc trưng đa phương thức 512 chiều bằng `OpenCLIP ViT-B/32` cho Vector Search (`M3`, `M10`).
- Tích hợp mô hình ngôn ngữ lớn (LLM/VLM) phân loại đa nhãn có căn cứ (Grounded Reasoning) và sinh siêu dữ liệu SEO (`NFR-07`).
- Thiết lập cơ chế kiểm duyệt Human-in-the-loop (M5) đảm bảo NFR-10 (độ chính xác $\ge 85\%$).

**Non-Goals:**
- Huấn luyện lại (training from scratch) các mô hình nền tảng thị giác lớn.
- Dựng ảnh 3D, AR, hoặc render thời gian thực.
- Tự động xuất bản ảnh ra public gallery mà không qua xác nhận của Kiến trúc sư.

## Decisions

### Quyết định 1: Gán nhãn ở cấp độ Không gian (`Space-level`) thay vì Dự án (`Project-level`)
* **Tại sao:** Một căn biệt thự có thể kết hợp nhiều không gian khác nhau (ví dụ: phòng ngủ phụ mang phong cách Japandi/Tối giản tông be sáng trong khi phòng khách mang phong cách Indochine gỗ sẫm - minh họa tại Slide 10). Gán nhãn cấp Project sẽ làm sai lệch hoàn toàn bộ lọc đa chiều và đề xuất tương tự.
* **Phương án thay thế đã loại bỏ:** Gán nhãn cấp Project (bị loại bỏ vì làm tê liệt logic lọc đa facet).

### Quyết định 2: Tách biệt trích xuất màu sắc bằng CV truyền thống (CIE-Lab K-Means) trên CPU
* **Tại sao:** K-Means trên CPU với OpenCV/scikit-learn tiêu tốn 0 MB VRAM, thời gian chạy chỉ ~40ms/ảnh, cho kết quả mã Hex và tỉ lệ % chính xác tuyệt đối về mặt vật lý điểm ảnh.
* **Phương án thay thế đã loại bỏ:** Nhờ LLM nhìn ảnh và đoán màu (kết quả không nhất quán, dễ sinh ảo giác và tốn chi phí token).

### Quyết định 3: Chọn `YOLO-World-S` (Open-Vocabulary) thay vì `Grounding DINO`
* **Tại sao:** `Grounding DINO Swin-B/L` yêu cầu từ 3.5GB đến 6GB VRAM, chắc chắn gây tràn bộ nhớ (CUDA OOM) trên RTX 3050 4GB. Ngược lại, `YOLO-World-S` chỉ chiếm ~1.2GB VRAM ở chế độ FP16, nhận diện tốt các từ khóa nội thất tùy chỉnh (`sofa`, `bed`, `pendant light`, `curtain`, `coffee table`).
* **Phương án thay thế đã loại bỏ:** Grounding DINO, DETR lớn.

### Quyết định 4: Chọn `OpenCLIP ViT-B/32` thay vì `ViT-L/14`
* **Tại sao:** `ViT-B/32` (vector 512 chiều) chỉ chiếm ~800MB VRAM ở chế độ FP16, tốc độ suy luận dưới 20ms/ảnh, độ chính xác tìm kiếm ảnh tương tự đã được kiểm chứng chuẩn công nghiệp và hoàn toàn vừa vặn trong ngân sách VRAM 4GB.

### Quyết định 5: Chiến lược Hybrid: Local Feature Extraction + Multimodal LLM Reasoning
* **Tại sao:** Dùng mô hình cục bộ nhanh, rẻ để bóc tách thông tin "thô" (màu sắc, đồ vật, vector embedding), sau đó truyền cấu trúc dữ liệu này kèm ảnh vào LLM để suy luận ngữ nghĩa cao cấp (phong cách, câu chuyện thiết kế, SEO). Dữ liệu Stage 1 đóng vai trò "mỏ neo sự thật" (ground truth evidence), triệt tiêu ảo giác của LLM.

## Architecture Diagram

```
[Ảnh thô từ image_d3/]
        │
        ├─▶ [1A. Color Engine - CPU] ──────▶ K-Means LAB (0 MB VRAM)
        │                                         │
        ├─▶ [1B. YOLO-World-S - GPU FP16] ──▶ Bounding Boxes (~1.2 GB VRAM)
        │                                         │
        ├─▶ [1C. OpenCLIP ViT-B/32 - GPU] ──▶ 512d Vector DB (~0.8 GB VRAM)
        │                                         │
        ▼                                         ▼
[Gói dữ liệu Feature JSON] ───────────────────────┤
        │                                         ▼
        └──────────────────────────────▶ [Stage 2: LLM / VLM Reasoning]
                                                  │
                                                  ▼
                                         [JSON Facet & SEO]
                                                  │
                                                  ▼
                                         [CMS Human-in-the-Loop]
```

## Risks / Trade-offs

- **[Nguy cơ tràn VRAM trên GPU 4GB]**  
  *Giảm thiểu:* Thiết lập pipeline chạy tuần tự: Giải phóng bộ nhớ đệm PyTorch (`torch.cuda.empty_cache()`) sau khi hoàn thành model YOLO trước khi gọi CLIP (nếu cần), hoặc duy trì cả 2 model dưới dạng persistent runtime với tổng bộ nhớ khóa cứng ở mức ~2.0GB. Đặt Batch size = 1 hoặc 2.
- **[Lệch màu khi load ảnh do bỏ qua ICC Profile (NFR-04)]**  
  *Giảm thiểu:* Sử dụng thư viện `Pillow` kết hợp `PIL.ImageCms` để chuyển đổi ảnh về không gian sRGB chuẩn trước khi phân tích màu, tránh dùng `cv2.imread` thuần tuý làm sai lệch kênh màu của các bản thiết kế 3D/nhiếp ảnh kiến trúc.
- **[Ảnh góc chụp rộng chứa nhiều không gian lồng nhau (Living + Dining)]**  
  *Giảm thiểu:* Cấu hình prompt LLM nhận diện không gian phức hợp, cho phép gán primary space và secondary space nếu tỉ lệ đồ vật của 2 khu vực ngang nhau.

## Open Questions

1. Cơ chế lưu trữ vector embedding: Sử dụng SQLite-vec, ChromaDB cục bộ, hay đẩy lên PostgreSQL (pgvector)?
2. Lựa chọn model LLM/VLM cho Stage 2: Sử dụng Google Gemini 1.5 Flash (tốc độ cao, chi phí thấp, hỗ trợ tiếng Việt rất tốt) hay Claude 3.5 Haiku/Sonnet?
