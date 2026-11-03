"""Train the on-device pain red-flag model and export it to web/src/painModel.json.

Logistic regression on distinct character 2-4-grams (pain_text.char_ngrams), each scaled by
1 / sqrt(number of n-grams in the note), balanced class weights, L2. Plain numpy, no new
dependency. Trained on training-notes.jsonl only; dev/test stay for evaluation, and the
threshold is the fixed 0.5 probability (not tuned on dev or test).

  py -3.14 ml\\pain\\train_flag_model.py
"""

import json
import math
from pathlib import Path

import numpy as np

from pain_text import NGRAM_MAX, NGRAM_MIN, char_ngrams

HERE = Path(__file__).parent
REPO = HERE.parents[1]
OUT = REPO / "web" / "src" / "painModel.json"
L2, STEPS, RATE, MIN_DF = 1e-3, 3000, 2.0, 2


def load(name: str) -> list[dict]:
    return [json.loads(l) for l in (HERE / name).read_text(encoding="utf-8").splitlines() if l.strip()]


def design(notes: list[dict], vocab: dict[str, int]) -> np.ndarray:
    x = np.zeros((len(notes), len(vocab)), dtype=np.float32)
    for row, note in enumerate(notes):
        grams = char_ngrams(note["text"])
        for gram in grams:
            if gram in vocab:
                x[row, vocab[gram]] = 1.0 / math.sqrt(len(grams))
    return x


def fit(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, float]:
    weight = np.where(y == 1, len(y) / (2 * y.sum()), len(y) / (2 * (len(y) - y.sum())))
    w, b = np.zeros(x.shape[1]), 0.0
    for _ in range(STEPS):
        p = 1 / (1 + np.exp(-(x @ w + b)))
        g = weight * (p - y) / len(y)
        w -= RATE * (x.T @ g + L2 * w)
        b -= RATE * g.sum()
    return w, b


def main() -> None:
    train = load("training-notes.jsonl")
    df: dict[str, int] = {}
    for note in train:
        for gram in char_ngrams(note["text"]):
            df[gram] = df.get(gram, 0) + 1
    vocab = {g: i for i, g in enumerate(sorted(g for g, c in df.items() if c >= MIN_DF))}
    y = np.array([float(n["red_flag"]) for n in train])
    w, b = fit(design(train, vocab), y)

    def score(text: str) -> float:
        grams = char_ngrams(text)
        return b + sum(w[vocab[g]] for g in grams if g in vocab) / math.sqrt(len(grams))

    train_acc = np.mean([(score(n["text"]) > 0) == n["red_flag"] for n in train])
    weights = {g: round(float(w[i]), 4) for g, i in vocab.items() if abs(w[i]) >= 5e-4}
    checks = [n["text"] for n in load("synthetic-notes.jsonl")[::10]]
    # parity checks use the rounded weights the app will load
    def rounded(text: str) -> float:
        grams = char_ngrams(text)
        return round(b, 4) + sum(weights.get(g, 0.0) for g in grams) / math.sqrt(len(grams))

    model = {
        "about": "Pain red-flag model: logistic regression on character n-grams. Trained on synthetic notes (ml/pain/training-notes.jsonl), not on patient text; not reviewed by a physiotherapist. Used only together with the word list (flag if either flags).",
        "ngram": [NGRAM_MIN, NGRAM_MAX],
        "bias": round(b, 4),
        "threshold": 0.0,
        "weights": weights,
        "checks": [{"text": t, "score": round(rounded(t), 6)} for t in checks],
    }
    OUT.write_text(json.dumps(model, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"vocab {len(vocab)}, kept {len(weights)} weights, train accuracy {train_acc:.3f}, {OUT.stat().st_size / 1024:.0f} KB -> {OUT}")


if __name__ == "__main__":
    main()
