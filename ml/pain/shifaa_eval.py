"""The pain check on real Arabic consultations (Shifaa, Kaggle, Apache 2.0). Counts only: texts stay in data/.

Rules: docs/superpowers/specs/2026-11-25-pain-check-real-text.md, written before any score.

  py -3.14 ml\\pain\\shifaa_eval.py sample     draws the blind sample -> data/derived/shifaa/blind.jsonl
  (label it: data/derived/shifaa/labels.json, {"1": true, ...})
  py -3.14 ml\\pain\\shifaa_eval.py score
"""

from __future__ import annotations

import csv
import io
import json
import random
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ARCHIVE = REPO / "data" / "raw" / "shifaa" / "archive.zip"
OUT = REPO / "data" / "derived" / "shifaa"
SYMPTOM = ("وخزات وآلام ومشاكل الصدر", "وخزات وآلام القلب", "ضيق التنفس ومشاكل الرئتين - ضيق التنفس", "الدوخة والدوار",
           "الإغماء والغيبوبة", "التنميل", "تورم الأقدام", "الجلطة الدماغية")
ORDINARY = ("الشد العضلي وآلام العضلات", "آلام أسفل الظهر", "آلام الرقبة", "آلام الركبة", "مشاكل الكتفين", "ممارسة الرياضة")
SEED = 20261125


def load() -> list[dict[str, Any]]:
    csv.field_size_limit(10**8)
    rows = []
    z = zipfile.ZipFile(ARCHIVE)
    for name in (n for n in z.namelist() if n.endswith(".csv")):
        for r in csv.DictReader(io.TextIOWrapper(z.open(name), encoding="utf-8", errors="replace", newline="")):
            number = "".join(c for c in r["Consultation Number"] or "" if c.isdigit())
            if not number or not (r["Question Title"] or "").strip():
                continue
            diagnosis = r["Hierarchical Diagnosis"] or ""
            kind = "symptom" if diagnosis.endswith(SYMPTOM) else "ordinary" if diagnosis.endswith(ORDINARY) else "other"
            rows.append({"id": int(number), "file": Path(name).stem, "kind": kind, "diagnosis": diagnosis,
                         "title": r["Question Title"].strip(), "question": (r["Question"] or "").strip()})
    unique = {r["id"]: r for r in rows}
    return list(unique.values())


def target(r: dict[str, Any]) -> bool:
    """The people this app is for: bone, muscle and sports consultations."""
    return r["file"] in ("Bone_Diseases", "Muscular_Diseases") or "الرياضة" in r["diagnosis"]


def blind_sample(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """150 target titles + 100 from symptom categories, odd consultation numbers only, shuffled."""
    rng = random.Random(SEED)
    odd = sorted((r for r in rows if r["id"] % 2), key=lambda r: r["id"])
    a = rng.sample([r for r in odd if target(r)], 150)
    taken = {r["id"] for r in a}
    b = rng.sample([r for r in odd if r["kind"] == "symptom" and r["id"] not in taken], 100)
    picked = [{**r, "group": "target"} for r in a] + [{**r, "group": "symptom"} for r in b]
    rng.shuffle(picked)
    return picked


def run_app_check(texts: list[str], model: Path | None = None) -> list[dict[str, Any]]:
    """The app's TypeScript check on every text, with the shipped model or another model file, bundled by rolldown (part of Vite)."""
    OUT.mkdir(parents=True, exist_ok=True)
    bundle, source, result = OUT / "painBatch.cjs", OUT / "texts.json", OUT / "flags.json"
    source.write_text(json.dumps(texts, ensure_ascii=False), encoding="utf-8")
    rolldown = REPO / "node_modules" / "rolldown" / "bin" / "cli.mjs"
    subprocess.run(["node", str(rolldown), str(HERE / "pain_batch.ts"), "--platform", "node", "--format", "cjs", "--file", str(bundle),
                    "--logLevel", "silent"], check=True)
    subprocess.run(["node", str(bundle), str(source), str(result), *([str(model)] if model else [])], check=True)
    return json.loads(result.read_text(encoding="utf-8"))


def confusion(y: list[bool], p: list[bool]) -> dict[str, Any]:
    tp = sum(a and b for a, b in zip(y, p, strict=True))
    fp = sum(b and not a for a, b in zip(y, p, strict=True))
    fn, tn = sum(y) - tp, len(y) - sum(y) - fp
    f1 = 2 * tp / (2 * tp + fp + fn) if tp else 0.0
    nf = 2 * tn / (2 * tn + fp + fn) if tn else 0.0
    return {"n": len(y), "positive": sum(y), "recall": round(tp / max(1, sum(y)), 3), "false_alarm_rate": round(fp / max(1, fp + tn), 3),
            "precision": round(tp / max(1, tp + fp), 3), "accuracy": round((tp + tn) / max(1, len(y)), 3), "f1": round(f1, 3),
            "macro_f1": round((f1 + nf) / 2, 3), "tp": tp, "fp": fp, "fn": fn, "tn": tn}


PARTS = {"word list": ("list",), "temperature": ("temp",), "model": ("model",), "word list + temperature": ("list", "temp"),
         "shipped": ("list", "temp", "model")}


def decide(flags: list[dict[str, Any]], parts: tuple[str, ...]) -> list[bool]:
    return [any(f[k] for k in parts) for f in flags]


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    rows = load()
    blind = blind_sample(rows)
    if argv[:1] == ["sample"]:
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "blind.jsonl").write_text("".join(json.dumps({"n": i + 1, "title": r["title"]}, ensure_ascii=False) + "\n"
                                                 for i, r in enumerate(blind)), encoding="utf-8")
        print(len(rows), "consultations;", len(blind), "titles to label")
        return 0
    labels = json.loads((OUT / "labels.json").read_text(encoding="utf-8"))
    y = [bool(labels[str(i + 1)]) for i in range(len(blind))]
    flags = run_app_check([r["title"] for r in blind])
    report: dict[str, Any] = {"consultations": len(rows)}
    for group in ("all", "target", "symptom"):
        idx = [i for i, r in enumerate(blind) if group == "all" or r["group"] == group]
        report[f"blind titles, {group}"] = {name: confusion([y[i] for i in idx], [decide(flags, parts)[i] for i in idx])
                                            for name, parts in PARTS.items()}
    for field in ("title", "question"):
        part = [r for r in rows if r["kind"] != "other" and r[field]]
        f = run_app_check([r[field] for r in part])
        report[f"category labels, {field}"] = {name: confusion([r["kind"] == "symptom" for r in part], decide(f, parts))
                                               for name, parts in PARTS.items()}
        everyone = [r for r in rows if target(r) and r[field]]
        f = run_app_check([r[field] for r in everyone])
        report[f"share flagged, bone/muscle/sports, {field}"] = {name: round(sum(decide(f, parts)) / len(everyone), 3)
                                                                 for name, parts in PARTS.items()} | {"n": len(everyone)}
    (OUT / "summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
