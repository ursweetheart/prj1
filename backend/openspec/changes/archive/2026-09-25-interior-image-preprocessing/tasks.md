## 1. Environment & Preprocessing Engine Setup

- [x] 1.1 Khởi tạo cấu trúc thư mục pipeline và định nghĩa file phụ thuộc (`pipeline/`, `requirements.txt` gồm OpenCV, scikit-learn, Pillow, PyTorch FP16, OpenCLIP, Ultralytics)
- [x] 1.2 Xây dựng Color Extraction Engine (Pillow giữ ICC profile, chuyển đổi sang CIE-Lab, K-Means clustering $k=5$, xuất mã Hex và tỉ lệ %)
- [x] 1.3 Thêm logic tính toán độ sáng (`light`/`dark`) và nhiệt độ màu (`warm`/`cool`/`neutral`) từ bảng màu trích xuất
- [x] 1.4 Kiểm thử trích xuất màu trên ảnh mẫu `image_d3/Indochine/` đảm bảo chạy hoàn toàn trên CPU (0 MB VRAM)

## 2. Local Vision Models Integration (GPU Constrained)

- [x] 2.1 Cài đặt và cấu hình `YOLO-World-S` với tập nhãn nội thất tùy chỉnh (`sofa`, `table`, `chair`, `bed`, `pendant light`, `chandelier`, `wardrobe`, `curtain`, `vanity mirror`)
- [x] 2.2 Đóng gói hàm trích xuất Bounding Boxes chuẩn hoá `[x_min, y_min, x_max, y_max]` phục vụ Hotspot M7, đo đạc VRAM $\le 1.3$ GB
- [x] 2.3 Cài đặt và cấu hình `OpenCLIP ViT-B/32` (FP16), trích xuất vector nhúng 512 chiều từ ảnh, kiểm soát VRAM $\le 0.9$ GB
- [x] 2.4 Cài đặt cơ chế quản lý bộ nhớ tuần tự và `torch.cuda.empty_cache()` đảm bảo chạy liên tục hàng loạt ảnh mà đỉnh VRAM luôn $\le 2.2$ GB trên RTX 3050

## 3. Multimodal Reasoning & Multi-Facet Classifier

- [x] 3.1 Thiết kế Pydantic/JSON Schema chuẩn hoá đầu ra theo taxonomy thiết kế (`space_type`, `design_style`, `color_tone`, `materials`, `seo_metadata`)
- [x] 3.2 Xây dựng bộ prompt đa phương thức kết hợp ảnh gốc và metadata định lượng (màu sắc, đồ vật nhận diện) làm bằng chứng suy luận (grounding evidence)
- [x] 3.3 Tích hợp adapter gọi API mô hình ngôn ngữ lớn (LLM/VLM) có xử lý retry và parse JSON chặt chẽ
- [x] 3.4 Thử nghiệm phân loại trên 5 ảnh mẫu đại diện các phong cách khác nhau trong `image_d3/` (`Indochine`, `hanjadin`, `luxury`, `modern`, `wallnut`)

## 4. Pipeline Integration & Batch Runner

- [x] 4.1 Xây dựng CLI/Script tổng hợp `process_space_image.py` nhận đầu vào đường dẫn ảnh, xuất ra bản ghi cấu trúc cấp Không gian (`Space-level JSON record`)
- [x] 4.2 Viết script xử lý hàng loạt theo thư mục (Batch Processor) cho kho ảnh `image_d3/`
- [x] 4.3 Đối soát chất lượng đầu ra với tiêu chuẩn NFR-10 (độ chính xác $\ge 85\%$ ở nhãn Không gian và Phong cách) và NFR-12 (tốc độ xử lý)
