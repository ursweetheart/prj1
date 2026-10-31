"""Write a detailed description (transcript) of every photo with Gemini and embed it, for chat RAG.

    python generate_transcripts.py --dry-run
    python generate_transcripts.py [--limit N] [--redo] [--workers 4]

Resumable: photos that already have a transcript / embedding are skipped (--redo rewrites them).
Photos only show how a space looks: the transcripts never carry prices, guarantees or promises.
"""

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import psycopg
from pgvector.psycopg import register_vector

from pipeline.assistant import FORBIDDEN
from pipeline import vertex
from pipeline.multimodal_classifier import MultimodalClassifier
from pipeline.store import DSN

IMG_DIR = Path("image_d3")
PROMPT = """Bạn là kiến trúc sư nội thất của D3 Studio. Hãy viết mô tả chi tiết bằng tiếng Việt cho bức ảnh này, \
để sau này trợ lý chat dựa vào đó trả lời khách.

Nhãn AI gán trước (chỉ để tham khảo, có thể sai, hãy ưu tiên những gì thực sự nhìn thấy): {facts}

Mô tả gồm các ý: loại không gian và bố cục, công năng; vật liệu và bề mặt cụ thể (sàn, tường, trần, mặt bàn...); \
bảng màu; đồ nội thất và đồ trang trí chính; ánh sáng (tự nhiên, đèn); phong cách và cảm giác chung.
Quy tắc bắt buộc:
- Văn xuôi liền mạch, 120 đến 250 từ, không gạch đầu dòng, không tiêu đề.
- Chỉ nêu điều nhìn thấy. Không nêu giá, chi phí, diện tích, thời gian, bảo hành, cam kết, tên người hay thương hiệu.
- Không bắt đầu bằng "Bức ảnh này" hay "Trong ảnh"; đi thẳng vào không gian."""


def facts(space_type, design_style, materials) -> str:
    return (f"loại không gian {space_type or '?'}; phong cách {design_style or '?'}; "
            f"vật liệu {', '.join(materials or []) or '?'}")


def clean(text: str) -> str:
    """Return the transcript, or raise if it is empty or claims anything a photo cannot show."""
    text = " ".join(str(text).split())
    if len(text) < 80:
        raise ValueError("too short")
    if FORBIDDEN.search(text):
        raise ValueError("mentions price/warranty/promises")
    return text


def describe(row) -> str:
    sid, path, *label = row
    b64, mime = MultimodalClassifier._prepare_image_payload(IMG_DIR / path)
    parts = [{"text": PROMPT.format(facts=facts(*label))}, {"inline_data": {"mime_type": mime, "data": b64}}]
    text, _ = vertex.generate(parts, temperature=0.3, as_json=False)
    return clean(text)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    with psycopg.connect(DSN) as conn:
        register_vector(conn)
        where = "" if args.redo else "WHERE NOT EXISTS (SELECT 1 FROM space_text t WHERE t.space_id = s.id)"
        todo = conn.execute(f"SELECT s.id, s.relative_path, s.space_type, s.design_style, s.materials FROM space s {where} "
                            "ORDER BY s.id").fetchall()[: args.limit]
        print(f"{len(todo)} photos need a transcript")
        if args.dry_run:
            return
        if not vertex.available():
            sys.exit("no Vertex service-account key: set GOOGLE_APPLICATION_CREDENTIALS or put sa-key.json in backend/")

        def work(row):
            try:
                return row[0], describe(row), None
            except Exception as e:  # one bad photo must not lose the rest
                return row[0], None, f"{row[1]}: {e}"

        failed = []
        with ThreadPoolExecutor(args.workers) as pool:
            for sid, text, err in pool.map(work, todo):
                if err:
                    failed.append(err)
                    continue
                conn.execute("INSERT INTO space_text (space_id, transcript, embedding) VALUES (%s, %s, NULL) "
                             "ON CONFLICT (space_id) DO UPDATE SET transcript=EXCLUDED.transcript, embedding=NULL", (sid, text))
                conn.commit()
        # embed everything that has text but no vector yet
        rows = conn.execute("SELECT space_id, transcript FROM space_text WHERE embedding IS NULL ORDER BY space_id").fetchall()
        for i in range(0, len(rows), 16):
            chunk = rows[i:i + 16]
            for (sid, _), vec in zip(chunk, vertex.embed([t for _, t in chunk], "RETRIEVAL_DOCUMENT")):
                conn.execute("UPDATE space_text SET embedding=%s WHERE space_id=%s", (np.asarray(vec, dtype=np.float32), sid))
            conn.commit()
        print(f"done: {len(todo) - len(failed)} transcripts written, {len(rows)} embedded")
        for f in failed:
            print("FAILED", f)


if __name__ == "__main__":
    main()
