# REHAB24-6 dataset report (Task 1a)

Status: local files inspected 2026-10-21. No MediaPipe run in this pass. Do not commit `data/raw/`.

## Source and license

- Record: [Zenodo 13305826](https://zenodo.org/records/13305826), DOI [10.5281/zenodo.13305826](https://doi.org/10.5281/zenodo.13305826), version v1, published 28 Aug 2024.
- Creators listed on that page: Černek, Sedmidubsky, Budikova, Jánošová, Katzer, Procházka (Masaryk University / VisionCraft / 4D Fyzioterapie).
- Citation on the page: Černek, A., Sedmidubsky, J., Budikova P.: *REHAB24-6: Physical Therapy Dataset for Analyzing Pose Estimation Methods*. SISAP 2024.
- **Rights field (Zenodo metadata `license.id`, checked 2026-10-23):** `cc-by-nc-4.0` (CC BY-NC 4.0).
- **Description / License text (quoted from the Zenodo page, including their spelling):** “This dataset is for academic or non-profit organization noncomercial research use only. By using you agree to appropriately reference the paper above in any publication making of its use. For comercial purposes contact us at info@visioncraft.ai”
- **What we follow:** both statements apply. We follow the **stricter** combination: academic or non-profit **noncommercial research use only**, plus the required SISAP 2024 citation. CC BY-NC 4.0 alone would still allow some non-research non-commercial uses; the description text does not. Redistribution of videos into git is forbidden by our `.gitignore` and is a bad idea under those terms. How those terms interact with a student GitHub repo that only stores code is **UNVERIFIED** — ask the supervisor; do not upload `data/raw/`.

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
- Filters live in `ml/qawam_ml/filters.py` (Task 1a-3). `gt_quality(row, cam)`: `mocap_erroneous=0` AND `lights_on=1` AND `extra_person_in_cam{cam}=0`. `label_quality` drops the mocap check. The old single clean-subset (`mocap_erroneous=0` AND `extra_person_in_cam17=0` AND `lights_on=1`) is `gt_quality(..., 17)` → **521** rows in the full CSV.

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

## Alignment checks (Camera18 PM_039 train sample)

On 2026-10-23, the authorized Camera18 train pair
`Ex1/PM_039-Camera18-30fps-transposed.mp4` and
`Ex1/PM_039-c18-30fps.npy` was checked at zero-based frames 94, 95, and 96.
The video is 1080×1920 at 30 FPS with 3803 frames; the joint array is
`(3803, 26, 2)`. The 26 labeled coordinates overlaid on the same-index video
frames follow the visible person's head, trunk, arms, legs, and feet. Neighbor
frames show consistent placement. For this recording, the coordinates fit
the displayed portrait frame without swapping x/y, supporting the
Camera18-transposed-video / same-index alignment hypothesis.

This is a visual check of one training recording and three adjacent sampled
frames, not a dataset-wide validation. The overlay's connecting lines follow
the named joint hierarchy for readability; they do not establish a clinical
or MediaPipe landmark mapping.

MediaPipe Pose Landmarker Lite v1.1.1 was then run on those same three
frames. In the annotated outputs, ground-truth joints/links are red/green
with numeric joint indices; MediaPipe landmarks/links are cyan with `M`
indices. Both skeletons are visually on the subject, but profile-view
self-occlusion and close bilateral points make some correspondences
ambiguous.

Three explicit candidate assignments were compared using Euclidean
ground-truth-to-MediaPipe point distance divided by the image diagonal,
aggregated over 12 corresponding point pairs × 3 adjacent frames in each of
two orientations of the same recording:

| Camera18 view in train export | Existing hypothesis | Adjacent arm-joint shift | Existing hypothesis with left/right indices swapped |
| --- | ---: | ---: | ---: |
| Profile (frames 94–96) | 2.40% | 3.36% | 2.61% |
| Half-profile (frames 2539–2541) | 1.41% | 3.98% | 8.31% |
| Combined six-frame sample | 1.90% | 3.67% | 5.46% |

The existing documented hypothesis maps `LeftArm`→left shoulder,
`LeftForeArm`→left elbow, `LeftHand`→left wrist (mirrored right), and
upper leg/leg/foot→hip/knee/ankle. The adjacent-arm candidate instead maps
the shoulder marker→shoulder, `Arm`→elbow, and `ForeArm`→wrist, with the
same lower-limb mapping.

The existing hypothesis has the lowest mean in both sampled views, but all
six frames are from one recording and a single half-profile repetition. The
limited score is not a validated mapping or enough evidence to change
production code. A second train recording was subsequently checked; see the
PM_101 section below. Keep the 26-joint to MediaPipe correspondence
**UNVERIFIED** pending authoritative joint-definition evidence and broader
review. No coaching, threshold, or app behavior was changed.

### Second train recording: PM_101 Camera18

On 2026-10-24, the specifically authorized PM_101 Camera18 half-profile
train pair was checked at zero-based frames 34–36. Its video has 1,307 frames
while its 30 FPS joint array has 1,308 rows, so equal total lengths are not
established. The selected same-index frames are within both files, and their
overlay is visually plausible, but the one-row difference keeps full-clip
synchronization **UNVERIFIED**.

For the same 12 candidate point pairs, mean normalized image-diagonal
distance on PM_101 frames 34–36 was 1.58% for the documented hypothesis,
4.21% for the adjacent arm-joint shift, and 10.49% for the
left/right-swapped hypothesis. Combined with the six PM_039 frames, across
both clips/views (108 point/frame comparisons), means were 1.80%, 3.85%, and
7.14%, respectively. This is cross-recording support for the existing
candidate over these tested alternatives, not definitive anatomical
ground-truth validation: the sample remains two people, two recordings, and
three frames per PM_101 clip section. The PM_101 image shows generally
plausible alignment, but medial/lateral limb distinctions and exact
landmark semantics still require an authoritative skeleton definition and
broader checks. Do not treat this as a fixed mapping or clinical result.

Overlay script: `py -3.14 ml/eval/overlay_camera18_train.py`. It reads only
the explicitly approved PM_039 and PM_101 files and the ignored Lite task
model, and writes nine PNG comparison overlays under the gitignored
`data/derived/overlay/`.
Official task model source:
https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task

## Remaining UNVERIFIED items

1. **Global pixel convention / origin.** On the checked PM_039 Camera18 sample, same-index coordinates fit the displayed 1080×1920 frame without swapping axes. Dataset-wide origin and axis convention remain **UNVERIFIED**.
2. **General frame synchronization.** PM_039 has matching 3803-frame counts and visually plausible same-index overlays. PM_101 has 1307 video frames vs 1308 joint rows; only the authorized same-index frames 34–36 were compared. Dataset-wide and PM_101 end-of-sequence alignment remain **UNVERIFIED**.
3. **26 joints → MediaPipe.** Candidate comparison across PM_039 and PM_101 favors the existing documented hypothesis over two tested alternatives, but the small sample does not establish a canonical correspondence. MediaPipe mapping remains **UNVERIFIED** pending authoritative joint definitions and broader checks.
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
