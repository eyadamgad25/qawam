# ml/

Python **3.14** (CI + local `.venv`). Runtime pins: `requirements.txt`. pytest/jupyter: `requirements-dev.txt`.

- `qawam_ml/rehab24.py` — REHAB24-6 CSV loader, named filters, sealed test split
- `qawam_ml/filters.py` — `none` / `gt_quality` / `label_quality`, Camera18 view swap
- `qawam_ml/angles.py` — generic 2D angle geometry; no joint mapping or clinical thresholds
- `qawam_ml/smoothing.py` — causal trailing moving average; caller chooses the window
- `qawam_ml/repetitions.py` — configurable low/high hysteresis counter; no threshold defaults
- `qawam_ml/capture_quality.py` — required-landmark visibility gate; caller supplies landmarks and cutoff
- `qawam_ml/angle_pipeline.py` — composes the configurable gate, angle, smoothing, and rep counter
- `splits.json` — frozen subject-wise 6/2/2 on `person_id`
- `pose/` — MediaPipe offline (Task 1b+)
- `eval/` — evaluation CLI (Task 4; sealing already starts in the loader)

```powershell
.\.venv\Scripts\python.exe -m pip install -r ml/requirements.txt -r ml/requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```
