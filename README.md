# D3 Studio

Website portfolio thiết kế nội thất tích hợp AI (tìm không gian tương tự, trợ lý hỏi đáp).

```
.                frontend (Vue 3 + Vite), deploy lên GitHub Pages
├── backend/     API FastAPI, pipeline AI, Postgres + pgvector, tests
├── docs/        tài liệu khảo sát
├── openspec/    spec của frontend (backend có openspec/ riêng)
└── .github/     workflow deploy Pages (chạy khi push vào main)
```

## Frontend

```
npm ci
npm run dev       # http://localhost:5173/prj1/ ; /api và /images được proxy sang backend :8000
npm run build     # ra dist/, giống bước build của CI
npm test          # vitest: kiểm tra phần phiên đăng nhập trong src/api.js
```

Biến của frontend (tuỳ chọn): `VITE_API_URL`, địa chỉ backend đã host (vd `https://api.example.com`). Để trống khi dev: frontend gọi qua proxy `/api` của Vite, nút Google/Facebook trỏ `http://localhost:8000`.

Trang quản trị: `/quan-tri` (kiến trúc sư duyệt không gian), `/khach-hang` (sales xem lead); cả hai cần đăng nhập đúng role. Tài khoản tự đăng ký luôn là `visitor`; admin nâng role bằng `PATCH /users/{id}/role` hoặc `python set_role.py`.

Bản deploy: https://ursweetheart.github.io/prj1/ (trang tĩnh nên tìm kiếm AI chỉ chạy khi bật backend).

## Backend

Chạy mọi lệnh trong `backend/`.

```
docker compose up -d                              # Postgres + pgvector (project "prj1", volume prj1_pgdata)
python -m venv .venv && .venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python ingest.py image_d3           # gán nhãn + embedding ảnh, ghi vào DB
.venv\Scripts\python -m pipeline.assistant kb/sample.json   # nạp kho tri thức cho chatbot
.venv\Scripts\python -m uvicorn api:app --port 8000 --env-file .env   # .env: copy từ .env.example, không commit
.venv\Scripts\python -m pytest                    # cần DB đang chạy và đã ingest
```

Dùng `python -m ...` thay vì chạy thẳng file trong `.venv\Scripts` (venv đã đổi đường dẫn).

Biến môi trường (tuỳ chọn, có mặc định cho dev):

| Biến | Dùng cho |
|---|---|
| `D3_DSN` | chuỗi kết nối Postgres, mặc định `postgresql://d3:d3@localhost:5432/d3` (chỉ dùng cho dev) |
| `D3_JWT_SECRET` | khoá ký JWT, đặt giá trị riêng khi chạy thật |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | đăng nhập Google. Redirect URI cần khai báo: `<backend>/auth/google/callback` |
| `FACEBOOK_APP_ID`, `FACEBOOK_APP_SECRET` | đăng nhập Facebook. Redirect URI: `<backend>/auth/facebook/callback` |
| `D3_CORS_ORIGINS` | các origin được gọi API từ trình duyệt, cách nhau bằng dấu phẩy (vd `https://ursweetheart.github.io`); trống thì không bật CORS |
| `D3_FRONTEND_URL` | sau khi đăng nhập OAuth, backend chuyển về địa chỉ này (vd `http://localhost:5173/prj1/`) kèm token; để trống thì trả JSON |
| `GEMINI_API_KEY` hoặc `GOOGLE_API_KEY` | phân loại ảnh bằng Gemini |
| `GOOGLE_APPLICATION_CREDENTIALS` / `VERTEX_SA_KEY` | khoá service account (`sa-key.json`, đã nằm trong `.gitignore`, không commit) |

Giới hạn tần suất (theo IP, trong bộ nhớ): `/chat` 20 lần/phút, đăng nhập và đăng ký 10 lần/phút, vượt thì trả 429 kèm `Retry-After`. Phía sau reverse proxy mọi người dùng chung IP của proxy nên cần đọc `X-Forwarded-For`, xem `backend/ratelimit.py`.

Kho tri thức: copy `backend/kb/template.json`, điền nội dung thật (mỗi đoạn có `kind`, `title` duy nhất, `match`, `content`), rồi nạp bằng lệnh trên. Lệnh nạp báo lỗi nếu thiếu trường, trùng tiêu đề hoặc sai `kind`, và cảnh báo nếu còn dữ liệu mẫu.

Sinh nháp mô tả dự án từ ảnh: `python generate_kb.py --dry-run` (xem trước), rồi `python generate_kb.py` (gọi Gemini qua Vertex, mỗi thư mục ảnh một lần). Ra `kb/generated.json` (các mục `project`, nội dung có dấu `[AI SINH - CHƯA DUYỆT]`) và `eval/chat_eval.generated.json` (câu hỏi đánh giá). Chỉ sinh mô tả dự án: giá, bảo hành, thời gian, chính sách không đọc ra được từ ảnh, và bộ lọc trong code từ chối mọi bản nháp có số tiền hay lời cam kết. Xem lại nội dung, xoá dấu đánh dấu ở những mục giữ lại rồi nạp; đo bằng `python eval_assistant.py eval/chat_eval.generated.json`.

Dữ liệu `backend/kb/sample.json` là **dữ liệu mẫu** (đánh dấu `[DỮ LIỆU MẪU]`), cần thay bằng bảng giá và FAQ thật của D3 Studio.
`python eval_labels.py` đo độ chính xác gán nhãn ảnh trên các không gian đã được người duyệt ở `/quan-tri` (mục tiêu ≥85%, cần ít nhất 30 ảnh đã duyệt).
`python eval_assistant.py` đo chất lượng truy hồi của chatbot trên `eval/chat_eval.json`.
