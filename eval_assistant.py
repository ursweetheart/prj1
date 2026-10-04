"""Evaluate retrieval on eval/chat_eval.json and suggest the MIN_SCORE threshold.  python eval_assistant.py"""
import json

from pipeline.assistant import MIN_SCORE, retrieve

cases = json.load(open("eval/chat_eval.json", encoding="utf-8"))
known, unknown = [], []
for c in cases:
    top = retrieve(c["q"], 1)[0]
    (known if c["expect"] else unknown).append((top[4], top[2] == c["expect"], c["q"]))

hit = sum(ok for _, ok, _ in known)
print(f"top-1 correct: {hit}/{len(known)}")
lo, hi = min(s for s, ok, _ in known if ok), max(s for s, _, _ in unknown)
print(f"lowest correct score {lo:.3f}; highest off-topic score {hi:.3f}  (a threshold between them separates both)")
answered = sum(s >= MIN_SCORE and ok for s, ok, _ in known)
refused = sum(s < MIN_SCORE for s, _, _ in unknown)
print(f"at MIN_SCORE={MIN_SCORE}: answered correctly {answered}/{len(known)}, refused off-topic {refused}/{len(unknown)}")
for s, ok, q in sorted(known + unknown):
    print(f"  {s:.3f} {'ok ' if ok else '   '} {q}")
