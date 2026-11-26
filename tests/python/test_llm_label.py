"""Smoke test for ml/pain/llm_label.py with a tiny random causal model (no download). Skipped where torch is not installed."""

import sys
from pathlib import Path

import numpy as np
import pytest

torch = pytest.importorskip("torch")
transformers = pytest.importorskip("transformers")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ml" / "pain"))
import llm_label as ll  # noqa: E402


def test_every_title_gets_one_probability(tmp_path):
    titles = ["ألم شديد في الصدر", "تمارين للركبة", "دوخة", ""]
    chars = sorted({c for t in titles + [ll.PROMPT] for c in t if not c.isspace()})
    (tmp_path / "vocab.txt").write_text("\n".join(["[PAD]", "[UNK]", "[CLS]", "[SEP]", "[MASK]", "yes", "no", *chars]), encoding="utf-8")
    tok = transformers.BertTokenizerFast(str(tmp_path / "vocab.txt"), tokenize_chinese_chars=False)
    cfg = transformers.LlamaConfig(vocab_size=len(chars) + 7, hidden_size=16, num_hidden_layers=1, num_attention_heads=2,
                                   num_key_value_heads=2, intermediate_size=32, max_position_embeddings=2048)
    p = ll.yes_probability(transformers.LlamaForCausalLM(cfg), tok, titles, batch=3)
    assert p.shape == (4,) and np.all((p >= 0) & (p <= 1))


def test_stops_without_a_graphics_card(monkeypatch, capsys):
    monkeypatch.setattr(torch.cuda, "is_available", lambda: False)
    assert ll.main(["nowhere", "out"]) == 2
    assert "graphics card" in capsys.readouterr().out
