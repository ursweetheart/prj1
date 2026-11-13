# D3 Studio: tổng quan dự án, nguồn diagram và lộ trình hoàn thiện

| | |
| :-- | :-- |
| **Dự án** | Website portfolio thiết kế nội thất tích hợp AI (mã PRJ1-INTERIOR-WEB) |
| **Nhóm** | Nhóm 6: Phạm Việt Tùng, Trần Xuân Bằng, Trần Xuân Tuấn |
| **Cập nhật** | 11/11/2026 |
| **Phiên bản code** | nhánh `main`, commit `1d72fc8` (repo `github.com/ursweetheart/prj1`) |
| **Bản tĩnh** | https://ursweetheart.github.io/prj1/ (không có backend nên các chức năng AI không chạy) |

Tài liệu này dành cho người tiếp tục phát triển dự án:

- mục 1–3 giúp hiểu hệ thống và chạy được trên máy;
- mục 4 chỉ ra nguồn diagram và tài liệu thiết kế;
- mục 5–7 cho biết chức năng nào đã xong, chức năng nào còn thiếu;
- mục 8 là lộ trình đến khi hoàn thiện.

---

## Mục lục

1. [Dự án là gì](#1-dự-án-là-gì)
2. [Kiến trúc và công nghệ](#2-kiến-trúc-và-công-nghệ)
3. [Chạy dự án trên máy](#3-chạy-dự-án-trên-máy)
4. [Nguồn diagram và tài liệu thiết kế](#4-nguồn-diagram-và-tài-liệu-thiết-kế)
5. [Đối chiếu use case với hiện trạng](#5-đối-chiếu-use-case-với-hiện-trạng)
6. [Đối chiếu module M1–M12](#6-đối-chiếu-module-m1m12)
7. [Yêu cầu phi chức năng và chất lượng](#7-yêu-cầu-phi-chức-năng-và-chất-lượng)
8. [Lộ trình phát triển đến khi hoàn thiện](#8-lộ-trình-phát-triển-đến-khi-hoàn-thiện)
9. [Vấn đề tồn tại và nợ kỹ thuật](#9-vấn-đề-tồn-tại-và-nợ-kỹ-thuật)
10. [Quy ước làm việc](#10-quy-ước-làm-việc)
11. [Phụ lục: API, trang, bảng dữ liệu, script](#11-phụ-lục)

---

## 1. Dự án là gì

D3 Studio là công ty thiết kế và thi công nội thất. Tài sản chính của công ty là thư viện ảnh công trình (concept 3D và ảnh thi công thực tế), hiện đang nằm rải rác trên Facebook, Behance và máy cá nhân. Ảnh không có cấu trúc nên khách không lọc được theo cách họ nghĩ (vd "phòng khách chung cư Wabi-sabi tông gỗ sáng"), và công ty cũng không biết khách thực sự thích gì.

Dự án xây dựng website portfolio dựa trên ba trục khoá vào nhau thành một vòng lặp dữ liệu:

```
[1] CẤU TRÚC HOÁ DỮ LIỆU      phân loại đa chiều + AI tự gán nhãn cho từng không gian
          │
          ▼
[2] KHAI THÁC NGHIỆP VỤ        lọc, tìm bằng chữ / bằng ảnh, gợi ý tương tự, trợ lý RAG
          │
          ▼
[3] VÒNG LẶP PHẢN HỒI          ghi nhận hành vi (có đồng ý) → phân tích xu hướng
          │
          └──────► quay lại nuôi [1] (đề xuất chiều phân loại mới) và [2]
```

**Quyết định thiết kế quan trọng nhất:** đơn vị gắn nhãn là **không gian** (`space`, một ảnh), không phải dự án. Lý do: một biệt thự có thể có phòng khách Indochine nhưng phòng ngủ trẻ em lại Scandinavian.

**Mục tiêu hệ thống** (theo tài liệu phân tích yêu cầu):

| ID | Mục tiêu |
| :-- | :-- |
| SG-01 | Lọc portfolio theo ít nhất 6 chiều đồng thời (loại công trình, không gian, phong cách, tông màu, vật liệu, mức đầu tư) |
| SG-02 | Tự gợi ý nhãn cho ảnh mới, độ chính xác ≥ 85% ở các chiều chính |
| SG-03 | Tìm không gian hoặc dự án tương tự |
| SG-04 | Trợ lý trả lời dựa trên dữ liệu công ty (RAG), có dẫn nguồn |
| SG-05 | Ghi nhận và phân tích hành vi để phát hiện xu hướng |

**Ngoài phạm vi:** bán hàng và thanh toán online, quản lý thi công và kế toán, dựng 3D/AR, app di động native. Đây là đồ án môn học, chạy demo trên máy cá nhân, nên **hosting thật, SSR và kiểm thử tải cũng không làm**.

---

## 2. Kiến trúc và công nghệ

```
                 Trình duyệt
                     │
     ┌───────────────┴────────────────┐
     │  Frontend: Vue 3 + Vite         │   src/  (SPA, base path /prj1/)
     │  Docker: nginx :8080            │   GitHub Pages: bản tĩnh, không backend
     └───────────────┬────────────────┘
                     │  /api/* , /images/*  (proxy)
     ┌───────────────┴────────────────┐
     │  Backend: FastAPI :8001         │   backend/api.py, auth.py
     │  ├─ pipeline/processor.py       │   xử lý ảnh khi tải lên
     │  ├─ pipeline/search.py          │   tìm bằng chữ / ảnh / tương tự
     │  ├─ pipeline/assistant.py       │   trợ lý RAG, tạo lead
     │  ├─ pipeline/taxonomy.py        │   phân loại đọc từ DB
     │  └─ pipeline/discovery.py       │   AI đề xuất chiều phân loại mới
     └──────┬──────────────────┬──────┘
            │                  │
  ┌─────────┴───────┐   ┌──────┴───────────────────────────────┐
  │ Postgres 16 +   │   │ Model AI                              │
  │ pgvector :5432  │   │  • YOLOv8s: tìm đồ vật → hotspot      │
  │ (Docker)        │   │  • SigLIP2 ViT-B-16: embedding ảnh    │
  └─────────────────┘   │    và chữ, 768 chiều (open_clip)      │
                        │  • Gemini (Vertex AI): phân loại,     │
                        │    mô tả ảnh, trả lời, đề xuất        │
                        │  • text-multilingual-embedding-002    │
                        │    (Vertex): embedding mô tả ảnh      │
                        └───────────────────────────────────────┘
```

- **Không tự train model nào.** YOLO và SigLIP2 dùng trọng số có sẵn. Gemini và các embedding gọi qua Vertex AI, dùng khoá service account `backend/sa-key.json`.
- **Frontend:** Vue 3, Vue Router, Vite, Vitest. Có một plugin Vite (`vite-plugins/projectImageSizes.js`) đọc kích thước ảnh lúc build cho gallery dự án.
- **Backend:** Python 3.12, FastAPI, psycopg 3, pgvector, PyJWT, Argon2 (pwdlib), Authlib (Google/Facebook OAuth), pytest.
- **Docker:** `docker-compose.yml` ở thư mục gốc gồm `db`, `backend` (torch CPU) và `web` (nginx). Trọng số model **không đóng vào image**, được gắn từ `backend/models/`.

### Cấu trúc repo

```
.
├── src/                    frontend Vue (views, components, composables, data, assets)
├── public/, img/, css/     ảnh và CSS tĩnh
├── vite-plugins/           plugin đọc kích thước ảnh lúc build
├── openspec/               OpenSpec của frontend (và change discover-taxonomy-dimensions)
├── backend/
│   ├── api.py, auth.py     API
│   ├── pipeline/           xử lý ảnh, tìm kiếm, trợ lý, phân loại, discovery
│   ├── schema.sql          toàn bộ schema DB (áp lại nhiều lần được)
│   ├── kb/                 kho tri thức trợ lý (mẫu, template, generated, taxonomy_seed)
│   ├── eval/               bộ câu hỏi đánh giá
│   ├── tests/              pytest
│   ├── openspec/           OpenSpec của backend (specs + archive)
│   ├── image_d3/           ảnh gốc (git ignore, phải chép tay)
│   └── models/             trọng số YOLO, SigLIP2 (git ignore)
├── docs/                   khảo sát và tài liệu này
├── Dockerfile, nginx.conf  image frontend
└── docker-compose.yml      cả hệ thống
```

---

## 3. Chạy dự án trên máy

### 3.1 File cần xin riêng (KHÔNG có trong git, KHÔNG gửi qua chat công khai)

| File | Dùng cho |
| :-- | :-- |
| `backend/.env` | khoá JWT, Google/Facebook OAuth, cấu hình (mẫu ở `.env.example`) |
| `backend/sa-key.json` | khoá service account Vertex AI (Gemini, embedding) |
| `backend/image_d3/` | thư mục ảnh gốc của các dự án |
| `backend/models/` | trọng số model (tuỳ chọn; thiếu thì tự tải: YOLO 22 MB, SigLIP2 1,5 GB) |

### 3.2 Chạy bằng Docker (cách nhanh nhất)

```bash
docker compose up -d --build        # ở thư mục gốc → http://localhost:8080/prj1/
docker compose exec backend python ingest.py image_d3          # nạp ảnh vào DB lần đầu
docker compose exec backend python -m pipeline.assistant kb/sample.json   # nạp kho tri thức
docker compose down                 # tắt; dữ liệu vẫn còn trong volume prj1_pgdata
```

- `schema.sql` chỉ tự chạy khi volume DB còn trống. Khi code thêm bảng/cột mới (vd change `lead-intake`), áp lại vào DB đang có (mọi lệnh đều chạy lại được):
  `docker compose exec -T db psql -U d3 -d d3 < backend/schema.sql`
- Dữ liệu MÔ PHỎNG cho bảng xu hướng (chỉ để demo): `docker compose exec backend python -m pipeline.demo_activity` tạo ~8 tuần hành vi giả (phiên `demo-…`, một phong cách tăng). Bảng điều khiển hiện cảnh báo "dữ liệu mô phỏng", phân loại tự động bỏ qua chúng. **Xóa trước khi dùng thật:** `docker compose exec backend python -m pipeline.demo_activity --remove`
- Email báo lead mới cho sales: điền `D3_SMTP_*` và `D3_SALES_EMAIL` trong `backend/.env` (mẫu ở `.env.example`). Bỏ trống thì lead chỉ ghi log và hiện "mới" ở `/khach-hang`, demo vẫn chạy.
- Cổng 8001 vẫn mở vì callback đăng nhập Google/Facebook đã đăng ký ở `localhost:8001`.
- Cổng 8000 để trống cho việc khác (crawl).

### 3.3 Chạy kiểu dev

```bash
docker compose up -d db                       # chỉ DB
cd backend
python -m venv .venv && .venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m uvicorn api:app --port 8001 --env-file .env
cd ..
npm ci && npm run dev                         # http://localhost:5173/prj1/ (proxy /api sang :8001)
```

### 3.4 Tài khoản và quyền

Tự đăng ký luôn được role `visitor`. Để nâng quyền:

```bash
cd backend
.venv\Scripts\python set_role.py email@example.com admin
```

Khi đã có admin, có thể dùng `PATCH /users/{id}/role`.

| Role | Được làm gì |
| :-- | :-- |
| `visitor` | xem, tìm, chat |
| `content` | sửa mô tả và alt text của ảnh ở trạng thái Chờ duyệt |
| `sales` | xem lead ở `/khach-hang` |
| `architect` | tải ảnh, sửa nhãn, gửi Nháp → Chờ duyệt |
| `lead_architect` | như architect, cộng duyệt/xác nhận quyền/đăng, duyệt phân loại, xem lead |
| `admin` | toàn quyền, đổi role người khác |

### 3.5 Kiểm thử

```bash
cd backend && .venv\Scripts\python -m pytest --ignore=tests/test_gpu_pipeline.py   # cần DB đang chạy
npm test                                                                            # vitest
npm run build && git restore dist      # dist/ vẫn đang bị git theo dõi, build xong phải restore
```

Kết quả gần nhất: backend 93 test qua, 1 bỏ qua (2/11/2026); frontend 20/20 qua sau khi gộp `main`.

---

## 4. Nguồn diagram và tài liệu thiết kế

### 4.1 Nơi lưu

| Nguồn | Vị trí |
| :-- | :-- |
| **Thư mục diagram chính `project 1`** (file `.drawio`, mở bằng draw.io / diagrams.net) | Google Drive: https://drive.google.com/drive/folders/1InjgGPRSpP0PDTOUjbA513_9IEVr5hIK (cần được Tuấn chia sẻ quyền xem). Bản sao trên máy Tuấn: `D:\prj1_tailieu\project 1\` |
| Tài liệu phân tích yêu cầu (BAD) | `D:\prj1_tailieu\01-Phan-tich-yeu-cau.md` |
| Kế hoạch luồng AI ban đầu | `D:\prj1_tailieu\KE-HOACH-LUONG-AI.md` |
| Slide thuyết trình | `D:\prj1_tailieu\D3-Studio-slides*.pptx`, `Slides_diagram.html` |
| Ảnh diagram đã render (PNG) | `D:\prj1_tailieu\slides_build\out\png\` |
| Khảo sát khách hàng | `docs/Website D3 Studio (Câu trả lời).xlsx` trong repo |
| Spec kỹ thuật (OpenSpec) | `backend/openspec/specs/` (backend), `openspec/changes/` (frontend + change đang làm) |

Tài liệu BAD tham chiếu thêm các file `02-Bo-cau-hoi-phong-van.md`, `03-User-story-va-tieu-chi-chap-nhan.md`, `04-Mo-hinh-hoa-yeu-cau.md` và `05-Taxonomy-ngon-ngu-thiet-ke.md`, nhưng các file này **không có** trong thư mục tài liệu hiện tại. Cần hỏi lại người giữ.

### 4.2 Danh sách diagram trong `project 1`

**Use case** (`Use case diagram/`): 6 file.

| File | Nội dung |
| :-- | :-- |
| `usecase-0-tong-quan` | toàn bộ UC01–UC27 và 9 tác nhân |
| `usecase-1-khach` | khách tham quan / khách đã đăng ký: UC01–UC11, UC21, UC27 |
| `usecase-2-kien-truc-su` | KTS / KTS trưởng: UC12–UC15, UC17, UC25–UC27 |
| `usecase-3-nv-noi-dung` | nhân viên nội dung: UC14, UC16, UC27 |
| `usecase-4-ban-hang` | trưởng phòng kinh doanh: UC21–UC23 |
| `usecase-5-quan-tri-he-thong` | quản trị viên và tác nhân hệ thống: UC23–UC27 |

**Chức năng và nghiệp vụ:**

| File | Nội dung |
| :-- | :-- |
| `BFD/bfd-1-tong-quan` | cây chức năng: 1. Khám phá, 2. Tương tác & tư vấn, 3. Quản trị nội dung, 5. Phân tích hành vi, 6. Nền tảng |
| `business-flow/business-flow-1-tong-the-d3-studio` | quy trình tổng thể theo làn: Khách, Website + AI, KTS, NV nội dung, Kinh doanh, Ban lãnh đạo (QT-01 → QT-06 → QT-02 → sau bán) |

**Activity** (`Activity diagram/`): 8 file.

| File | Quy trình |
| :-- | :-- |
| `activity-1-xuat-ban-du-an-QT01` | xuất bản dự án: tải ảnh → AI gán nhãn → KTS xác nhận → biên tập → duyệt → xác nhận quyền → đăng |
| `act-2-xu-ly-khach-tiem-nang-QT02` | xử lý lead |
| `act-3-thu-thap-phan-tich-xu-huong-QT06` | thu thập hành vi và phân tích xu hướng |
| `act-4-hoi-dap-tro-ly-va-chuyen-tiep` | chat với trợ lý và chuyển cho người thật |
| `act-5-tim-bang-anh-tai-len` | tìm bằng ảnh tải lên |
| `act-6-uoc-tinh-chi-phi` | ước tính chi phí sơ bộ |
| `act-7-dong-y-thu-thap-du-lieu` | đồng ý thu thập dữ liệu (cookie/consent) |
| `act-8-luu-anh-va-gui-brief` | lưu ảnh vào bộ sưu tập và gửi làm brief |

**Sequence** (`Sequence diagram/`): 18 file. Không có seq-17.

| File | Use case | Đã có code? |
| :-- | :-- | :-- |
| `seq-1-gan-nhan-tu-dong` | UC25, UC26 | Có |
| `seq-2-tim-khong-gian-tuong-tu` | UC03 | Có |
| `seq-3-hoi-dap-tro-ly-rag` | UC09 | Có |
| `seq-4-ghi-nhan-hanh-vi` | UC21 | Một phần: xem và lưu ảnh (`luu_anh`); tính khi mở bảng điều khiển, chưa có tiến trình hằng đêm |
| `seq-5-gui-form-lien-he` | UC11 | Một phần (qua chat) |
| `seq-6-duyet-va-xuat-ban` | UC14 | Có |
| `seq-7-gui-bo-suu-tap-lam-brief` | UC08 | Có (change `saved-collection-brief`) |
| `seq-8-tim-bang-anh-tai-len` | UC04 | Có |
| `seq-9-uoc-tinh-chi-phi` | UC10 | Có (change `cost-estimate`), với đơn giá mẫu |
| `seq-10-loc-portfolio-va-xem-chi-tiet` | UC01, UC02 | Có (đang bị ẩn, xem mục 9) |
| `seq-11-tim-bang-mo-ta-tu-nhien` | UC05 | Có |
| `seq-12-trac-nghiem-phong-cach` | UC06 | Chưa |
| `seq-13-luu-anh-va-dang-ky-giu-bo-suu-tap` | UC07 | Có: trình duyệt khi chưa đăng nhập, gộp vào tài khoản khi đăng ký/đăng nhập |
| `seq-14-gan-hotspot-mon-do` | UC17 | Một phần |
| `seq-15-quan-ly-taxonomy-gop-gia-tri` | UC15 | Một phần (API, chưa có UI) |
| `seq-16-quan-ly-tri-thuc-tro-ly` | UC16 | Một phần (CLI, chưa có UI) |
| `seq-18-bao-cao-dinh-ky-va-bang-dieu-khien` | UC22, UC23 | Bảng điều khiển: có (change `trend-dashboard`). Báo cáo email hằng tuần: chưa |
| `seq-19-quan-ly-tai-khoan-va-phan-quyen` | UC24 | Một phần (API, chưa có UI) |

**Class** (`Class diagram/`): 7 file.

| File | Nhóm lớp |
| :-- | :-- |
| `class-0-tong-quan` | 16 lớp và quan hệ |
| `class-1-noi-dung-portfolio` | DuAn, KhongGian, Anh, Hotspot, MonDo |
| `class-2-taxonomy` | ChieuPhanLoai, GiaTriPhanLoai |
| `class-3-khach-hang-va-ban-hang` | KhachTiemNang, BoSuuTap |
| `class-4-hoi-thoai-va-hanh-vi` | PhienTruyCap, SuKien, HoiThoai, TinNhan |
| `class-5-nguoi-dung-va-phan-quyen` | NguoiDung |
| `class-6-day-du-thuoc-tinh` | toàn bộ, kèm thuộc tính |

**DFD** (`DFD/`): 7 file. Gồm `dfd-0-1-ngu-canh-va-muc-1` (bản đầy đủ và bản gọn), và các DFD mức 2: `2-1-kham-pha`, `2-2-tuong-tac`, `2-3-quan-tri-noi-dung`, `2-4-khach-tiem-nang`, `2-5-phan-tich-xu-huong`.

### 4.3 Diagram cần cập nhật cho khớp code

Code đã khác thiết kế ở vài chỗ. Người sửa diagram nên đối chiếu `backend/schema.sql`.

| Diagram | Cần sửa |
| :-- | :-- |
| `class-2-taxonomy`, `class-6` | thêm lớp **UngVienPhanLoai** (đề xuất chiều mới: tên, giá trị, bằng chứng/điểm, trạng thái `cho_bang_chung` / `cho_duyet` / `chap_nhan` / `tu_choi`), **KhoangTrongTriThuc** (câu hỏi chatbot không trả lời được) và bảng nối `space_gia_tri` |
| `class-4`, `class-6` | **SuKienAnDanh**: bộ đếm theo ngày khi khách không đồng ý thu thập |
| `class-1`, `class-6` | trạng thái duyệt của KhongGian: `draft`, `in_review`, `approved`, `cleared`, `published`; nhật ký `review_log` |
| `seq-15` | thêm luồng "AI đề xuất chiều mới → KTS trưởng duyệt → AI gắn nhãn cả thư viện" (tín hiệu → chấm điểm → cổng duyệt) |
| `class-5`, `seq-19` | role thực tế là `visitor`, `content`, `sales`, `architect`, `lead_architect`, `admin`. Diagram có "Khách đã đăng ký" và "TP Kinh doanh", cần ghi rõ ánh xạ |
| Tất cả | **tên bảng trong code** khác tên lớp: `space` = KhongGian/Anh, `app_user` = NguoiDung, `lead` = KhachTiemNang, `kb_chunk` = tri thức trợ lý, `space_text` = VectorMoTa. Chưa có bảng DuAn (dự án lấy theo thư mục ảnh), BoSuuTap, HoiThoai/TinNhan (hội thoại lưu trong `lead.conversation`), MonDo |

---

## 5. Đối chiếu use case với hiện trạng

Ký hiệu: **Xong** = chạy được đầu cuối và có test. **Một phần** = có lõi nhưng thiếu so với thiết kế. **Chưa** = chưa có code.

### 5.1 Khám phá nội dung (khách)

| UC | Tên | Trạng thái | Đang ở đâu | Còn thiếu |
| :-- | :-- | :-- | :-- | :-- |
| UC01 | Bộ lọc portfolio đa chiều | **Một phần** | `CongTrinhView.vue` lọc 6 chiều (`/spaces` + `/taxonomy`). Trang chủ và `/du-an` lọc theo 3 nhóm Tất cả / Nhà ở / Thương mại | Route `/cong-trinh` đang bị chuyển sang `/du-an` nên trang lọc 6 chiều không vào được. Chưa có URL SEO cho từng tổ hợp (`/portfolio/phong-khach/chung-cu/wabi-sabi`), chưa sắp xếp kết quả (BFD 1.2) |
| UC02 | Xem chi tiết dự án | **Một phần** | `/du-an/:slug` (64 dự án tĩnh, gallery, lightbox); `/khong-gian/:id` (ảnh từ DB, hotspot, bảng màu, tương tự) | Hai nguồn dữ liệu tách rời (mục 9.1). Thiếu bảng thông số (diện tích, số phòng, thời gian, mức đầu tư), thuyết minh ý tưởng, so sánh Concept ↔ Thực tế (component `BeforeAfter.vue` có nhưng chưa có dữ liệu cặp ảnh) |
| UC03 | Tìm không gian tương tự | **Xong** | `GET /spaces/{id}/similar`, khối "tương tự" ở `/khong-gian/:id` | Chưa đo precision@5 (NFR-11). Luồng "món đồ → dịch vụ" (M3) chưa có |
| UC04 | Tìm bằng ảnh tải lên | **Xong** | `POST /search/image`, nút "Tìm bằng ảnh" ở `/cong-trinh` | Hiện không truy cập được vì `/cong-trinh` bị ẩn |
| UC05 | Tìm bằng mô tả tự nhiên | **Xong** | `GET /search?q=` (SigLIP2), ô tìm ở `/cong-trinh` | Như trên |
| UC06 | Trắc nghiệm phong cách | **Chưa** | | Thiết kế ở `seq-12` |

### 5.2 Tương tác cá nhân

| UC | Tên | Trạng thái | Đang ở đâu | Còn thiếu |
| :-- | :-- | :-- | :-- | :-- |
| UC07 | Lưu ảnh vào bộ sưu tập | **Có** | tim trên thẻ `/khong-gian` và trang không gian (`SaveHeart.vue`), `lib/collection.js`: chưa đăng nhập giữ trong trình duyệt, đăng nhập thì lưu ở bảng `bo_suu_tap` và gộp bản trình duyệt; trang `/bo-suu-tap` có ghi chú từng ảnh, tối đa 60 ảnh. **Tùng lưu ý:** tim nằm trên `SpaceTile.vue` (bọc thêm một `div`, link giữ nguyên) và hàng tiêu đề `SpaceView.vue` | Chưa có tim trong Lightbox trang dự án (chờ ảnh dự án được nạp thành không gian). `useMoodboard.js` + `SpaceCard.vue` là code cũ không còn trang nào dùng |
| UC08 | Gửi bộ sưu tập làm brief | **Có** | `BriefForm.vue` → `POST /briefs` (không cần tài khoản): bản sao cố định + link chỉ xem `/bo-suu-tap/xem/<mã>`, lead nguồn `brief` kèm loại nhà, diện tích, ngân sách, tóm tắt "Wabi-sabi 60% · tông Ấm · phòng khách"; email cho sales và khách kèm link | Chưa có chia sẻ bộ sưu tập đang lưu (chỉ bản đã gửi) |
| UC09 | Hỏi trợ lý ảo | **Xong** | `POST /chat`, `ChatWidget.vue`. Trả lời từ kho tri thức, sau đó từ mô tả ảnh đã đăng; kèm ảnh nguồn; dưới ngưỡng thì chuyển KTS; chặn câu trả lời có số tiền hay cam kết | Kho tri thức đang là **dữ liệu mẫu** (`kb/sample.json`), cần bảng giá và FAQ thật. Chưa lưu lịch sử hội thoại riêng |
| UC10 | Ước tính chi phí sơ bộ | **Có (đơn giá mẫu)** | `/uoc-tinh`: loại nhà, diện tích, số phòng ngủ, gói vật liệu → khoảng giá + bóc tách 4 hạng mục, công thức cố định trên bảng `don_gia` (`pipeline/estimate.py`); dự án cùng loại; "Nhận bản chi tiết qua email" → lead nguồn `estimate` + email bóc tách. KTS trưởng sửa giá ở `/quan-tri/don-gia` | **D3 chưa có bảng giá: 60 ô đang là giá MẪU tự đặt (`nguon='mau'`, trang ghi rõ "Đơn giá mẫu"). Phải thay bằng giá thật ở `/quan-tri/don-gia` trước khi dùng thật.** Chưa gợi ý dự án theo ngân sách (dự án chưa có khoảng đầu tư) |
| UC11 | Gửi yêu cầu tư vấn | **Một phần** | `POST /leads` + `ContactForm.vue` (≤ 5 trường, chống spam, hồ sơ hành vi khi khách đồng ý 2 lần) ở cuối trang dự án; chat chuyển tiếp dùng chung luồng; email cho sales khi có SMTP | Trang `/lien-he` chưa có (0.3): chỉ cần nhúng `<ContactForm />`. Chưa gửi SMS |

### 5.3 Quản trị nội dung

| UC | Tên | Trạng thái | Đang ở đâu | Còn thiếu |
| :-- | :-- | :-- | :-- | :-- |
| UC12 | Tải ảnh hàng loạt | **Xong** | `/quan-tri` → "Tải ảnh dự án mới", `POST /spaces/ingest` | Xử lý tuần tự từng ảnh; trên CPU mất vài giây mỗi ảnh |
| UC13 | Gắn nhãn không gian | **Xong** | `/quan-tri`: sửa loại phòng, phong cách, vật liệu; tag loại công trình và mức đầu tư theo ảnh hoặc cả dự án | |
| UC14 | Duyệt và xuất bản dự án | **Xong** | `/quan-tri`: Nháp → Chờ duyệt → Đã duyệt → Đã xác nhận quyền → Đã đăng, chuyển hàng loạt, ô xác nhận quyền công bố, `review_log` | Chưa có nút trả về hay từ chối. Chưa theo dõi hiệu quả sau 30 ngày (QT-01 bước cuối, BFD 5.4) |
| UC15 | Quản lý taxonomy | **Một phần** | Phân loại nằm trong DB. API thêm / đổi tên / gộp giá trị. AI đề xuất chiều mới, duyệt ở `/quan-tri/phan-loai` | **Chưa có giao diện** thêm, đổi tên, gộp giá trị. Chưa tạo chiều mới bằng tay. Đổi tên chưa cập nhật nhãn trong chỉ mục vector |
| UC16 | Quản lý tri thức trợ lý | **Một phần** | file JSON + lệnh `python -m pipeline.assistant kb/...`; `generate_kb.py` sinh nháp | Chưa có giao diện CMS để NV nội dung thêm, sửa, xoá đoạn tri thức |
| UC17 | Gắn hotspot món đồ | **Một phần** | YOLO gợi ý; ở `/quan-tri` sửa tên và xoá hotspot; hiển thị trên `/khong-gian/:id` | Chưa thêm hotspot mới bằng tay, chưa kéo vị trí, chưa liên kết tới **thư viện món đồ/vật liệu (M7)** và gói dịch vụ |

### 5.4 Phân tích và hệ thống

| UC | Tên | Trạng thái | Đang ở đâu | Còn thiếu |
| :-- | :-- | :-- | :-- | :-- |
| UC21 | Ghi nhận hành vi | **Một phần** | sự kiện `xem_khong_gian` và `luu_anh` (tim lưu ảnh, change `trend-dashboard`); `POST /events`; banner đồng ý (`ConsentBanner.vue`); chỉ lưu khi khách đồng ý, nếu không thì chỉ đếm theo ngày; sự kiện kèm giá trị phân loại | Chỉ có **1 loại sự kiện** (`xem_khong_gian`). Thiết kế cần thêm: `xem_trang`, `xem_du_an`, `phong_to_anh`, `chuyen_anh`, `ap_dung_bo_loc`, `bam_hotspot`, `luu_moodboard`, `chia_se`, `nhan_chatbot`, `bam_CTA`, `gui_form` |
| UC22 | Bảng điều khiển xu hướng | **Có (v1)** | `/quan-tri/xu-huong` (sales, KTS trưởng, admin): điểm quan tâm = xem×1 + lưu×3 + ảnh gửi brief×5 theo từng giá trị phân loại, tỉ lệ trong chiều, xu hướng 7 ngày so với trung bình 4 tuần (tăng ≥ 50%, giảm ≤ 50%, mới nổi, cần ≥ 5 tín hiệu), cảnh báo, tổng lượt xem/lưu/brief/lead, lead theo tuần, top không gian (`pipeline/trends.py`, `GET /analytics/overview`) | Chưa có tiến trình hằng đêm và kho phân tích (tính khi mở trang), chưa phân cụm phiên, chưa có thời gian xem / độ sâu cuộn |
| UC23 | Gửi báo cáo định kỳ | **Chưa** | | bộ lập lịch + gửi email hằng tuần |
| UC24 | Quản lý tài khoản, phân quyền | **Một phần** | đăng ký, đăng nhập email / Google / Facebook, JWT tự gia hạn, 6 role, `PATCH /users/{id}/role`, `set_role.py` | Chưa có trang quản trị người dùng, chưa khoá hay xoá tài khoản, chưa quên mật khẩu |
| UC25 | Gợi ý nhãn tự động | **Xong** | `pipeline/processor.py` (Gemini + màu + YOLO), `relabel.py` | Chưa đo được NFR-10 vì mới có 9 ảnh được duyệt (cần ≥ 30) |
| UC26 | Sinh mô tả nháp | **Xong** | mô tả + alt text khi ingest; `generate_transcripts.py` (mô tả dài cho RAG) | |
| UC27 | Lập chỉ mục vector | **Xong** | pgvector: embedding ảnh (SigLIP2) + embedding mô tả (Vertex) | Chưa có chỉ mục HNSW/IVFFlat (chỉ cần khi > ~10.000 ảnh) |

### 5.5 Chức năng có trong code nhưng không có trong use case

- **AI đề xuất chiều phân loại mới** (`pipeline/discovery.py`): Gemini đọc mô tả ảnh, câu hỏi khách chưa được trả lời và lượt xem của khách đã đồng ý, rồi đề xuất chiều mới. Mỗi đề xuất được chấm điểm theo độ phủ, độ khác biệt và nhu cầu, rồi qua một bước Gemini tự kiểm tra trùng lặp. KTS trưởng duyệt; chấp nhận thì AI gắn nhãn cả thư viện. Ngày 2/11 có 2 đề xuất đang chờ duyệt.
- **Ghi lại câu hỏi chatbot không trả lời được** (`khoang_trong_tri_thuc`), làm nguồn cho đề xuất trên.
- **Trang `/khach-hang`** cho sales xem danh sách lead (ý định, nội dung hội thoại, liên hệ).
- **Giới hạn tần suất** theo IP: chat 20 lần/phút, đăng nhập và đăng ký 10 lần/phút, tìm bằng ảnh 10 lần/phút.

---

## 6. Đối chiếu module M1–M12

| Module | Trạng thái | Ghi chú ngắn |
| :-- | :-- | :-- |
| M1 Danh mục đa chiều | Một phần | lọc 6 chiều có, nhưng trang đang bị ẩn; chưa có URL SEO |
| M2 Trang chi tiết dự án | Một phần | gallery đẹp; thiếu thông số, before/after, khối "dự án tương tự" ở cấp dự án |
| M3 Gợi ý tương tự | Một phần | ảnh → ảnh và chữ → ảnh có; món đồ → dịch vụ chưa có |
| M4 RAG Chatbot | Xong (lõi) | cần dữ liệu tri thức thật; chưa lọc theo metadata chi tiết (vd diện tích) |
| M5 CMS & QT-01 | Xong | thiếu trả về/từ chối và theo dõi sau 30 ngày |
| M6 Quản lý lead (QT-02) | Một phần | chỉ tạo và xem lead. Chưa có vòng đời `Mới → Đã liên hệ → Đủ điều kiện → Đã hẹn khảo sát → Đã báo giá → Ký HĐ / Thất bại`, chấm điểm lead theo hành vi, "dấu chân" khách, thông báo cho sales |
| M7 Thư viện vật liệu/sản phẩm + hotspot | Một phần | hotspot có; thư viện món đồ (bảng MonDo) chưa có |
| M8 Người dùng & phân quyền | Một phần | 6 role và API có; chưa có UI quản trị; audit log mới có cho duyệt ảnh |
| M9 Auto-tagging | Xong | |
| M10 Vector index | Xong | |
| M11 Thu thập hành vi | Một phần | đồng ý + 1 loại sự kiện |
| M12 Xu hướng & dashboard | Chưa | |

---

## 7. Yêu cầu phi chức năng và chất lượng

| ID | Yêu cầu | Trạng thái |
| :-- | :-- | :-- |
| NFR-01 | LCP < 2,5 s; lọc < 500 ms | Chưa đo |
| NFR-02/03 | tìm vector trên 10.000 ảnh < 1 s; 50.000 ảnh, 100 người dùng | Ngoài phạm vi (chỉ demo local, không kiểm thử tải) |
| NFR-04 | ảnh đúng màu, không méo | Gallery giữ tỉ lệ gốc; ảnh dự án nén 1600 px q75, cần KTS xác nhận chất lượng |
| NFR-05 | giao diện tối giản, ≤ 2 font | Đã theo phong cách Elemental |
| NFR-06 | mobile-first, Safari iOS, Chrome Android | Header co lại dưới 1024 px; **chưa thử trên điện thoại thật** (task 5.4, 5.5 của `responsive-stacked-navbar`) |
| NFR-07 | SEO: SSR, schema.org, URL theo facet | Chưa (SPA thuần; SSR ngoài phạm vi demo) |
| NFR-08 | phân quyền, chặn file độc hại, giới hạn gọi AI | Có: role, kiểm tra loại và kích thước ảnh (415/413), rate limit |
| NFR-09 | banner đồng ý, ẩn danh hành vi | Có |
| NFR-10 | gán nhãn ≥ 85% ở Phong cách và Không gian | Có công cụ `eval_labels.py`; chưa đủ ảnh đã duyệt để đo |
| NFR-11 | precision@5 ≥ 0,7 cho gợi ý tương tự | Chưa đo |
| NFR-12 | đăng 1 dự án 40 ảnh < 20 phút | Chưa đo (đã đi hết quy trình với dự án 9 ảnh) |
| NFR-13 | thêm phong cách mới không sửa code | Đạt về dữ liệu (phân loại trong DB); còn thiếu giao diện (UC15) |

**Dữ liệu ngày 2/11/2026:** 152 không gian trong DB, trong đó 9 ảnh đã đăng (dự án `indochine_chinosere_villa`) và 143 ảnh nháp. Frontend tĩnh có 64 dự án trong `src/assets/projects/`.

---

## 8. Lộ trình phát triển đến khi hoàn thiện

Các giai đoạn xếp theo thứ tự ưu tiên. Mỗi việc ghi diagram liên quan và tiêu chí coi là xong. Mỗi việc lớn nên được làm thành một **OpenSpec change** (`/opsx:propose` → `/opsx:apply` → `/opsx:archive`).

### Giai đoạn 0: Gỡ vướng hiện tại (làm trước mọi thứ)

| # | Việc | Diagram | Xong khi |
| :-- | :-- | :-- | :-- |
| 0.1 | **Thống nhất một nguồn dữ liệu dự án.** Hiện `/du-an` đọc 64 dự án tĩnh trong `src/data/projects.js`, còn tìm kiếm, lọc, chat và duyệt dùng 152 ảnh trong DB. Đề xuất: tạo bảng `du_an` (slug, tên, loại, năm, mô tả) và nạp 64 dự án vào DB qua `ingest`. Trang `/du-an` đọc API khi có backend, dùng file tĩnh khi chạy trên GitHub Pages | class-1, seq-10 | một dự án tải lên ở `/quan-tri` và được đăng sẽ hiện ở `/du-an` |
| 0.2 | **Đưa trang lọc và tìm kiếm trở lại.** Bỏ redirect `/cong-trinh → /du-an`, thêm mục menu (vd "Không gian" hoặc "Tìm kiếm"). Có thể chỉ bật khi build có backend | seq-10, seq-11, seq-8 | vào được lọc 6 chiều, tìm bằng chữ, tìm bằng ảnh từ menu |
| 0.3 | Tạo trang **Về chúng tôi** (`/ve-chung-toi`) và **Liên hệ** (`/lien-he`). Menu đang trỏ tới nhưng chưa có route. Trang Liên hệ **không tự làm form**: `import ContactForm from '@/components/ContactForm.vue'` rồi đặt `<ContactForm />` (lead tự ghi trang `/lien-he`) | BFD 2, seq-5 | không còn link chết trên menu |
| 0.4 | Duyệt và đăng thêm ảnh để có dữ liệu demo (mục tiêu ≥ 30 ảnh đã duyệt) | act-1 | `eval_labels.py` chạy được |
| 0.5 | Duyệt 2 đề xuất phân loại đang chờ, đánh dấu thật/sai để làm task 4.1, archive change `discover-taxonomy-dimensions` | seq-15 | change được archive |
| 0.6 | Archive 8 change frontend đã xong task; hoàn thành task 5.4, 5.5 của `responsive-stacked-navbar` | | `openspec list` chỉ còn change đang làm |

### Giai đoạn 1: Hoàn thiện nghiệp vụ nội bộ

| # | Việc | Diagram | Xong khi |
| :-- | :-- | :-- | :-- |
| 1.1 | **UI quản lý taxonomy** ở `/quan-tri/phan-loai`: liệt kê chiều và giá trị; thêm, đổi tên, gộp (API đã có); thêm chiều mới bằng tay; sửa từ đồng nghĩa | seq-15, class-2 | KTS trưởng làm được mọi thao tác không cần Swagger |
| 1.2 | ~~Vòng đời lead (QT-02)~~ **Bỏ:** `usecase-0` và `usecase-4` ghi rõ liên hệ, phân công, theo dõi lead do đội tư vấn làm *ngoài hệ thống*; hệ thống chỉ lưu lead và báo kèm hồ sơ hành vi | act-2, usecase-0/4 | — |
| 1.3 | ✓ **Hồ sơ hành vi trong lead** (change `lead-intake`): bản chụp không gian đã xem và giá trị phân loại nổi bật, chỉ khi khách đồng ý banner *và* tick ô trên form/chat. Chưa chấm điểm lead | act-2, seq-4 | `/khach-hang` hiện "Sở thích" kèm ảnh đã xem |
| 1.4 | ✓ **Thông báo cho sales** khi có lead mới (change `lead-intake`): email qua SMTP nếu cấu hình, không thì ghi log | business-flow, seq-5 | có email kèm nguồn, liên hệ, ngữ cảnh, tóm tắt sở thích |
| 1.5 | **UI quản lý tri thức trợ lý** cho NV nội dung: thêm, sửa, xoá đoạn `kb_chunk`, duyệt bản nháp AI sinh | seq-16, usecase-3 | không phải sửa JSON tay |
| 1.6 | Thay `kb/sample.json` bằng **bảng giá, quy trình, FAQ thật** của D3 Studio | seq-3 | không còn dấu `[DỮ LIỆU MẪU]` |
| 1.7 | **UI quản trị người dùng**: danh sách, đổi role, khoá tài khoản; quên mật khẩu | seq-19, usecase-5 | admin không phải dùng `set_role.py` |
| 1.8 | Duyệt ảnh: nút **trả về / từ chối** kèm lý do | act-1, seq-6 | |
| 1.9 | Hotspot: thêm điểm bằng tay, kéo vị trí; bảng **MonDo** (thư viện món đồ/vật liệu) và liên kết hotspot → món đồ → gói dịch vụ | seq-14, class-1 | bấm hotspot sofa ra các không gian có sofa tương tự |

### Giai đoạn 2: Hoàn thiện trải nghiệm khách

| # | Việc | Diagram | Xong khi |
| :-- | :-- | :-- | :-- |
| 2.1 | ✓ **Bộ sưu tập** (change `saved-collection-brief`): trình duyệt → tài khoản khi đăng nhập, trang `/bo-suu-tap`, ghi chú. Link chia sẻ chỉ cho bản đã gửi | seq-13, act-8, class-3 | đổi máy vẫn thấy |
| 2.2 | ✓ **Gửi bộ sưu tập làm brief** (change `saved-collection-brief`): lead nguồn `brief` kèm ảnh, ghi chú, tóm tắt gu, link chỉ xem | seq-7, act-8 | sales thấy brief kèm ảnh ở `/khach-hang` |
| 2.3 | **Form liên hệ:** đã có `ContactForm.vue` + `POST /leads` (change `lead-intake`), đặt ở trang dự án. Còn lại: nhúng `<ContactForm />` vào trang `/lien-he` của 0.3 | seq-5 | lead loại "form" xuất hiện |
| 2.4 | ✓ **Ước tính chi phí sơ bộ** (change `cost-estimate`): công thức trên bảng đơn giá, giá mẫu ghi rõ, nhân viên sửa giá không cần sửa code | seq-9, act-6 | còn lại: nhập giá thật của D3 |
| 2.5 | **Trắc nghiệm phong cách**: chọn ảnh thích → gợi ý phong cách và không gian phù hợp (dùng embedding SigLIP2) | seq-12 | |
| 2.6 | Trang chi tiết dự án đầy đủ: bảng thông số, thuyết minh, dải màu, vật liệu chính, before/after Concept ↔ Thực tế, "dự án tương tự" | seq-10, class-1 | đủ các mục của M2 |
| 2.7 | Sắp xếp kết quả lọc (mới nhất, phổ biến) | BFD 1.2 | |
| 2.8 | Trợ lý: lọc theo metadata (diện tích, loại công trình khách nói), lưu lịch sử hội thoại (bảng HoiThoai/TinNhan) | seq-3, class-4 | |

### Giai đoạn 3: Vòng lặp phản hồi (trục 3)

| # | Việc | Diagram | Xong khi |
| :-- | :-- | :-- | :-- |
| 3.1 | Thêm các loại sự kiện còn thiếu (danh sách ở UC21), vẫn chỉ ghi khi có đồng ý | seq-4, act-7, dfd-2-5 | |
| 3.2 | ✓ **InterestScore** và **Trend** (change `trend-dashboard`): xem, lưu, ảnh gửi brief; so 7 ngày với trung bình 4 tuần | act-3, seq-4 | còn: thời gian xem, chia sẻ, lead phát sinh theo giá trị |
| 3.3 | ✓ **Dashboard xu hướng** `/quan-tri/xu-huong` (v1) | seq-18, usecase-4 | còn: phân khúc mới (phân cụm phiên) |
| 3.4 | **Báo cáo định kỳ** hằng tuần qua email (bộ lập lịch) | seq-18, usecase-5 | |
| 3.5 | Hiệu quả từng dự án sau khi đăng (lượt xem, lưu, lead), cho KTS xem | BFD 5.4 | |

### Giai đoạn 4: Chất lượng, đo lường, hoàn tất đồ án

| # | Việc | Xong khi |
| :-- | :-- | :-- |
| 4.1 | Đo NFR-10 (`eval_labels.py`, ≥ 85% ở Phong cách và Không gian) | có số liệu |
| 4.2 | Đo NFR-11 precision@5 trên 50 truy vấn có KTS chấm | có số liệu |
| 4.3 | Đo NFR-12: đăng một dự án 40 ảnh, ghi thời gian | có số liệu |
| 4.4 | Thử trên Safari iOS và Chrome Android (NFR-06), đo LCP bằng PageSpeed | |
| 4.5 | SEO cơ bản cho bản tĩnh: thẻ meta, `sitemap.xml`, schema.org cho dự án (SSR vẫn ngoài phạm vi) | |
| 4.6 | Cập nhật diagram theo mục 4.3; cập nhật slide và báo cáo | diagram khớp code |
| 4.7 | Kịch bản demo đầu cuối: tải ảnh → duyệt → đăng → khách tìm và chat → lead → sales xử lý → dashboard | chạy trơn trên Docker |

---

## 9. Vấn đề tồn tại và nợ kỹ thuật

1. **Hai nguồn dữ liệu dự án.** Trang chủ và `/du-an` dùng 64 dự án tĩnh (ảnh trong `src/assets/projects/`). Backend dùng 152 ảnh trong `backend/image_d3/` và DB. Duyệt ảnh xong cũng không làm thay đổi `/du-an`. Xem việc 0.1.
2. **Trang `/cong-trinh` bị ẩn** từ commit `c0fc9ee` (redirect sang `/du-an`), nên lọc 6 chiều, tìm bằng chữ, tìm bằng ảnh và link "Xem bộ lọc" ở trang Phân loại đều không truy cập được. File `CongTrinhView.vue` vẫn còn.
3. **Link chết trên menu:** "Về chúng tôi" (`/ve-chung-toi`) và "Liên hệ" (`/lien-he`) chưa có trang. `SpaceCard.vue` có link `/cong-trinh-chi-tiet#…` cũng không có route.
4. **`dist/`** có trong `.gitignore` nhưng vẫn bị git theo dõi. Sau mỗi `npm run build` phải `git restore dist`. Nên `git rm -r --cached dist` khi CI deploy Pages không cần nó nữa.
5. **Rate limit lưu trong bộ nhớ** và tính theo IP. Khởi động lại là mất; phía sau proxy cần đọc `X-Forwarded-For` (`backend/ratelimit.py`).
6. **`D3_JWT_SECRET`** phải được đặt trong `.env`. Nếu không, mỗi lần khởi động lại backend mọi người bị đăng xuất. Script chạy ngoài Docker (vd `set_role.py`) có in cảnh báo này nhưng không ảnh hưởng.
7. **Backend Docker chạy CPU**: ingest chậm (vài giây mỗi ảnh). Muốn nhanh thì chạy backend ngoài Docker với GPU.
8. **Hội thoại chỉ lưu trong `lead.conversation`**, không có bảng HoiThoai/TinNhan riêng như class diagram.
9. **Hotspot chỉ có nhãn chữ**, chưa trỏ tới bản ghi món đồ.
10. **Tài khoản thử `qt01-walk@example.com`** (lead_architect) tạo khi chạy thử quy trình duyệt. Tài khoản này được giữ vì `review_log` tham chiếu tới. Nên hạ xuống `visitor` khi demo thật.
11. **Quyền công bố 9 ảnh đã đăng** được tick để demo (ảnh lấy từ Behance). Khi dùng thật phải xin quyền khách.
12. **`openspec validate`** có lúc báo 0 delta với change đã xong. Đây là lỗi của công cụ, có thể bỏ qua.
13. **Thiếu tài liệu 02–05** (bộ câu hỏi phỏng vấn, user story, mô hình hoá, taxonomy) mà BAD tham chiếu.

---

## 10. Quy ước làm việc

- **Nhánh:** mỗi người một nhánh (`Tuan`, `tung_dev`, …), gộp vào `main` qua PR. Push vào `main` sẽ tự deploy GitHub Pages (`.github/`).
- **Trước khi gộp `main`:** báo nhau khi đổi route hoặc menu, vì frontend và backend đang được hai người sửa song song (xem mục 9.2).
- **OpenSpec:** mỗi tính năng là một change: `proposal.md` (vì sao), `design.md` (cách làm), `specs/` (yêu cầu + kịch bản), `tasks.md` (checklist). Làm xong thì archive để spec được gộp vào `openspec/specs/`. Backend có thư mục `backend/openspec/` riêng.
- **Bí mật:** không bao giờ commit `sa-key.json`, `.env`, `*-key.json` (đã có trong `.gitignore`). Tài khoản thử dùng email `@example.com`.
- **Cổng:** 8080 (web Docker), 8001 (backend), 5432 (DB), 5173 (Vite dev). Cổng 8000 để trống.
- **Ngôn ngữ:** nội dung hiển thị cho khách bằng tiếng Việt có dấu; mã định danh (`ma_dinh_danh`) không dấu, dùng gạch dưới.
- **Test:** thêm test cho mỗi thay đổi backend (`backend/tests/`); chạy cả pytest và vitest trước khi mở PR.

---

## 11. Phụ lục

### 11.1 Trang frontend

| Đường dẫn | Ai xem | Nội dung |
| :-- | :-- | :-- |
| `/` | mọi người | slideshow, lưới dự án, CTA, nút "Hỏi trợ lý" |
| `/du-an` | mọi người | 64 dự án tĩnh, lọc Tất cả / Nhà ở / Thương mại |
| `/du-an/:slug` | mọi người | trang dự án: gallery, lightbox, dự án trước/tiếp |
| `/cong-trinh` | mọi người | **đang chuyển sang `/du-an`** (trang lọc 6 chiều + tìm kiếm còn trong `CongTrinhView.vue`) |
| `/khong-gian/:id` | mọi người | ảnh từ DB, hotspot, bảng màu, không gian tương tự |
| `/dang-nhap` | mọi người | email / Google / Facebook |
| `/quan-tri` | architect, content, lead_architect, admin | duyệt và đăng ảnh |
| `/quan-tri/phan-loai` | lead_architect, admin | duyệt chiều phân loại AI đề xuất |
| `/khach-hang` | sales, lead_architect, admin | danh sách lead |

### 11.2 API backend (`http://localhost:8001`, Swagger ở `/docs`)

| Method | Đường dẫn | Quyền | Việc |
| :-- | :-- | :-- | :-- |
| GET | `/spaces` | công khai (nháp cần staff) | danh sách không gian, lọc theo trạng thái |
| GET | `/spaces/{id}` | công khai | chi tiết |
| GET | `/spaces/{id}/similar` | công khai | không gian tương tự |
| GET | `/search?q=` | công khai | tìm bằng chữ |
| POST | `/search/image` | công khai, 10/phút | tìm bằng ảnh (jpg/png/webp, ≤ 8 MB) |
| POST | `/spaces/ingest` | staff | tải ảnh + chạy pipeline AI |
| PATCH | `/spaces/{id}` | staff / content | sửa nhãn, mô tả, hotspot, chuyển trạng thái |
| POST | `/spaces/advance` | staff / approver | chuyển trạng thái hàng loạt |
| PUT | `/spaces/tags` | staff | gắn tag theo ảnh hoặc cả dự án |
| POST | `/events` | công khai, 120/phút | ghi lượt xem (theo đồng ý) |
| POST | `/chat` | công khai, 20/phút | trợ lý |
| POST | `/leads` | công khai, 5/10 phút | form liên hệ tạo lead (nguồn `form`), kèm hồ sơ hành vi nếu khách đồng ý |
| GET | `/leads` | sales, approver | lead mọi nguồn, lọc `?nguon=form\|brief\|chat`; lead brief kèm ảnh, ghi chú, mã chia sẻ |
| GET | `/spaces?ids=1,2,3` | công khai | các không gian theo id (≤ 60), cho bộ sưu tập trong trình duyệt |
| GET / PUT / DELETE | `/collections/me`, `/collections/me/items/{space_id}` | đã đăng nhập, 120/phút | bộ sưu tập của tài khoản: xem, lưu/sửa ghi chú, bỏ |
| POST | `/collections/me/merge` | đã đăng nhập | gộp bộ sưu tập trong trình duyệt vào tài khoản khi đăng nhập |
| GET | `/collections/shared/{mã}` | công khai | bản đã gửi, chỉ xem: ảnh, ghi chú, tóm tắt, không có thông tin liên hệ |
| POST | `/briefs` | công khai, chung giới hạn 5/10 phút với `/leads` | gửi bộ sưu tập cho kiến trúc sư → lead nguồn `brief` |
| POST | `/estimates` | công khai, 30/phút | ước tính từ bảng đơn giá, không lưu gì |
| POST | `/estimates/send` | công khai, chung giới hạn với `/leads` | nhận bản chi tiết qua email → lead nguồn `estimate` (máy chủ tự tính lại) |
| GET / PUT | `/prices`, `/prices/{id}` | approver | bảng đơn giá D8; lưu một ô thì ô đó thành `d3` (không còn là giá mẫu) |
| GET | `/analytics/overview?days=7\|30\|90` | sales, approver | điểm quan tâm, xu hướng, cảnh báo, tổng, lead theo tuần, top không gian; chỉ số tổng hợp, không có dữ liệu cá nhân |
| GET | `/taxonomy` | công khai | các chiều và giá trị (cho bộ lọc) |
| POST | `/taxonomy/{dim_id}/values` | lead_architect | thêm giá trị |
| PATCH | `/taxonomy/values/{id}` | lead_architect | đổi tên giá trị |
| POST | `/taxonomy/values/{id}/merge` | lead_architect | gộp giá trị |
| GET | `/taxonomy/candidates` | approver | đề xuất chiều mới |
| POST | `/taxonomy/candidates/{id}/accept` | approver | chấp nhận, AI gắn nhãn thư viện |
| POST | `/taxonomy/candidates/{id}/reject` | approver | từ chối |
| POST | `/auth/register`, `/auth/login`, `/auth/refresh` | công khai | tài khoản, JWT |
| GET | `/auth/me` | đã đăng nhập | thông tin người dùng |
| GET | `/auth/google/*`, `/auth/facebook/*` | công khai | OAuth |
| PATCH | `/users/{id}/role` | admin | đổi role |

### 11.3 Bảng dữ liệu (`backend/schema.sql`)

| Bảng | Nội dung |
| :-- | :-- |
| `space` | mỗi ảnh/không gian: đường dẫn, nhãn AI, màu, hotspot, embedding SigLIP2, `review_status` |
| `space_text` | mô tả dài của ảnh + embedding Vertex (RAG) |
| `app_user` | tài khoản, role |
| `review_log` | nhật ký duyệt, sửa, gán nhãn lại |
| `kb_chunk` | đoạn tri thức trợ lý + embedding |
| `lead` | khách tiềm năng mọi nguồn (`nguon`: form, chat, brief, estimate): họ tên, SĐT, email, lời nhắn, ngữ cảnh trang/dự án, hồ sơ hành vi (bản chụp), và với chat thì ý định, yêu cầu, hội thoại |
| `bo_suu_tap`, `bo_suu_tap_anh` | bộ sưu tập: `dang_luu` (một cái mỗi tài khoản) và `da_gui` (bản cố định của mỗi brief, có `ma_chia_se`); ảnh + ghi chú (≤ 300 ký tự) |
| `don_gia` | bảng đơn giá D8: 5 loại nhà × 4 hạng mục × 3 gói, khoảng VND/m², `nguon` `mau` (giá mẫu) / `d3` (nhân viên đặt) |
| `chieu_phan_loai`, `gia_tri_phan_loai`, `space_gia_tri` | phân loại và nhãn của từng không gian |
| `ung_vien_phan_loai` | đề xuất chiều mới chờ duyệt |
| `khoang_trong_tri_thuc` | câu hỏi trợ lý chưa trả lời được |
| `phien_truy_cap`, `su_kien`, `su_kien_an_danh` | hành vi có đồng ý, bộ đếm ẩn danh |

### 11.4 Script backend (chạy trong `backend/`)

| Script | Việc |
| :-- | :-- |
| `ingest.py <thư mục>` | nạp ảnh: phân loại, màu, YOLO, embedding, ghi DB |
| `relabel.py` | gán nhãn lại ảnh nháp (không ghi đè nhãn người đã duyệt) |
| `reembed.py` | tính lại embedding |
| `generate_transcripts.py` | mô tả dài từng ảnh cho RAG |
| `generate_kb.py` | sinh nháp mô tả dự án và câu hỏi đánh giá |
| `python -m pipeline.assistant <file.json>` | nạp kho tri thức |
| `python -m pipeline.discovery [--dry-run]` | chạy AI đề xuất chiều phân loại mới |
| `seed_taxonomy.py` | nạp phân loại gốc từ `kb/taxonomy_seed.json` |
| `set_role.py <email> <role>` | đổi role |
| `eval_labels.py`, `eval_assistant.py`, `eval_photo_rag.py` | đo độ chính xác nhãn, truy hồi chatbot, RAG ảnh |
