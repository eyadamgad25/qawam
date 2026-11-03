# Dataset register

Raw data never enters git (`data/raw/` is ignored). Cite each dataset in any write-up.

| Dataset | People | What it gives Qawam | Labels | Licence | Source | Status |
| --- | --- | --- | --- | --- | --- | --- |
| REHAB24-6 | 10 | RGB video (2 cameras), mocap 2D/3D skeletons, 6 exercises | correct / incorrect per rep | CC BY-NC 4.0 + research-only text | https://zenodo.org/records/13305826 | in use (train/val; test 7, 9 sealed) |
| REHAB26-ViewAngles | 5 | MediaPipe 2D/3D skeletons, 3 cameras x 11 orientations, squat / arm abduction / shoulder extension | correct / incorrect + error type | CC BY-NC 4.0 | https://zenodo.org/records/23018128 | in use (`ml/eval/rehab26_eval.py`) |
| IntelliRehabDS | 30 | Kinect v2 skeletons (25 joints), 9 gestures, standing and seated | correct / incorrect | CC BY 4.0 | https://zenodo.org/records/4610859 | downloaded (SkeletonData.zip); loader next |
| UCOPhyRehab++ | 27 | 3D joints with angles (OptiTrack), 5 viewpoints, silhouettes, optical flow; no raw RGB | quality score per rep, 1-5, from several PhD physiotherapists rating independently | CC BY 4.0 | https://zenodo.org/records/17935737 | in use (`ml/eval/ucophyrehab_eval.py`); release has one score per rep and only the moving limb's 3 joints |
| Fit3D | 13 | 4 synchronised RGB cameras + Vicon 3D skeletons and SMPL-X, 611 sequences, 37 fitness exercises incl. squat, at least 5 annotated reps each | repetitions; instructor as reference (no clinical labels) | non-commercial research only, single user, no training for commercial use | https://fit3d.imar.ro | account created; test-set ground truth held by the challenge |
| FineRehab | 50 (30 musculoskeletal patients) | 2 Kinect Azure (front + side), 17 IMUs, 16 exercises, 4,215 samples | quality labels (per paper) | not published | https://bsu3dvlab.github.io/FineRehab | "released soon": ask the authors |
| KIMORE | 78 incl. patients | Kinect skeletons, RGB-D, 5 exercises | clinical scores | see paper | https://doi.org/10.1109/TNSRE.2019.2923060 | pending: download by hand |
| UI-PRMD | 10 | Vicon / Kinect skeletons, 10 movements | correct / incorrect | public domain | https://webpages.uidaho.edu/ui-prmd/ | pending: host not reachable from the cloud workspace |
| UCO Physical Rehabilitation (videos) | 27 | RGB multi-view video | none for quality | on request | https://github.com/AVAuco/ucophyrehab | optional: email inforeha@uco.es |

Splits are always by person. For cross-dataset tests, a model or threshold is fitted on one dataset and evaluated, untouched, on another.
