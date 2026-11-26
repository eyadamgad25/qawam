"""Kaggle run 1: an open LLM reads each Shifaa title against the written codebook and gives P(yes). Numbers only.

Spec: docs/superpowers/specs/2026-11-26-llm-pain-labels-design.md. The prompt is fixed here, before any score, and is never
tuned; only the yes-threshold is chosen afterwards, on blind set 1 (ml/pain/llm_gate.py).
Writes llm_scores.csv: set,id,p_yes (set = blind1, blind2, blind3 or train).

  python ml/pain/llm_label.py <folder or zip with Shifaa CSVs> <output folder>
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

MODEL = "Qwen/Qwen2.5-7B-Instruct"
BATCH = 32
PROMPT = (
    "You label short Arabic medical question titles for a home exercise app.\n"
    "Question: does the title say that the person (or someone they ask about) has one of these warning signs NOW?\n"
    "1. chest pain or chest pressure or tightness\n"
    "2. difficulty breathing or shortness of breath\n"
    "3. calf pain or swelling\n"
    "4. fever or shivering\n"
    "5. discharge from a wound\n"
    "6. a swollen, hot or red knee\n"
    "7. numbness or tingling\n"
    "8. dizziness or fainting\n"
    "9. sharp, sudden or severe pain\n"
    "Answer no if the title asks about a symptom in general (causes, treatment, a topic), or if the symptom is denied or over.\n"
    "Title: {title}\n"
    "Answer with one word: yes or no."
)


def prompt_text(tok, title: str) -> str:
    content = PROMPT.format(title=title)
    if getattr(tok, "chat_template", None):
        return tok.apply_chat_template([{"role": "user", "content": content}], tokenize=False, add_generation_prompt=True)
    return content + "\n"


def yes_probability(model, tok, titles: list[str], device: str = "cpu", batch: int = BATCH) -> np.ndarray:
    """Softmax over the 'yes' and 'no' answer tokens at the first answer position, so every title gets a number."""
    import torch

    yes, no = (tok.encode(w, add_special_tokens=False)[0] for w in ("yes", "no"))
    tok.padding_side = "left"
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model.eval()
    out = np.empty(len(titles))
    with torch.no_grad():
        for start in range(0, len(titles), batch):
            enc = tok([prompt_text(tok, t) for t in titles[start:start + batch]], return_tensors="pt", padding=True).to(device)
            last = model(**enc).logits[:, -1, :].float()
            out[start:start + batch] = torch.softmax(last[:, [yes, no]], -1)[:, 0].cpu().numpy()
    return out


def main(argv: list[str]) -> int:
    import torch
    from shifaa_eval import blind_sample, blind_sample2, blind_sample3, load
    from teacher_data import training_rows
    from transformers import AutoModelForCausalLM, AutoTokenizer

    if not torch.cuda.is_available():
        print("No graphics card. On Kaggle: Settings -> Accelerator -> GPU T4 x2 (needs a phone-verified account), then run again.")
        return 2
    rows = load(Path(argv[0]))
    pos, neg = training_rows(rows)
    sets = [("blind1", blind_sample(rows)), ("blind2", blind_sample2(rows)), ("blind3", blind_sample3(rows)), ("train", pos + neg)]
    tok = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.float16, device_map="auto")
    out = Path(argv[1])
    out.mkdir(parents=True, exist_ok=True)
    with (out / "llm_scores.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["set", "id", "p_yes"])
        for name, part in sets:
            p = yes_probability(model, tok, [r["title"] for r in part], device=model.device)
            w.writerows([name, r["id"], f"{x:.5f}"] for r, x in zip(part, p))
            print(name, len(part), "done")
    print("wrote", out / "llm_scores.csv")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent))
    raise SystemExit(main(sys.argv[1:]))
