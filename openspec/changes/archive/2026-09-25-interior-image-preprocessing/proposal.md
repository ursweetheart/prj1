## Why

Kho tài sản hình ảnh thiết kế và thi công của D3 Studio (trong thư mục `image_d3/`) hiện là dữ liệu phi cấu trúc, chưa được chuẩn hoá theo các chiều phân loại nội thất. Nhằm hiện thực hóa Trục 1 (Cấu trúc hóa dữ liệu ở cấp độ `Space`) theo yêu cầu tại Slide 05 và Slide 10, dự án cần một pipeline tiền xử lý ảnh hiệu năng cao, trích xuất bảng màu (palette), đồ vật nội thất (hotspot), và embedding đa phương thức, sau đó tích hợp mô hình ngôn ngữ lớn (LLM/VLM) để phân loại đa lớp (Multi-facet classification) tự động nhưng có kiểm soát chất lượng (Human-in-the-loop).

Hệ thống được thiết kế để chạy mượt mà ngay trên phần cứng hạn chế (GPU laptop RTX 3050 4GB VRAM) với mức tiêu thụ bộ nhớ dưới 2.5GB VRAM và chi phí API tối ưu.

## What Changes

- Xây dựng module tiền xử lý thị giác (Computer Vision Preprocessing Pipeline):
  - Chuẩn hoá ảnh và trích xuất bảng màu 5 màu (Color Palette) trong không gian CIE-Lab bằng K-Means (chạy CPU, 0 MB VRAM), xác định độ sáng và tính chất nhiệt độ màu (Ấm/Lạnh).
  - Tích hợp mô hình nhận diện đồ vật nhẹ `YOLO-World-S` chạy trên GPU (FP16, ~1.2GB VRAM) để phát hiện đồ nội thất chính (sofa, đèn, giường, bàn trà...) phục vụ tính năng Hotspot (M7).
  - Trích xuất vector đặc trưng ngữ nghĩa bằng `OpenCLIP ViT-B/32` (FP16, ~0.8GB VRAM) phục vụ tìm kiếm ảnh tương tự (M3) và Vector Index (M10).
- Xây dựng module tổng hợp và phân loại đa lớp (Multimodal Facet Classification):
  - Nhận đầu vào là ảnh và dữ liệu cấu trúc JSON từ bước tiền xử lý để suy luận phân loại 10+ facets (Không gian, Phong cách, Tông màu, Vật liệu...).
  - Sinh siêu dữ liệu SEO (Alt-text, caption mô tả không gian).
- Tích hợp giao diện kiểm duyệt (Human-in-the-loop CMS workflow) đáp ứng chỉ số chất lượng NFR-10 (độ chính xác $\ge 85\%$).

## Capabilities

### New Capabilities
- `image-feature-extraction`: Module trích xuất đặc trưng định lượng cục bộ (Color Palette, Bounding Boxes đồ nội thất, Vision Embedding) chạy an toàn trên GPU 4GB VRAM.
- `multimodal-facet-classifier`: Module tích hợp LLM/VLM phân loại đa chiều có cấu trúc (Structured JSON) theo taxonomy nội thất và cơ chế kiểm duyệt gợi ý tag cho KTS.

### Modified Capabilities
<!-- Không có capability nào trước đó bị thay đổi yêu cầu -->

## Impact

- **Phần cứng & Runtime:** Tối ưu hóa cho môi trường GPU 4GB VRAM (RTX 3050), PyTorch FP16, OpenCV, scikit-learn, Ultralytics YOLO-World, OpenCLIP.
- **Dữ liệu đầu vào:** Thư mục ảnh `D:\prj1\image_d3\` (gồm các thư mục phong cách `Indochine`, `hanjadin`, `luxury`, `modern`, `wallnut`, v.v.).
- **Dữ liệu đầu ra:** Metadata JSON có cấu trúc theo cấp `Space`, sẵn sàng nạp vào cơ sở dữ liệu CMS (M5), Vector DB (M10), và hiển thị ở bộ lọc đa chiều (M1).
