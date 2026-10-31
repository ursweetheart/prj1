"""How well do the photo descriptions cover questions? Picks MIN_TEXT_SCORE and shows real answers.

    python eval_photo_rag.py                      # on-topic: eval/chat_eval.generated.json, off-topic: chat_eval.json
    python eval_photo_rag.py --answers 5          # also let Gemini answer the first 5 on-topic questions

Drafts are included (published_only=False) so it works before anything is published.
"""
import argparse
import json
import sys

from pipeline.assistant import MIN_TEXT_SCORE, answer_from_photos, retrieve_photos

sys.stdout.reconfigure(encoding="utf-8")
ap = argparse.ArgumentParser()
ap.add_argument("--on", default="eval/chat_eval.generated.json")
ap.add_argument("--off", default="eval/chat_eval.json")
ap.add_argument("--answers", type=int, default=0)
args = ap.parse_args()

on = [c["q"] for c in json.load(open(args.on, encoding="utf-8")) if c["expect"]]
off = [c["q"] for c in json.load(open(args.off, encoding="utf-8")) if not c["expect"]]
top = lambda q: retrieve_photos(q, 4, published_only=False)
on_scores = sorted(top(q)[0][5] for q in on)
off_scores = sorted(top(q)[0][5] for q in off)
print(f"on-topic  best cosine: min {on_scores[0]:.3f}  median {on_scores[len(on_scores) // 2]:.3f}  ({len(on)} questions)")
print(f"off-topic best cosine: max {off_scores[-1]:.3f}  median {off_scores[len(off_scores) // 2]:.3f}  ({len(off)} questions)")
print(f"at MIN_TEXT_SCORE={MIN_TEXT_SCORE}: on-topic passing {sum(s >= MIN_TEXT_SCORE for s in on_scores)}/{len(on)}, "
      f"off-topic blocked {sum(s < MIN_TEXT_SCORE for s in off_scores)}/{len(off)}")
for q in on[: args.answers]:
    r = answer_from_photos(q, None, top(q))
    print(f"\nQ: {q}\nA: {r['answer'] if r else '(cannot answer)'}")
