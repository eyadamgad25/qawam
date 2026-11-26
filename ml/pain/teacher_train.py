"""Fine-tune the two Arabic teachers on Kaggle's graphics card and score every Shifaa title and synthetic note.

Spec: docs/superpowers/specs/2026-11-26-arabic-pain-model-design.md. Labels: teacher_data.training_set (same as the phone
model). Settings fixed before any score: 3 epochs, learning rate 2e-5, max length 64, batch 32, seed 20261126.
Writes teacher_scores.csv: kind,key,marbert,camelbert (kind "title" -> consultation number, "note" -> file:line index).
Scores only: no text is written.

  python ml/pain/teacher_train.py <folder or zip with Shifaa CSVs> <output folder>
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

TEACHERS = {"marbert": "UBC-NLP/MARBERTv2", "camelbert": "CAMeL-Lab/bert-base-arabic-camelbert-da"}
EPOCHS, LR, MAX_LEN, BATCH, SEED = 3, 2e-5, 64, 32, 20261126
NOTE_FILES = ("synthetic-notes.jsonl", "training-notes.jsonl")


def train_and_score(model, tokenizer, texts, y, weight, score_texts, device="cpu", epochs=EPOCHS):
    """Weighted cross-entropy fine-tuning, then P(warning sign) for each of score_texts."""
    import torch

    torch.manual_seed(SEED)
    rng = np.random.default_rng(SEED)
    model.to(device).train()
    opt = torch.optim.AdamW(model.parameters(), lr=LR)
    steps = epochs * -(-len(texts) // BATCH)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda s: max(0.0, 1 - s / steps))
    amp = device == "cuda"
    for _ in range(epochs):
        for idx in np.array_split(rng.permutation(len(texts)), -(-len(texts) // BATCH)):
            enc = tokenizer([texts[i] for i in idx], truncation=True, max_length=MAX_LEN, padding=True, return_tensors="pt").to(device)
            with torch.autocast("cuda", enabled=amp):
                logits = model(**enc).logits.float()
            loss = torch.nn.functional.cross_entropy(logits, torch.tensor(y[idx], device=device), reduction="none")
            w = torch.tensor(weight[idx], device=device, dtype=torch.float32)
            (loss * w).sum().div(w.sum()).backward()
            opt.step()
            sched.step()
            opt.zero_grad()
    model.eval()
    out = np.empty(len(score_texts))
    order = np.argsort([len(t) for t in score_texts])  # similar lengths together: less padding
    with torch.no_grad():
        for idx in np.array_split(order, max(1, -(-len(order) // 256))):
            enc = tokenizer([score_texts[i] for i in idx], truncation=True, max_length=MAX_LEN, padding=True, return_tensors="pt").to(device)
            with torch.autocast("cuda", enabled=amp):
                out[idx] = torch.softmax(model(**enc).logits.float(), -1)[:, 1].cpu().numpy()
    return out


def main(argv: list[str]) -> int:
    import torch
    from shifaa_eval import load
    from teacher_data import training_set
    from train_flag_model import load as load_notes
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    if not torch.cuda.is_available():
        print("No graphics card. On Kaggle: Settings -> Accelerator -> GPU T4 x2 (needs a phone-verified account), then run again.")
        return 2
    source, out = Path(argv[0]), Path(argv[1])
    rows = load(source)
    train_notes = load_notes("training-notes.jsonl")
    texts, y, weight = training_set(rows, train_notes)
    keys = [("title", str(r["id"])) for r in rows]
    score_texts = [r["title"] for r in rows]
    for name in NOTE_FILES:
        for i, n in enumerate(load_notes(name)):
            keys.append(("note", f"{name}:{i}"))
            score_texts.append(n["text"])
    print(f"{len(rows)} titles, training on {len(texts)} texts; scoring {len(score_texts)}")
    scores = {}
    for short, hub in TEACHERS.items():
        tok = AutoTokenizer.from_pretrained(hub)
        model = AutoModelForSequenceClassification.from_pretrained(hub, num_labels=2)
        scores[short] = train_and_score(model, tok, texts, y, weight, score_texts, device="cuda")
        print(short, "done")
        del model
        torch.cuda.empty_cache()
    out.mkdir(parents=True, exist_ok=True)
    with (out / "teacher_scores.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["kind", "key", *TEACHERS])
        for i, (kind, key) in enumerate(keys):
            w.writerow([kind, key, *(f"{scores[t][i]:.5f}" for t in TEACHERS)])
    print("wrote", out / "teacher_scores.csv")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent))
    raise SystemExit(main(sys.argv[1:]))
