# REHAB24-6 dataset report (Task 1a)

Status: local files inspected 2026-10-21. No MediaPipe run in this pass. Do not commit `data/raw/`.

## Source and license

- Record: [Zenodo 13305826](https://zenodo.org/records/13305826), DOI [10.5281/zenodo.13305826](https://doi.org/10.5281/zenodo.13305826), version v1, published 28 Aug 2024.
- Creators listed on that page: Černek, Sedmidubsky, Budikova, Jánošová, Katzer, Procházka (Masaryk University / VisionCraft / 4D Fyzioterapie).
- Citation on the page: Černek, A., Sedmidubsky, J., Budikova P.: *REHAB24-6: Physical Therapy Dataset for Analyzing Pose Estimation Methods*. SISAP 2024.
- **License (quoted from the Zenodo page, including their spelling):** “This dataset is for academic or non-profit organization noncomercial research use only. By using you agree to appropriately reference the paper above in any publication making of its use. For comercial purposes contact us at info@visioncraft.ai”
- This is **not** a Creative Commons SPDX id. Redistribution of videos into git is forbidden by our `.gitignore` and is a bad idea under those terms. How those terms interact with a student GitHub repo that only stores code is **UNVERIFIED** — ask the supervisor; do not upload `data/raw/`.

Owner report: `videos.zip` and `2d_joints.zip` were extracted into `Ex1`…`Ex6` (merged). All 5 MD5 hashes match the Zenodo record. This pass did **not** re-hash the zips. Zenodo lists (among others):

| File | Zenodo md5 (from the record page) |
| --- | --- |
| `2d_joints.zip` | `dbfbc09d3f087482abc3f6c23bcf48bd` |
| `videos.zip` | `ed183a245a1b171638e422f7a288e5a8` |
| `Segmentation.csv` | `90b8fbd7445dd050bf27b17126c78fbe` |
| `Segmentation.txt` | `5f2a5b886c6f794f03e1a8f642738c86` |
| `joints_names.txt` | `3f04a37cce43086b1ea1fa49f1e4514f` |

Zenodo’s table says `joint_names.txt`; the local filename is `joints_names.txt`.

## Local layout (`data/raw/rehab24-6/`)

Observed 2026-10-21:

- `Ex1` … `Ex6/` (extracted recordings)
- `2d_joints.zip`, `videos.zip` (archives still present)
- `Segmentation.csv`, `Segmentation.txt`, `joints_names.txt`

Zenodo also lists `2d_markers.zip`, `3d_joints.zip`, `3d_markers.zip`, `marker_names.txt`. Those files are **not** in this local folder.

Per recording, inside `ExN/` (confirmed on `Ex1/PM_000*`):

- `PM_000-Camera17-30fps.mp4`
- `PM_000-Camera18-30fps-transposed.mp4`
- `PM_000-c17-30fps.npy`
- `PM_000-c17-120fps.npy`
- `PM_000-c18-30fps.npy`
- `PM_000-c18-120fps.npy`

Zenodo text: Camera17 = horizontal RGB, Camera18 = vertical RGB; both 30 FPS. CSV frame indexes are **30 FPS only** (`Segmentation.txt` + Zenodo).

## Segmentation.csv

- Delimiter: **semicolon** (not comma).
- Line count: **1073** including header → **1072** repetition rows (matches `len(pandas.read_csv)`).
- Header (exactly):

`video_id;repetition_number;exercise_id;person_id;first_frame;last_frame;cam17_orientation;mocap_erroneous;exercise_subtype;lights_on;extra_person_in_cam17;extra_person_in_cam18;correctness`

- First data row: `PM_000;1;1;1;180;377;front;0;right arm;0;3;0;1`
- **`video_id` is the recording id, not the subject.** `person_id` is the subject.
- Unique `person_id`: 1–10 (10 subjects). Unique `video_id`: 65. Unique `exercise_id`: 1–6.
- `cam17_orientation` values present: `front`, `half-profile`, `profile` (no string `side` in the CSV).
- Counts measured from the CSV: `lights_on` 1=764, 0=308; `mocap_erroneous` 0=1057, 1=15; `correctness` 1=568, 0=504; `extra_person_in_cam17` 0=686, 1=117, 2=206, 3=63.
- Reps per `exercise_id`: 1=178, 2=208, 3=107, 4=210, 5=174, 6=195.
- Subject coverage is **not** a full 10×6 grid: `person_id` 10 appears only in `exercise_id` 3; `person_id` 1 has no rows in `exercise_id` 5.
- `exercise_subtype` empty on 510 rows; non-empty values seen: `right arm` (178), `left leg` (106), `right leg` (104), `front leg right` (91), `front leg left` (83).
- Clean-subset rule used by the loader (as specified for this task): `mocap_erroneous=0` AND `extra_person_in_cam17=0` AND `lights_on=1` → **521** rows in the full CSV. `extra_person_in_cam18` is **not** part of that filter.

Whether `first_frame`/`last_frame` are inclusive is **UNVERIFIED** (file does not say). Loader returns the integers as stored.

## Segmentation.txt inconsistencies (**UNVERIFIED** which side is a typo)

1. Possible `cam17_orientation` values are listed as `front` / `half-profile` / `profile`, but the conversion table’s third row is `side -> front`. The CSV never contains `side`.
2. `extra_person_in_cam18` is described as extra persons “in the **camera17** recording”.

Do not silently rewrite `profile` to `side` in code until a physio/dataset author confirms.

## Exercises (names from the Zenodo page, not from local CSV)

Local CSV only stores `exercise_id` 1–6 and folders `Ex1`–`Ex6`. Names below are copied from [the Zenodo record](https://zenodo.org/records/13305826):

| id | Folder | Zenodo name |
| --- | --- | --- |
| 1 | Ex1 | Arm abduction |
| 2 | Ex2 | Arm VW |
| 3 | Ex3 | Push-ups (hands on a table) |
| 4 | Ex4 | Leg abduction |
| 5 | Ex5 | Leg lunge |
| 6 | Ex6 | Squats |

## 26 joints (`joints_names.txt`)

```
0 Hips, 1 Spine, 2 Spine1, 3 Neck, 4 Head, 5 Head_end,
6 LeftShoulder, 7 LeftArm, 8 LeftForeArm, 9 LeftHand, 10 LeftHand_end,
11 RightShoulder, 12 RightArm, 13 RightForeArm, 14 RightHand, 15 RightHand_end,
16 LeftUpLeg, 17 LeftLeg, 18 LeftFoot, 19 LeftToeBase, 20 LeftToeBase_end,
21 RightUpLeg, 22 RightLeg, 23 RightFoot, 24 RightToeBase, 25 RightToeBase_end
```

OptiTrack-style names: in this skeleton `LeftArm` is the upper arm segment name, not “hand”. **Mapping to MediaPipe landmarks is UNVERIFIED.** Working hypothesis for Task 1b overlay (do not use as fact until overlay):

| REHAB24-6 | hypothesized MediaPipe |
| --- | --- |
| LeftArm | shoulder |
| LeftForeArm | elbow |
| LeftHand | wrist |
| LeftUpLeg | hip |
| LeftLeg | knee |
| LeftFoot | ankle |

(and the Right* mirrors). `LeftShoulder` vs `LeftArm` collision with MediaPipe “shoulder” is exactly why this must be checked visually.

## Measured files (Ex1 / PM_000)

Camera17 30 FPS video (`cv2.VideoCapture`): `isOpened=True`, **1304** frames, **30.0** FPS, **1920×1080**.

`PM_000-c17-30fps.npy`: shape `(1304, 26, 2)`, dtype `float64`. First-frame joints 0–2 (owner measurement): `(751.97, 555.65)`, `(751.10, 517.70)`, `(745.33, 426.56)`. **Frame count matches the video 1:1 for Camera17 30 FPS.**

This pass also opened Camera18 (not in the owner bullet list, measured here):

- `PM_000-Camera18-30fps-transposed.mp4`: opened, **1304** frames, **30.0** FPS, **1080×1920** (portrait).
- `PM_000-c18-30fps.npy`: `(1304, 26, 2)` float64 — **same frame count** as that video.
- Value ranges on this recording: c17 xy ≈ x∈[332.8, 1147.0], y∈[−14.69, 1019.9]; c18 xy ≈ x∈[202.5, 474.4], y∈[317.4, 1690.7].
- 120 FPS npy: both cameras `(5215, 26, 2)`. 5215 / 1304 ≈ 3.999 (not an integer 4). How to index 120 FPS arrays from CSV 30 FPS frames is **UNVERIFIED**.

## UNVERIFIED (verify in Task 1b overlay, do not code as truth)

1. **Pixel convention / origin.** Zenodo text says the 2D GT is “pixel coordinates” from a pinhole projection. Local files do not state origin (top-left vs bottom-left) or that +y is down. Negative y on c17 joint min (−14.69) is compatible with “slightly out of frame” if origin is top-left on a 1080-tall image, but that is **not** proof. Treat “pixels, origin top-left” as **UNVERIFIED** until overlay.
2. **Camera18 joints vs the “transposed” video.** Frame counts match (1304) and the y-range on this clip fits a 1920-tall frame better than 1080. That still does **not** prove the npy is in the same orientation as `*-Camera18-30fps-transposed.mp4`. Overlay in 1b.
3. **26 joints → MediaPipe** (hypothesis table above). Overlay in 1b.
4. **`profile` vs `side`** in `Segmentation.txt` (above).
5. **`extra_person_in_cam18` prose** pointing at camera17 (above).

## Split (frozen)

`ml/splits.json`: shuffle `person_id` 1–10 with `random.Random(20261021)` on Python 3.14.0, then 6/2/2.

- train: 8, 5, 6, 2, 3, 10
- validation: 4, 1
- test: 7, 9 (sealed)

Because person 10 is only in Ex3, the train split is thinner on other exercises. Do not “fix” this by moving subjects.

## Software pins (this machine’s `.venv`)

Python **3.14.0**. `mediapipe==1.1.1`, `numpy==2.5.4`, `opencv-python==5.0.0.93`, `pandas==3.0.6`, `matplotlib==3.11.2`. MediaPipe 1.1.1 is newer than most tutorials — Task 1b must read **that** version’s docs and must not assume `mp.solutions.pose` exists.
