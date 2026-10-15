"""Evaluate retrieval on eval/chat_eval.json and suggest the MIN_SCORE threshold.  python eval_assistant.py [questions.json]"""
import json
import sys

sys.stdout.reconfigure(encoding="utf-8")  # Vietnamese output on the Windows console

from pipeline.assistant import MIN_SCORE, retrieve

cases = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "eval/chat_eval.json", encoding="utf-8"))
known, unknown = [], []
for c in cases:
    top = retrieve(c["q"], 1)[0]
    (known if c["expect"] else unknown).append((top[4], top[2] == c["expect"], c["q"]))

hit = sum(ok for _, ok, _ in known)
print(f"top-1 correct: {hit}/{len(known)}")
lo = min((s for s, ok, _ in known if ok), default=None)
hi = max((s for s, _, _ in unknown), default=None)
if lo is not None and hi is not None:  # a file with only on-topic (or only off-topic) questions has no gap to report
    print(f"lowest correct score {lo:.3f}; highest off-topic score {hi:.3f}  (a threshold between them separates both)")
answered = sum(s >= MIN_SCORE and ok for s, ok, _ in known)
refused = sum(s < MIN_SCORE for s, _, _ in unknown)
print(f"at MIN_SCORE={MIN_SCORE}: answered correctly {answered}/{len(known)}, refused off-topic {refused}/{len(unknown)}")
for s, ok, q in sorted(known + unknown):
    print(f"  {s:.3f} {'ok ' if ok else '   '} {q}")
