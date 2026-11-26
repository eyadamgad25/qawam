"""Smoke test for ml/pain/teacher_train.py with a tiny random BERT (no download). Skipped where torch is not installed."""

import sys
from pathlib import Path

import numpy as np
import pytest

torch = pytest.importorskip("torch")
transformers = pytest.importorskip("transformers")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ml" / "pain"))
import teacher_train as tt  # noqa: E402


def tiny(tmp_path):
    texts = [f"ألم في الصدر {i}" if i % 2 else f"شد في الرقبة {i}" for i in range(40)]
    chars = sorted({c for t in texts for c in t if not c.isspace()})
    (tmp_path / "vocab.txt").write_text("\n".join(["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]", *chars]), encoding="utf-8")
    tok = transformers.BertTokenizerFast(str(tmp_path / "vocab.txt"), tokenize_chinese_chars=False)
    cfg = transformers.BertConfig(vocab_size=len(chars) + 5, hidden_size=16, num_hidden_layers=1, num_attention_heads=2,
                                  intermediate_size=32, num_labels=2)
    return texts, tok, transformers.BertForSequenceClassification(cfg)


def test_trains_and_scores_every_text_as_a_probability(tmp_path):
    texts, tok, model = tiny(tmp_path)
    y = np.array([i % 2 for i in range(40)])
    p = tt.train_and_score(model, tok, texts, y, np.ones(40), texts + ["جديد"], epochs=1)
    assert p.shape == (41,) and np.all((p >= 0) & (p <= 1))


def test_stops_without_a_graphics_card(monkeypatch, capsys):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    assert tt.main(["nowhere", "out"]) == 2
    assert "graphics card" in capsys.readouterr().out
