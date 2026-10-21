# ml/

Python 3.11 target (CI). Local 3.14 is **UNVERIFIED** for MediaPipe/OpenCV.

Packages will appear as tasks land:

- `pose/` — MediaPipe offline
- `angles/` — in-plane joint angles (Task 2)
- `rules/` — may wrap JSON from `/rules`
- `eval/` — subject-wise splits + sealed test (Task 4)
- `nlp/` — pain-note lexicon baseline (later)

Install test tools: `python -m pip install -r ml/requirements-dev.txt`
