# ml/eval

Evaluation CLI lands in Task 4. Sealed test enforcement already lives in `qawam_ml.rehab24.load_repetitions(..., final=True)` (Task 1a). The CLI must pass `final` only with `--final` and must not add a back door.

`audit_splits.py` (Task 1a-3, pandas, not CI) reads `Segmentation.csv` + `ml/splits.json` only and writes `docs/split-audit.md`. It does not open video/npy and does not call `load_repetitions('test')`.
