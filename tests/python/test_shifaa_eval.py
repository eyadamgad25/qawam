"""Tests for ml/pain/shifaa_eval.py on a tiny made-up archive: categories, the odd/even split, and scoring."""

import csv
import importlib.util
import io
import sys
import zipfile
from pathlib import Path

PAIN_DIR = Path(__file__).resolve().parents[2] / "ml" / "pain"
sys.path.insert(0, str(PAIN_DIR))
spec = importlib.util.spec_from_file_location("shifaa_eval", PAIN_DIR / "shifaa_eval.py")
s = importlib.util.module_from_spec(spec)
sys.modules["shifaa_eval"] = s
spec.loader.exec_module(s)
COLUMNS = ["Question Title", "Question", "Answer", "Doctor Name", "Consultation Number", "Date of Answer", "Hierarchical Diagnosis"]


def archive(path, rows):
    with zipfile.ZipFile(path, "w") as z:
        for name in {r[0] for r in rows}:
            out = io.StringIO()
            w = csv.writer(out)
            w.writerow(COLUMNS)
            for file, number, diagnosis in rows:
                if file == name:
                    w.writerow([f"title {number}", "q", "a", "d", number, "2020", diagnosis])
            z.writestr(f"{name}.csv", out.getvalue())


def test_categories_come_from_the_end_of_the_diagnosis(tmp_path, monkeypatch):
    archive(tmp_path / "a.zip", [("Bone_Diseases", "1001", "العظام - المفاصل - التنميل"), ("Bone_Diseases", "1002", "العظام - آلام الرقبة"),
                                 ("Physical_Health", "1003", "الصحة البدنية - الرياضة وصحة البدن - ممارسة الرياضة"),
                                 ("Physical_Health", "1004", "الصحة الغذائية - المأكولات")])
    monkeypatch.setattr(s, "ARCHIVE", tmp_path / "a.zip")
    rows = {r["id"]: r for r in s.load()}
    assert [rows[i]["kind"] for i in (1001, 1002, 1003, 1004)] == ["symptom", "ordinary", "ordinary", "other"]
    assert [s.target(rows[i]) for i in (1001, 1002, 1003, 1004)] == [True, True, True, False]


def test_blind_sample_uses_odd_numbers_only_and_never_twice():
    rows = [{"id": i, "file": "Bone_Diseases", "diagnosis": "", "kind": "symptom" if i % 3 == 0 else "ordinary", "title": str(i)} for i in range(1, 1500)]
    picked = s.blind_sample(rows)
    assert len(picked) == 250 == len({r["id"] for r in picked})
    assert all(r["id"] % 2 for r in picked)


def test_scores():
    c = s.confusion([True, True, False, False], [True, False, True, False])
    assert (c["recall"], c["false_alarm_rate"], c["f1"], c["macro_f1"]) == (0.5, 0.5, 0.5, 0.5)
    assert s.decide([{"list": False, "temp": False, "model": True}], ("list", "temp")) == [False]


def test_a_folder_of_csvs_loads_like_the_zip(tmp_path):
    rows = [("Bone_Diseases", "1001", "العظام - المفاصل - التنميل"), ("Physical_Health", "1004", "الصحة الغذائية - المأكولات")]
    archive(tmp_path / "a.zip", rows)
    folder = tmp_path / "unzipped" / "inner"
    folder.mkdir(parents=True)
    with zipfile.ZipFile(tmp_path / "a.zip") as z:
        z.extractall(folder)
    assert s.load(tmp_path / "a.zip") == s.load(tmp_path / "unzipped")


def test_second_blind_sample_is_new_odd_and_split_as_written():
    rows = [{"id": i, "file": "Bone_Diseases" if i % 5 else "Internal", "diagnosis": "", "kind": "symptom" if i % 3 == 0 else "ordinary",
             "title": str(i)} for i in range(1, 6000)]
    first = {r["id"] for r in s.blind_sample(rows)}
    second = s.blind_sample2(rows)
    assert len(second) == 300 == len({r["id"] for r in second})
    assert all(r["id"] % 2 for r in second) and not first & {r["id"] for r in second}
    assert sum(r["group"] == "target" for r in second) == 180
