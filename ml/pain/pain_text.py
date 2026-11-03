"""Text features shared by the pain red-flag model's trainer and the app (web/src/painModel.ts).

normalize() is a copy of normalizeArabicText in web/src/painTriage.ts; char_ngrams() matches
painModel.ts. The exported model carries check scores so a web test catches any drift.
"""

import re
import unicodedata

NGRAM_MIN, NGRAM_MAX = 2, 4

_DIACRITICS = re.compile("[ً-ٰٟۖ-ۭ]")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = _DIACRITICS.sub("", text).replace("ـ", "")
    text = re.sub("[أإآٱ]", "ا", text)
    text = re.sub("[ىئ]", "ي", text)
    text = "".join(str(ord(c) - 0x0660) if "٠" <= c <= "٩" else str(ord(c) - 0x06F0) if "۰" <= c <= "۹" else c for c in text)
    return re.sub(r"\s+", " ", text).strip().lower()


def char_ngrams(text: str) -> set[str]:
    """Distinct character n-grams of the normalised text, padded with one space each side."""
    padded = f" {normalize(text)} "
    return {padded[i : i + n] for n in range(NGRAM_MIN, NGRAM_MAX + 1) for i in range(len(padded) - n + 1)}
