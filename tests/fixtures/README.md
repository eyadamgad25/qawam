# Fixtures

Tiny, shareable or synthetic clips and landmark JSON. Real dataset files stay out of git.

REHAB24-6 loader tests (Task 1a) build a **synthetic** `Segmentation.csv` in pytest `tmp_path`. They do not read `data/raw/`. Global `.gitignore` of `*.mp4` / `*.npy` means those binaries cannot be stored here anyway.
