# KẾ HOẠCH LUỒNG AI — tối nay + 7 ngày tới

Nguồn: Drive `project 1` (seq-1 gán nhãn tự động, seq-2 tìm không gian tương tự, seq-3 hỏi đáp RAG; DFD 2.x; usecase 0/1/2) + code `pipeline/` + `openspec/specs/`.

## Hiện trạng (đã đối chiếu code)

| Seq | Luồng | Đã có | Còn thiếu |
|---|---|---|---|
| 1 | Gán nhãn tự động | `processor.py`: màu + YOLO + CLIP + Gemini classify → `SpaceRecord` (draft) | **Embedding bị bỏ** (chỉ lưu `embedding_dimension`); chưa ghi vào kho/chỉ mục; chưa có trạng thái duyệt (draft→in_review) |
| 2 | Tìm không gian tương tự | CLIP embedder | Vector index, lọc theo facet bắt buộc, trả điểm tương đồng + lý do |
| 3 | RAG trợ lý | Gemini classifier (tái dùng client) | Kho tri thức, embed câu hỏi, truy hồi lai (vector + facet), ngưỡng chống bịa, tạo lead |

Việc chặn mọi luồng: **embedding chưa được lưu**. Làm trước.

## TỐI NAY (≈3–4h) — mục tiêu: seq-1 chạy xuyên suốt và ra được chỉ mục

1. **Dựng Postgres + pgvector (30')** — Docker `pgvector/pgvector:pg16`, `docker-compose.yml`, extension `vector`. *Đã chốt.*
2. **Lưu embedding (45')** — `processor.py` trả vector (không chỉ độ dài); `SpaceRecord` giữ `embedding`; ghi bảng `space` (id, đường dẫn, facets, màu, hotspot JSONB, review_status) + cột `embedding vector(512)`.
3. **Chạy lại toàn bộ `image_d3/` (8 thư mục)** (60') — dựng chỉ mục thật; kiểm tra chi phí Gemini ở `outputs/*_cost_*`.
4. **Hàm `search_similar(space_id | text, filters, k)` (45')** — SQL `WHERE space_type=… ORDER BY embedding <=> $1` (cosine) + lọc `space_type` bắt buộc (note seq-2: không trả phòng bếp khi xem phòng ngủ) + trả điểm và lý do (facet trùng).
5. **Test (30')** — thêm vào `tests/`: nạp 1 ảnh → tìm lại chính nó top-1; lọc loại phòng đúng.

Kết thúc tối nay: `python -m pipeline.search "phòng ngủ tông gỗ ấm"` trả được danh sách.

## 7 NGÀY TỚI

| Ngày | Việc | Kết quả kiểm được |
|---|---|---|
| 1 (tối nay) | Như trên | seq-1 + lõi seq-2 chạy CLI |
| 2 | API mỏng (FastAPI): `POST /spaces/ingest`, `GET /spaces/{id}/similar`, `GET /search?q=` ; trạng thái duyệt draft→in_review→approved | gọi được bằng curl/HTTP |
| 3 | Nối API vào `prototype/` (trang chi tiết: khối "Dự án tương tự"; ô tìm kiếm văn bản) | demo trên web |
| 4 | **Kho tri thức RAG**: nạp mô tả dự án, bảng giá, FAQ → chia đoạn → embed (CLIP text hoặc embedding text riêng — quyết định ngày này) | truy hồi top-k có nguồn |
| 5 | Chat endpoint: trích yêu cầu (loại công trình, m², phong cách, ý định hỏi giá) → truy hồi lai → Gemini trả lời + nguồn + 3 ảnh dự án; **ngưỡng chống bịa** ("chưa có thông tin, chuyển KTS") | 10 câu hỏi mẫu pass |
| 6 | Lead handoff (phát hiện hỏi giá/xin hẹn → tạo lead + lưu hội thoại), hotspot "món đồ → dịch vụ" từ `furniture_detection` | seq-3 bước 15–22 chạy |
| 7 | Đánh giá & dọn: bộ ~30 ảnh/câu hỏi có đáp án, đo độ chính xác facet (NFR-10 ≥85%), chi phí/ảnh, viết hướng dẫn chạy | báo cáo số liệu + demo |

## Ngoài phạm vi tuần này (cố ý bỏ)
- M12 InterestScore/dashboard xu hướng, M6 chấm điểm lead theo hành vi, đăng nhập/phân quyền — cần dữ liệu hành vi thật, chưa có.
- Chỉ mục HNSW/IVFFlat — thêm khi >~10k ảnh.

## Rủi ro
- `torch`/`chromadb` không có trong Python mặc định (đã thử import) — xác nhận môi trường chạy GPU 4GB đang dùng ở đâu trước khi chạy lại.
- Chi phí Gemini khi chạy lại hàng loạt — dùng cache theo hash ảnh, bỏ qua ảnh đã phân loại.
- CLIP ViT-B-32 yếu với tiếng Việt: truy vấn văn bản cần dịch sang tiếng Anh trước khi embed (hoặc dùng LLM viết lại truy vấn).
- `sa-key.json` (khóa dịch vụ) đang untracked trong repo — thêm vào `.gitignore` trước khi commit.
