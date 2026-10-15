"""Draft chatbot knowledge-base chunks (kind=project) from the images, one per project folder, plus eval questions.

    python generate_kb.py --dry-run            # what it would send, no API call
    python generate_kb.py [--limit N] [--images-per-folder 6]

Writes kb/generated.json and eval/chat_eval.generated.json. Review them, delete the marker from the content you
keep, then load:  python -m pipeline.assistant kb/generated.json
Only project descriptions are generated: prices, warranty, timelines and policies cannot be read from a photo.
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

import psycopg
import requests

from pipeline.assistant import validate_kb
from pipeline.multimodal_classifier import MultimodalClassifier
from pipeline.store import DSN

MARK = "[AI SINH - CHƯA DUYỆT]"
QUESTIONS = 5
# A photo says nothing about money, guarantees or promises: refuse any draft that makes such claims.
FORBIDDEN = re.compile(r"\d\s*(đ|đồng|vnd|vnđ|k|tr|triệu|tỷ|usd|\$)\b|bảo hành|cam kết|giảm giá|khuyến mãi|miễn phí", re.I)

PROMPT = """Bạn viết nội dung cho trợ lý chat của D3 Studio (thiết kế nội thất). Dưới đây là {n} ảnh thuộc một nhóm dự án \
và các nhãn do AI gán trước đó.

Nhãn: {facts}

Viết MỘT mục mô tả nhóm dự án này bằng tiếng Việt, chỉ dựa vào những gì nhìn thấy trong ảnh và nhãn ở trên.
Quy tắc bắt buộc:
- Không nêu giá, chi phí, diện tích, thời gian, bảo hành, cam kết, tên khách hàng hay tên người thiết kế.
- Không khẳng định điều không thấy trong ảnh.
- content: 2 đến 4 câu về phong cách, vật liệu, màu sắc, bố cục.
- match: khoảng 10 đến 15 từ, cách khách hàng thường nhắc tới dự án kiểu này (dùng để tìm kiếm).
- title: ngắn, mô tả phong cách và loại công trình, không trùng với tên thư mục.
- questions: {q} câu hỏi khác nhau mà khách có thể hỏi và mục này trả lời được. Mỗi câu phải tự đứng độc lập: nêu rõ phong cách hoặc loại công trình, không dùng "này", "đó", "dự án này"; diễn đạt tự nhiên, không lặp từ.

Chỉ trả về JSON: {{"title": "...", "match": "...", "content": "...", "questions": ["..."]}}"""


def folder_facts(rows) -> str:
    """rows: (space_type, design_style, materials, caption) of the sampled images -> one line of context."""
    types = sorted({r[0] for r in rows if r[0]})
    styles = sorted({r[1] for r in rows if r[1]})
    mats = sorted({m for r in rows for m in (r[2] or [])})[:12]
    return f"loại không gian {', '.join(types) or '?'}; phong cách {', '.join(styles) or '?'}; vật liệu {', '.join(mats) or '?'}"


def parse_reply(text: str) -> dict:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    return json.loads(text)


def to_chunk(reply: dict, folder: str) -> tuple[dict, list[str]]:
    """-> (kb chunk, eval questions). Raises ValueError when the draft is unusable."""
    chunk = {"kind": "project", "title": str(reply.get("title", "")).strip(),
             "match": str(reply.get("match", "")).strip(), "content": str(reply.get("content", "")).strip()}
    if errors := validate_kb([chunk]):
        raise ValueError(f"{folder}: " + "; ".join(errors))
    for field in ("title", "match", "content"):
        if FORBIDDEN.search(chunk[field]):
            raise ValueError(f"{folder}: {field} makes a claim about price/warranty/promises: {chunk[field]!r}")
    chunk["content"] = f"{MARK} {chunk['content']}"
    questions = [q.strip() for q in reply.get("questions", []) if isinstance(q, str) and q.strip()]
    return chunk, questions


def sample(rows, k):
    """k images spread over the folder instead of the first k (consecutive shots look alike)."""
    if len(rows) <= k:
        return rows
    return [rows[i * len(rows) // k] for i in range(k)]


def folders(per_folder):
    with psycopg.connect(DSN) as c:
        names = [r[0] for r in c.execute(
            "SELECT DISTINCT split_part(relative_path,'/',1) FROM space WHERE relative_path LIKE '%/%' ORDER BY 1")]
        names = [n for n in names if n != "uploads"]
        for name in names:
            rows = c.execute("SELECT relative_path, space_type, design_style, materials FROM space "
                             "WHERE relative_path LIKE %s ORDER BY id", (name + "/%",)).fetchall()
            yield name, sample(rows, per_folder)


def ask(clf, images, facts):
    creds = clf._get_vertex_credentials()
    url = (f"https://{clf.location}-aiplatform.googleapis.com/v1/projects/{creds.project_id}/locations/{clf.location}"
           f"/publishers/google/models/{clf.model}:generateContent")
    parts = [{"text": PROMPT.format(n=len(images), facts=facts, q=QUESTIONS)}]
    for p in images:
        b64, mime = clf._prepare_image_payload(Path("image_d3") / p)
        parts.append({"inline_data": {"mime_type": mime, "data": b64}})
    body = {"contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"response_mime_type": "application/json", "temperature": 0.4}}
    for attempt in range(1, 4):
        try:
            r = requests.post(url, headers={"Authorization": f"Bearer {creds.token}"}, json=body, timeout=120)
            r.raise_for_status()
            data = r.json()
            return parse_reply(data["candidates"][0]["content"]["parts"][0]["text"]), data.get("usageMetadata", {})
        except Exception:
            if attempt == 3:
                raise
            time.sleep(attempt * 3)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, help="only the first N folders")
    ap.add_argument("--images-per-folder", type=int, default=6)
    args = ap.parse_args()

    work = list(folders(args.images_per_folder))[: args.limit]
    if args.dry_run:
        n = sum(len(rows) for _, rows in work)
        print(f"{len(work)} folders, {n} images would be sent in {len(work)} requests (about {n * 1000} input tokens; "
              "check the current Gemini price before multiplying)")
        for name, rows in work:
            print(f"  {name}: {len(rows)} images; {folder_facts([r[1:] for r in rows])}")
        return

    clf = MultimodalClassifier()
    if not clf.sa_key_path:
        sys.exit("no Vertex service-account key: set GOOGLE_APPLICATION_CREDENTIALS or put sa-key.json in backend/")
    chunks, evals, skipped, prompt_t, out_t = [], [], [], 0, 0
    for name, rows in work:
        try:
            reply, usage = ask(clf, [r[0] for r in rows], folder_facts([r[1:] for r in rows]))
            chunk, questions = to_chunk(reply, name)
        except Exception as e:  # one bad folder must not lose the others
            skipped.append(f"{name}: {e}")
            continue
        prompt_t += usage.get("promptTokenCount", 0)
        out_t += usage.get("candidatesTokenCount", 0) + usage.get("thoughtsTokenCount", 0)
        chunks.append(chunk)
        evals += [{"q": q, "expect": chunk["title"]} for q in questions]
        print(f"ok   {name}: {chunk['title']}")

    if errors := validate_kb(chunks):  # e.g. two folders got the same title
        skipped += errors
    Path("kb/generated.json").write_text(json.dumps(chunks, ensure_ascii=False, indent=2), encoding="utf-8")
    Path("eval/chat_eval.generated.json").write_text(json.dumps(evals, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{len(chunks)} chunks -> kb/generated.json, {len(evals)} questions -> eval/chat_eval.generated.json")
    print(f"tokens: {prompt_t} in, {out_t} out (thinking included); price it with the current Gemini rate card")
    for s in skipped:
        print("SKIPPED", s)


if __name__ == "__main__":
    main()
