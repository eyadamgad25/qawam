# ml/

Python **3.14** (CI + local `.venv`). Runtime pins: `requirements.txt`. pytest/jupyter: `requirements-dev.txt`.

- `qawam_ml/rehab24.py` — REHAB24-6 CSV loader, clean subset, sealed test split
- `splits.json` — frozen subject-wise 6/2/2 on `person_id`
- `pose/` — MediaPipe offline (Task 1b+)
- `eval/` — evaluation CLI (Task 4; sealing already starts in the loader)

```powershell
.\.venv\Scripts\python.exe -m pip install -r ml/requirements.txt -r ml/requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest
```
