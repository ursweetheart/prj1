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

Biến của frontend (tuỳ chọn): `VITE_BACKEND_URL` (mặc định `http://localhost:8000`), địa chỉ backend cho nút đăng nhập Google/Facebook.

Trang quản trị: `/quan-tri` (kiến trúc sư duyệt không gian), `/khach-hang` (sales xem lead); cả hai cần đăng nhập đúng role. Tài khoản tự đăng ký luôn là `visitor`; admin nâng role bằng `PATCH /users/{id}/role` hoặc `python set_role.py`.

Bản deploy: https://ursweetheart.github.io/prj1/ (trang tĩnh nên tìm kiếm AI chỉ chạy khi bật backend).

## Backend

Chạy mọi lệnh trong `backend/`.

```
docker compose up -d                              # Postgres + pgvector (project "prj1", volume prj1_pgdata)
python -m venv .venv && .venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python ingest.py image_d3           # gán nhãn + embedding ảnh, ghi vào DB
.venv\Scripts\python -m pipeline.assistant kb/sample.json   # nạp kho tri thức cho chatbot
.venv\Scripts\python -m uvicorn api:app --port 8000
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
| `D3_FRONTEND_URL` | sau khi đăng nhập OAuth, backend chuyển về địa chỉ này (vd `http://localhost:5173/prj1/`) kèm token; để trống thì trả JSON |
| `GEMINI_API_KEY` hoặc `GOOGLE_API_KEY` | phân loại ảnh bằng Gemini |
| `GOOGLE_APPLICATION_CREDENTIALS` / `VERTEX_SA_KEY` | khoá service account (`sa-key.json`, đã nằm trong `.gitignore`, không commit) |

Kho tri thức: copy `backend/kb/template.json`, điền nội dung thật (mỗi đoạn có `kind`, `title` duy nhất, `match`, `content`), rồi nạp bằng lệnh trên. Lệnh nạp báo lỗi nếu thiếu trường, trùng tiêu đề hoặc sai `kind`, và cảnh báo nếu còn dữ liệu mẫu.

Dữ liệu `backend/kb/sample.json` là **dữ liệu mẫu** (đánh dấu `[DỮ LIỆU MẪU]`), cần thay bằng bảng giá và FAQ thật của D3 Studio.
`python eval_assistant.py` đo chất lượng truy hồi của chatbot trên `eval/chat_eval.json`.
