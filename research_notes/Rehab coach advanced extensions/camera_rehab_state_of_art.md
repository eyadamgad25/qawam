# Camera-based assessment for home MSK rehabilitation: state of the art 2024-2026

Scope: what goes beyond 2D BlazePose + angle thresholds + DTW-to-3-reps, with measured accuracy and phone/browser feasibility. Researched 2026-11-26 with 17 search/fetch calls. Several 2026 items are preprints and are marked as such.

## 1. Pose models that beat or complement MediaPipe BlazePose (accuracy vs mocap, mobile speed, licence)

### Takeaway
No single-phone model is yet interchangeable with marker-based mocap for clinical joint angles. Sagittal lower-limb error clusters around 5-6 deg, and frontal/transverse planes and the upper limb are worse. The biggest measured accuracy jump comes from OpenCap-style pipelines that add a biomechanical model and physics refinement on top of a pose model (OpenCap Monocular reports 4.8 deg MAE from a single phone), not from swapping the 2D keypoint detector. For an in-browser PWA, RTMPose-s via ONNX Runtime Web is the realistic "stronger detector" option. Heavy 3D/SMPL pipelines are server-side and mostly research-licensed.

### Cited Findings
- **Scoping review (arXiv 2609.18667, 2026 preprint):** 117 studies, mostly published from 2024 on, mostly healthy adults walking in labs. Sagittal lower-limb agreement with marker-based systems clusters around 5-6 deg, described as "generally short of clinical acceptability". Most studies report raw joint angles without biomechanical refinement. Out-of-plane kinematics, kinetics and older or pathological populations are rarely validated. Foundation-model mesh recovery and differentiable IK are almost absent from validated studies. — [arXiv 2609.18667](https://arxiv.org/abs/2609.18667)
- **MediaPipe vs marker-based mocap:**
  - Hand/finger joint-angle RMSE was 10.9 ± 7.8 deg for MediaPipe vs 14.7 ± 8.6 deg for Leap Motion (Sensors 2025). — [Sensors 25(4):1079](https://doi.org/10.3390/s25041079)
  - A VR-rehab validation found valid hip/knee estimates but overestimation, with a mean bias of −17.49 deg at the right hip. — [ResearchGate](https://www.researchgate.net/publication/383968901_Validation_of_a_MediaPipe_System_for_Markerless_Motion_Analysis_During_Virtual_Reality_Rehabilitation)
  - A Politecnico di Milano thesis (2024) reports RMSE under 9 deg for the lower limbs and 15 deg for the upper limbs. — [Polimi thesis](https://www.politesi.polimi.it/retrieve/285978a4-81d8-4962-99ce-4c93114044c8/2024_04_Francia_Tesi_01.pdf)
  - Three-camera MediaPipe vs Vicon during squats and lunges: mean angle error 6.4 deg, segment orientation error 9.6 deg. — [Sensors 26(21):6773](https://www.mdpi.com/1424-8220/26/21/6773)
- **YOLOv7-pose vs MediaPipe (shoulder/elbow rehab):** MAE about 5 deg vs about 17 deg for MediaPipe. YOLOv7 is 2D-only, needs more compute and struggles with multi-DoF movements. This is a single study on an old YOLO version. — [Springer chapter](https://link.springer.com/chapter/10.1007/978-3-031-53036-4_1)
- **OpenCap (2+ phones, Stanford, PLOS Comp Bio 2023, older):** lower-extremity RMSE 2.0-10.2 deg across degrees of freedom, comparable to IMUs (about 2-12 deg) and 8-camera video (about 2.6-11 deg). — [PLOS Comp Bio](https://journals.plos.org/ploscompbiol/article?id=10.1371%2Fjournal.pcbi.1011462)
- **OpenCap return-to-sport validation (J Biomech 2024):** 437 trials, grand mean MAE 3.85 deg and RMSE 4.34 deg. Frontal-plane CMC was 0.47-0.78 and transverse 0.51-0.6, weaker than sagittal. A knee OA cohort had a grand mean RMSE of 6.1 deg, with higher error in patients than in controls. — [J Biomech 2024](https://www.sciencedirect.com/science/article/abs/pii/S0021929024002781)
- **OpenCap functional tasks (Applied Sciences 2026):** knee flexion RMSE 1.4-10.5 deg (r = 0.94-0.999). Ankle RMSE ranged from 1.4 deg (sit-to-stand) to 9.3 deg. — [Appl Sci 16(18):9211](https://www.mdpi.com/2076-3417/16/18/9211)
- **OpenCap Monocular (single smartphone, arXiv 2603.24733, March 2026, preprint):** It refines WHAM monocular 3D estimates with physics-inspired optimisation onto a musculoskeletal model.
  - Rotational MAE 4.8 deg and translational MAE 3.4 cm, vs 9.3 deg / 11.0 cm for a direct computer-vision baseline (48% and 69% lower).
  - Walking ground reaction forces at 9.7% bodyweight MAE.
  - Validated on walking, squat and sit-to-stand in 10 healthy adults (public OpenCap dataset).
  - Sources: [arXiv 2603.24733](https://arxiv.org/abs/2603.24733); [Utah MoBL announcement](https://mobl.mech.utah.edu/opencap-monocular-released/); [CVBW 2026 paper page](https://cvbw2026.github.io/_pages/15.html)
- **Other single-camera methods on the same OpenCap dataset:** about 6 deg error, higher in frontal/transverse planes. — [arXiv 2507.08268 (Portable Biomechanics Lab)](https://arxiv.org/html/2507.08268v2)
- **RTMPose (open-mmlab, 2023, older):** RTMPose-s reaches 72.2% AP on COCO at 70+ FPS on a Snapdragon 865 (ncnn, native, not browser). RTMO-l reaches 74.8% AP on COCO at 141 FPS on a V100 GPU. No mobile figure was found for RTMO. — [arXiv 2303.07399](https://arxiv.org/abs/2303.07399)
- **RTMPose in the browser:** a Harvard tool page runs RTMPose-s with an RTMDet-nano detector in ONNX Runtime Web. First load is about 22 MB (pose) + about 3 MB (detector), and no FPS benchmark is published. — [Harvard MMLA RTMPose tool](https://mmla.gse.harvard.edu/tools/rtmpose/)
- **Practitioner guidance (secondary, unverified):** MediaPipe remains the default where frames must stay on-device with a ready browser SDK. RTMPose is preferred for multi-stream server or edge processing. MediaPipe is said to be "a few points" below RTMPose on hard sets, with no source given. — [fullstackcv playbook](https://fullstackcv.github.io/playbook/pose/); [Forasoft comparison](https://www.forasoft.com/learn/ai-for-video-engineering/articles-ai/openpose-mediapipe-rtmpose-pose-tracking)
- **Depth limitation of BlazePose:** the z-axis is inferred from monocular priors, so out-of-plane movement and poor camera angles add angle error. — [PMC13454122 hybrid single-camera rehab model](https://pmc.ncbi.nlm.nih.gov/articles/PMC13454122/)
- **Licences (repos named here, not re-fetched this session):**
  - [google-ai-edge/mediapipe](https://github.com/google-ai-edge/mediapipe): Apache-2.0
  - [open-mmlab/mmpose (RTMPose/RTMO/ViTPose impl.)](https://github.com/open-mmlab/mmpose): Apache-2.0
  - [ViTPose](https://github.com/ViTAE-Transformer/ViTPose): Apache-2.0
  - [MotionBERT](https://github.com/Walter0807/MotionBERT): Apache-2.0
  - [Ultralytics YOLO11-pose](https://github.com/ultralytics/ultralytics): AGPL-3.0, or a paid enterprise licence for closed or commercial use
  - [SMPL](https://smpl.is.tue.mpg.de/) and WHAM-style SMPL pipelines: research/non-commercial unless a commercial licence is bought
  - [stanfordnmbl/opencap-core](https://github.com/stanfordnmbl/opencap-core): Apache-2.0 code, with non-commercial terms on the hosted service

### Inferences
- For this PWA, swapping BlazePose for RTMPose-s (ONNX Runtime Web, WebGPU/WASM) is feasible but costs about 25 MB extra download. That fits offline caching, but it is a 2D-only gain, and BlazePose's 3D world landmarks would be lost. Treat it as an A/B experiment on KERAAL and REHAB24-6 angle error, not an assumed win.
- The clinically meaningful upgrade path is "pose model + kinematic model + constraints", for example fitting a bone-length-constrained skeleton and computing angles in anatomical planes, as OpenCap does. The scoping review notes most studies skip this step.
- OpenCap Monocular could serve as an offline, physio-side "lab check" (upload a clip, get 3D kinematics) rather than an on-phone runtime. SMPL licensing makes commercial reuse of WHAM-based pipelines a problem.
- Because frontal/transverse errors are large across all monocular methods, the app should restrict quantitative ROM claims to sagittal-plane joints filmed side-on and label others "qualitative".

### Gaps
- No head-to-head benchmark of MediaPipe vs RTMPose vs ViTPose vs YOLO11-pose vs MotionBERT on rehab joint-angle RMSE was found.
- No measured in-browser FPS on mid-range Android was found for RTMPose or YOLO-pose.
- MoveNet was not specifically validated against mocap in the sources found.
- Licences above come from repo knowledge and were not re-fetched this session. Verify before citing in the thesis.

## 2. Exercise quality / movement-error assessment models and reported accuracy

### Takeaway
On KIMORE and UI-PRMD, the field has moved from GCNs to lightweight CNN and transformer hybrids and contrastive training. The largest unified benchmark (DeepRehabPile, 60 dataset-tasks) finds a small depthwise-separable CNN (LITEMV) best on average and GCNs near chance for binary correctness. Absolute binary-correctness accuracy is modest (about 77% average). A 2026 preprint on REHAB24-6 finds that MediaPipe angle templates reach only 0.58 balanced accuracy and 16-camera mocap only 0.60, so label and protocol design dominate over pose quality.

### Cited Findings
- **DeepRehabPile benchmark (arXiv 2507.21018, 2025):** 60 dataset-tasks (21 regression, 39 classification) across EHE, KIMORE, UI-PRMD, IRDS (IntelliRehabDS), KERAAL, KINECAL, SPHERE and UCDHE.
  - Models compared: FCN, H-Inception, LITEMV, DisjointCNN, ConvLSTM, MotionGRU, VanTran, ConvTran and STGCN.
  - Regression: LITEMV is best on average (MAE 5.35, RMSE 6.43), with ConvTran second and STGCN sixth.
  - Classification: LITEMV leads at 77.37% average accuracy, but its balanced accuracy is about 7 points lower. VanTran is statistically tied.
  - STGCN is competitive on KIMORE/UI-PRMD regression but near chance on classification.
  - LITEMV has the lowest FLOPs. VanTran is the most expensive, scaling quadratically with sequence length.
  - Code: [DeepRehabPile](https://github.com/MSD-IRIMAS/DeepRehabPile). Source: [arXiv 2507.21018](https://arxiv.org/html/2507.21018v1)
- **Frame topology fusion hierarchical GCN (Sci Rep, July 2025):** reports top results vs other methods on UI-PRMD and KIMORE. Exact numbers were not retrieved (paywall redirect). — [Sci Rep](https://www.nature.com/articles/s41598-025-12020-8)
- **PhysioFormer (2025):** a spatio-temporal transformer with skeletal-temporal self-attention over joint groups, evaluated on KIMORE, UI-PRMD and KERAAL. — [Springer](https://link.springer.com/chapter/10.1007/978-981-96-3525-2_14)
- **Sequential GCN with action classification (Comput Biol Med, 2025):** classifies the action first so that only valid sequences are scored. It claims SOTA quality-score prediction and efficiency. — [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S0010482524016639); [HAL](https://imt-atlantique.hal.science/hal-04117417)
- **Efficient Graph 3D Convolution (SSRN):** subject-wise 5-fold CV. On KIMORE it improves MAE, RMSE and R² by 5.05%, 7.70% and 21.75% over the best baseline, with smaller gains on UI-PRMD. — [SSRN 7305411](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7305411)
- **Supervised contrastive learning with hard/soft negatives (Med Biol Eng Comput, 2024):** targets few samples per exercise and reports gains on UI-PRMD, IRDS and KIMORE. — [Springer](https://link.springer.com/article/10.1007/s11517-024-03177-x); [arXiv 2403.02772](https://arxiv.org/pdf/2403.02772)
- **LLM-based quality assessment and feedback with prompt engineering (arXiv 2505.18412, 2025).** — [arXiv](https://arxiv.org/pdf/2505.18412)
- **REHAB24-6 dataset (Zenodo, Aug 2024):** 1,072 repetitions with binary correctness labels. Academic/non-profit non-commercial use only. — [Zenodo](https://zenodo.org/records/13305826)
  - A pose-estimation fine-tuning study (Černek et al., 2025) found fine-tuning improves quality, with depth estimation as the key limitation. — [MUNI](https://is.muni.cz/publication/2505537/en/Pose-Estimation-Analysis-and-Fine-Tuning-on-the-REHAB24-6-Rehabilitation-Dataset/Cernek-Sedmidubsky-Budikova)
  - An audit paper filters to 1,057 repetitions (558 correct / 499 incorrect) and warns about research-selection bias. — [arXiv 2610.01188](https://arxiv.org/pdf/2610.01188)
- **Arogya (Research Square 2026 preprint, not peer-reviewed):** interpretable joint-angle templates on REHAB24-6. MediaPipe reaches a mean balanced accuracy of 0.58, and a 16-camera optical system raises it only to 0.60. Only the title page could be fetched, so the numbers come from search-snippet text. — [Research Square rs-11822923](https://www.researchsquare.com/article/rs-11822923/v1)
- **Real-time action scoring system for physical therapy with pose estimation (Sci Rep 2025).** — [Sci Rep s41598-025-29062-7](https://www.nature.com/articles/s41598-025-29062-7)
- **Single-camera joint-angle system for chair-based frailty exercise quality (2025).** — [PMC12251734](https://pmc.ncbi.nlm.nih.gov/articles/PMC12251734/)

### Inferences
- The project's per-patient 3-rep DTW reference is in line with the "interpretable template" direction, and the Arogya preprint suggests pose quality is not the bottleneck. Gains are more likely from:
  - per-error-type labels (which joint, which phase) rather than binary correct/incorrect
  - reporting balanced accuracy, not accuracy
  - subject-wise splits
- A cheap technical upgrade that fits a browser is a small depthwise-separable 1D-CNN (LITEMV-like) or a tiny transformer on angle sequences, trained on KIMORE/UI-PRMD/KERAAL and run after DTW alignment. A GCN is a poor choice for binary correctness, per DeepRehabPile.
- Contrastive or few-shot training fits the "few reps per patient" reality and could turn the 3-rep reference into a learned embedding distance instead of raw DTW.
- An LLM could turn per-joint deviations into Arabic feedback text. That is a natural fit for an Arabic-first coach, but it needs grounding to avoid made-up advice.

### Gaps
- Exact KIMORE/UI-PRMD MAE tables for the 2025 Sci Rep HGCN and PhysioFormer were not retrieved.
- No REHAB24-6 correctness SOTA table from a peer-reviewed paper was found.
- No published KneE-PAD or PhysioLens benchmark comparisons were found in this pass.

## 3. Clinically meaningful measures from video (ROM, gait speed, STS, TUG, balance)

### Takeaway
Functional tests are where camera-only measurement is most validated. Repetition counts and durations are robust even when joint angles are not. The strongest 2026 evidence is a single-device app (Ameya MMC, iPad Pro with LiDAR) in 228 adults with chronic disease:
- 5xSTS ICC 0.995
- TUG ICC 0.962
- 30s-STS ICC 0.928
- gait speed ICC 0.868

Timing and counting tests are therefore the most defensible "clinical" features for this PWA.

### Cited Findings
- **Ameya MMC (PLOS Digital Health 2026):** single iPad Pro on a tripod at 2.5 m, LiDAR-assisted, 34 landmarks at about 30 Hz. 228 adults, age 61.6 ± 11.9, with chronic disease (37% cancer, 25% cirrhosis). The reference was a certified exercise physiologist.
  - ICC(2,1): TUG 0.962 (0.927-0.977); 30s-STS 0.928 (0.895-0.949); 5xSTS 0.995 (0.983-0.998); gait speed 0.868 (0.796-0.910); tandem stand 0.812 (0.979 after excluding chair-support cases).
  - SPPB total weighted kappa 0.808. Data loss 3.1%.
  - Limitations: supervised in-clinic use only; needs a LiDAR device; gait speed relied on depth (degrades beyond about 5 m); tracking was worse with dark or loose clothing; about 80% White sample; no Bland-Altman analysis.
  - Sources: [PMC12773808](https://pmc.ncbi.nlm.nih.gov/articles/PMC12773808/); [ResearchGate](https://www.researchgate.net/publication/399514514_Validation_of_a_markerless_motion_capture_app_for_automated_scoring_of_sit-to-stand_timed_up_and_go_and_short_physical_performance_battery_tests_in_adults_with_chronic_disease)
- **Computer-vision TUG subtask segmentation (2025):** used AlphaPose + MotionBERT on GoPro video against manual coding. — [PMC12762308](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12762308/)
- **Smartphone TUG (inertial, not camera):** an Electronics 2025 study reports ICC 0.93 for manual TUG and 0.94 for instrumented TUG. — [Electronics 14(23):4650](https://doi.org/10.3390/electronics14234650)
- **Smartphone iTUG reliability in young adults (Sensors 2024):** excellent reliability for total duration, weaker for the sit-to-stand sub-phase. — [Sensors 24(9):2918](https://www.mdpi.com/1424-8220/24/9/2918)
- **MoveLab (sensor-based, Sensors 2025):** TUG ICC 0.757 vs optical mocap in 25 healthy adults. — [PMC12473320](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12473320/)
- **OpenCap sit-to-stand:** ankle RMSE 1.4 deg during STS. — [Appl Sci 16(18):9211](https://www.mdpi.com/2076-3417/16/18/9211)
- **OpenCap Monocular:** validated on sit-to-stand and squat from one phone (preprint). — [arXiv 2603.24733](https://arxiv.org/abs/2603.24733)
- **Video-based biomechanics (OpenCap) found disease-specific movement signatures in neuromuscular disease (bioRxiv 2024).** — [bioRxiv 2024.09.26.613967](https://www.biorxiv.org/content/10.1101/2024.09.26.613967v2.full)

### Inferences
- Adding a guided "test mode" (30s-STS count, 5xSTS time, TUG time, gait speed over a marked 4 m) is a high clinical-value, low-model-risk extension. These tests have published normative and MCID values that the physio portal can chart.
- Ameya used LiDAR. With RGB-only BlazePose, timing tests should transfer well (they depend on event detection), but gait speed without depth needs a known distance or floor markers. The app should validate this itself against a stopwatch on its own data.

### Gaps
- No RGB-only smartphone (no LiDAR) validation of 30s-STS/5xSTS/TUG with ICCs, using BlazePose specifically, was retrieved in this pass.
- Balance (sway) from a phone camera vs a force plate was not found.

## 4. Longitudinal progress, change detection and adherence from home video

### Takeaway
Evidence is thin. Camera-guided home programmes report adherence-outcome links and periodic ROM measurement, but no study was found that validates camera-measured longitudinal ROM change (for example, against an MDC/MCID) in a camera-only app. Non-adherence to home exercise is commonly cited at 50-70% for MSK conditions.

### Cited Findings
- **ACDF cohort (JMIR Rehabilitation 2025):** 336 post-op patients followed a 12-week mobile programme with computer-vision-guided exercise, wearable posture sensors and CBT. Cervical ROM was measured at baseline, week 12 and week 24. Higher adherence was linked to better outcomes. The programme is not camera-only. — [JMIR Rehab 2025 e60717](https://rehab.jmir.org/2025//e60717)
- **Knee OA RCT (JMIR mHealth 2025, NCT06220565):** a computer-vision exercise app in older adults. ROM and adherence results were not retrieved. — [JMIR mHealth e63022](https://mhealth.jmir.org/2025/1/e63022/PDF)
- **Single-webcam platform (Sensors 2025):** per-session individualised ROM calibration plus socially assistive guidance. It cites 50-70% non-adherence to prescribed home programmes in MSK conditions. — [Sensors 25(19):6239](https://www.mdpi.com/1424-8220/25/19/6239)
- **Physiosmart (BlazePose home app pilot):** measured elbow angles post-stroke, and the authors state accuracy needs improvement. — [CEUR-WS Vol-3323](https://ceur-ws.org/Vol-3323/paper2.pdf)

### Inferences
- Given monocular angle error of about 5-15 deg, the app should apply these rules before calling something "progress":
  - Show per-session ROM with a noise band.
  - Flag change only when it exceeds a minimum detectable change estimated from test-retest of its own sessions (same camera setup).
  - Use a trend over several sessions, not a single delta.
- Adherence can be measured directly and reliably: sessions done, reps completed, time-on-task and the fraction of reps within the template. These are stronger portal metrics than absolute angles.

### Gaps
- No validated method for camera-based longitudinal ROM change detection was found.
- No study of video-verified vs self-reported adherence was found in this pass.

## 5. Fall-risk or safety signals from video at home

### Takeaway
Smartphone pose can reliably extract gait features from older adults (93.5% extraction success in one 2026 study), and gait timing features are known fall-risk predictors. Direct validation of smartphone-video fall-risk prediction is still largely missing. Use it as a screening flag tied to validated tests (TUG > threshold, 5xSTS time), not a prediction.

### Cited Findings
- **JMIR Formative 2026:** MediaPipe extracted pose from 145/155 (93.5%) smartphone walking videos of older Thai adults, used for age and sex classification. The authors state that smartphone video for frailty and fall risk "has not been explored". — [JMIR Formative 2026 e76755](https://formative.jmir.org/2026/1/e76755)
- **Ambient corridor video (IEEE JTEHM 2020, older):** pose estimation on 1,066 walking videos of 31 older adults with dementia. Gait features were linked to clinical mobility scores and future falls. — [PMC7289176](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7289176/)
- **Portable Biomechanics Laboratory (arXiv 2025):** fits biomechanical models to handheld smartphone video. It notes stride and swing time predict fall risk in older adults. — [arXiv 2507.08268](https://arxiv.org/html/2507.08268v1)
- **Single-camera smartphone knee app (Sensors 2024):** positioned for knee OA screening and fall prevention. — [Sensors 24(23):7625](https://mdpi.com/1424-8220/24/23/7625)
- **Smartphone inertial (not video) fall-risk protocol vs the Physiological Profile Assessment (Sensors 2023, older):** reported as reliable. — [PMC10385364](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10385364/)
- **Predicting TUG score from video gait features with ML (arXiv 2020, older).** — [arXiv 2003.00875](https://arxiv.org/pdf/2003.00875)

### Inferences
- Practical in-session safety signals for this PWA, all derivable from existing BlazePose output:
  - sudden loss of the person from the frame, or the hip dropping below knee height quickly (a possible fall)
  - excessive trunk sway during standing exercises
  - an escalation path such as "stop and call your physio"
- None of these is validated, so label them as safety prompts, not diagnoses.

### Gaps
- No validated smartphone-video fall-risk model with AUC for home use was found.
- No validated in-session fall detection from a phone camera was found.

## 6. Privacy-preserving / on-device approaches

### Takeaway
On-device inference with only skeleton or angle data leaving the phone is the pragmatic standard, and it is what this PWA already does. Federated learning for vision-based rehab exists only in early or edge-prototype work (FLORE). FL alone is not private: gradient inversion and membership inference can leak motion patterns, so it needs secure aggregation or differential privacy.

### Cited Findings
- **FLORE:** federated transfer learning on edge devices for vision-based motor-rehab routine classification. It uses video frames, not skeletons. — [UTB catalogue record](https://vufind.katalog.k.utb.cz/SummonRecord/FETCH-LOGICAL-i93t-34d6b79af8c23b4f4a0f720172e6fb4f7018fc5b1d77731d1cbe34e8b18cc5e53)
- **Federated pose estimation for rehab robotics (Sensors 2025):** highlights non-IID viewpoint, illumination and action distributions across clients as a core FL challenge. — [Sensors 25(14):4372](https://mdpi.com/1424-8220/25/14/4372)
- **Skeleton-based FL for activity recognition (arXiv 2508.14113, 2025, industrial setting):** FL improved cross-user generalisation as well as privacy. — [arXiv 2508.14113](https://arxiv.org/abs/2508.14113)
- **Federated joint learning across hospitals for stroke-rehab robots (arXiv 2403.05472, 2024).** — [arXiv 2403.05472](https://arxiv.org/pdf/2403.05472)
- **Sports motion recognition with FL (2026):** warns that gradient inversion, membership inference and model-update analysis can reveal abnormal exercise habits or motion trajectories, and recommends DP or secure aggregation. — [JASE 2026](https://jase.tku.edu.tw/jase/wp-content/uploads/2026/08/064_2026_2039_V34.pdf)

### Inferences
- For a graduation project, "video never leaves the device; only keypoints/angles are synced to the physio portal" is a defensible, citable privacy design. FL is a stretch goal, worth mentioning as future work with the DP caveat. Implementing it is not justified given the small user base and non-IID data.
- Keypoint sequences are still identifying (gait is a biometric), so the portal should treat them as health data under Egypt's Personal Data Protection Law (Law 151/2020). This is an inference and was not researched here.

### Gaps
- No deployed federated home-rehab skeleton system with measured accuracy was found.
- The legal analysis of Egypt's PDPL for keypoint data was not researched.
