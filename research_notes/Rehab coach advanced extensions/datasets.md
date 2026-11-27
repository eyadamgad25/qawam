# Public datasets to extend the Arabic-first home-rehabilitation coach (2026-11-26)

Scope: new data beyond what the project already uses (KERAAL, IntelliRehabDS, REHAB24-6, REHAB26, KneE-PAD, PhysioLens, KIMORE, UI-PRMD, Fit3D, Shifaa). Licences were checked on the dataset page itself where the page could be fetched; otherwise the source of the licence claim is named and the item is flagged "verify".

Note: the "Medical Low-Back Pain Physical Rehabilitation Dataset" (arXiv 2407.00521, Kinect skeleton + RGB + correctness annotations) is the KERAAL paper, so it is already used. [arXiv](https://arxiv.org/html/2407.00521v1)

## 1. Rehab/physio exercise datasets with correctness or clinician scores (beyond those already used)

### Takeaway
The single best addition is the Rehab-Pile benchmark (2025), which packages 8 public skeleton repositories into 60 ready-made tasks with a common split and code, and brings in three repositories the project does not yet use (EHE, KINECAL, SPHERE, UCDHE). For phone-camera form checks, a new CC BY 4.0 Mendeley set (July 2026) of smartphone gym videos with good/bad form labels is the most licence-friendly find.

### Cited Findings

| Dataset | Contents / size | Labels | Licence | Access | Feature it enables |
|---|---|---|---|---|---|
| **Rehab-Pile / DeepRehabPile** (2025) | Benchmark archive: 60 datasets (39 classification, 21 regression) built from EHE, KIMORE, UI-PRMD, IRDS, KERAAL, KINECAL, SPHERE, UCDHE | Binary correct/incorrect, multi-class error types (UCDHE, KERAAL), regression scores (KIMORE 0-100, UI-PRMD 0-1, EHE 0-10) | Not stated for the archive; inherits each source licence (verify per source) | Download instructions at msd-irimas.github.io/pages/DeepRehabPile; code at github.com/MSD-IRIMAS/DeepRehabPile | Standardised benchmark to report the quality-check model against published baselines; quick access to extra repositories |
| **EHE** (Elderly Home Exercise, Bruce et al. 2021, via Rehab-Pile) | 25 nursing-home residents, Kinect, 6 daily exercises | Alzheimer's severity 0-10 per sequence | Verify | Via Rehab-Pile instructions | Movement-based cognitive/frailty severity regression (research only) |
| **UCDHE** (via Rehab-Pile) | Video processed with OpenPose (2D, 8 joints), rowing and military press, healthy participants | Multi-class error types + binary correct/incorrect | Verify | Via Rehab-Pile | 2D (camera) error-type classifier, closest to the MediaPipe 2D setting |
| **SPHERE stairs** (via Rehab-Pile) | Kinect, walking up stairs | Binary anomaly | Verify | Via Rehab-Pile | Stair-climbing anomaly check |
| **Multi-view smartphone gym videos with good/bad form** (Mendeley, v2, 13 Jul 2026, DOI 10.17632/kgbb3yn47p.2) | 26 participants, 7 exercises (side bend, bent-over row, bicep curl, push-up, shoulder press, bodyweight squat, triceps extension), 3 views (front, side, diagonal), raw MP4 shot on smartphones in a real gym | Subject, exercise, posture quality good/bad (no error types) | **CC BY 4.0** (commercial OK with attribution) | Direct download, Mendeley Data | Phone-camera form classifier and view-angle robustness test; size not stated |
| **Stroke rehab exercise data, 3D depth + IMU** (Mendeley ygpdzx52g2) | Kinect skeleton files + IMU | Scores split into Primary Outcome and Control Factor | Verify on page | Mendeley Data | Stroke-patient quality scoring |
| **Upper-limb stroke rehab exercise video dataset** (Data in Brief, 2026) | 491 videos, 4 upper-limb strengthening exercises | Not confirmed (search snippet does not mention clinician scores or skeletons) | Verify (page returned 403) | ScienceDirect / linked repo | Upper-limb exercise recognition for stroke users |
| **University of Liverpool Rehabilitation Exercise Dataset (UL-RED)** | 22 non-specialised exercises, 10 subjects | Not confirmed | Verify | See PMC article | More exercise classes for recognition |
| **Fitness-AQA** (Parmar et al., ECCV 2022) | Back squat, barbell row, overhead press; in-the-wild images/videos mostly from fitness sources and YouTube | 7 error types | No explicit licence found | Request form on GitHub; Zenodo record 7310289 points to GitHub | Error-type feedback ("knees caving", etc.) |
| **QEVD (Qualcomm Exercise Video Dataset)** incl. FIT-COACH | FIT-COACH: 149 structured workout videos (4-6 exercises each) with timestamped coaching feedback; benchmark of 74 videos; FIT-300K for video QA | Timestamped feedback text, QA | Qualcomm Data License Agreement, **research use** | Qualcomm OneID account required | Training/evaluating spoken live-coaching feedback |
| **FLEX** (2025) | Large multi-modal multi-action fitness AQA dataset | AQA scores | arXiv page shows CC BY-NC-SA 4.0 (that is the paper's licence; dataset terms not verified) | github.com/haoyin116/flex | Fitness quality scoring (non-commercial at best) |

Sources:
- Rehab-Pile contents, label types, subject counts, download/code links; licence not stated — [arXiv 2507.21018](https://arxiv.org/html/2507.21018)
- EHE: 25 nursing-home residents, Kinect, Alzheimer's severity 0-10 — [arXiv 2507.21018](https://arxiv.org/html/2507.21018)
- Mendeley multi-view smartphone dataset details and CC BY 4.0 — [Mendeley Data](https://data.mendeley.com/datasets/kgbb3yn47p/2)
- Stroke depth+IMU data with PO/CF scores — [Mendeley Data](https://data.mendeley.com/datasets/ygpdzx52g2/1)
- Upper-limb stroke video dataset, 491 videos, 4 exercises — [ScienceDirect](https://www.sciencedirect.com/science/article/pii/S2352340926003719)
- UL-RED 22 exercises, 10 subjects — [PMC12062305](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12062305/)
- Fitness-AQA exercises, 7 error types, request form — [Papers with Code](https://paperswithcode.com/dataset/fitness-aqa); [Zenodo](https://zenodo.org/records/7310289)
- QEVD research-only availability, OneID, FIT-COACH sizes — [Qualcomm QEVD](https://www.qualcomm.com/developer/software/qevd-dataset); [Research licence PDF](https://www.qualcomm.com/content/dam/qcomm-martech/dm-assets/documents/Dataset-Research-License-Feb-25-2025.pdf); [Voxel51 card](https://docs.voxel51.com/dataset_zoo/datasets_hf/qualcomm_exercise_video_dataset_benchmark.html)
- FLEX — [arXiv 2506.03198](https://arxiv.org/html/2506.03198v4); [GitHub](https://github.com/haoyin116/flex)

### Inferences
- Rehab-Pile is the cheapest way to "measure better": it gives a published leaderboard on KIMORE/UI-PRMD/IRDS/KERAAL, which the project already uses, so results become comparable to the literature with no new data collection.
- UCDHE and the Mendeley smartphone set are the only finds that are 2D camera-based, matching the MediaPipe phone setting better than Kinect skeletons.
- Only the Mendeley smartphone set has a clearly commercial-friendly licence; QEVD and Fitness-AQA are research-only or unclear, so they suit evaluation/thesis work, not a shipped model.

### Gaps
- Exact licences of EHE, UCDHE, SPHERE and UL-RED were not confirmed on their own pages.
- Size (GB) of the Mendeley smartphone set and of Rehab-Pile downloads not stated on fetched pages.
- Not verified this session (known candidates worth a follow-up search): EgoExo-Fitness, Toronto Rehab Stroke Pose (TRSP), UCO Physical Rehabilitation, MM-Fit, Vogtareuth Rehab Depth ([arXiv 2108.10272](https://arxiv.org/pdf/2108.10272) appeared in results but was not opened), TCM rehab cross-view dataset ([arXiv 2606.28104](https://arxiv.org/pdf/2606.28104), not opened).

## 2. Clinical tests from video: sit-to-stand, TUG, gait, balance, ROM

### Takeaway
KINECAL (PhysioNet, CC0) is the standout: 90 people, Kinect skeletons for TUG, 5x sit-to-stand, 3 m walk and 8 balance stances, with SPPB scores and falls-risk labels. For gait from ordinary video, GAVD (MIT-licensed annotations, YouTube links) and the Toronto Older Adults Gait Archive (video + pose + BBS/TUG/POMA) are the main options. No public shoulder-ROM video set with goniometer ground truth was found.

### Cited Findings

| Dataset | Contents / size | Labels / ground truth | Licence | Access | Feature it enables |
|---|---|---|---|---|---|
| **KINECAL** (PhysioNet v1.0.3, 2023) | 90 participants aged 18-92, Kinect V2 skeleton + depth, 11 movements incl. TUG, STS-5, 3 m walk, quiet/tandem/single-leg stance. **180.1 GB uncompressed, 86.2 GB zip** | SPPB score and class; at-risk thresholds (STS-5 >16.7 s, TUG >14 s, 3 m walk >5 s); groups Healthy-Adult (33), Non-Faller 65+ (33), Self-reported Faller (24), Clinically-At-Risk (6); sway metrics | **CC0 1.0** | Open, direct download (also on AWS Open Data) | Camera-timed STS-5 and TUG tests, balance-stance hold timer, falls-risk flag for the physio portal |
| **Toronto Older Adults Gait Archive (TOAGA)** (Sci Data 2022) | 14 healthy older adults (>65, retirement home), 2D video, 2D pose-tracking joints, 3D Xsens IMU | Tinetti POMA gait/balance, Berg Balance Scale, TUG per participant | Not confirmed (figshare record 10.6084/m9.figshare.c.5515953.v1) | figshare | Validating video gait parameters against IMU ground truth in older adults |
| **GAVD** (IEEE Access 2025) | Links to public (YouTube) gait videos; paper reports 1,874 sequences, repo text mentions 450+ videos | Normal vs abnormal, clinician gait-pattern class, limited gait events, bbox, camera view | Annotations **MIT**; videos remain under YouTube terms, not redistributed | GitHub; user must fetch videos (some removed) | Abnormal-gait screening classifier |
| **Monash Sitting-to-Walking transitions** (figshare) | 65 adults across ages, TUG-based protocol; motion capture, IMU, sEMG (no video). 1.03 GB | Mocap ground truth of sit-to-walk | Verify on figshare | Direct download | Ground truth for sit-to-stand phase timing (not video) |
| **Multi-camera indoor/outdoor gait dataset** (Sci Data 2023) | 3,120 videos + digital goniometer data for thigh, upper arm, head | Goniometer angles | Verify | See paper | Checking video joint-angle accuracy vs goniometer (walking only) |
| **Mendeley gait / fall-risk older adults** (Data in Brief) | Vicon marker data + videos, clinical protocol incl. TUG | Fall risk | Verify; DOI was reported as reserved | Mendeley | Fall-risk gait features |
| **UP-Fall** | Multimodal fall dataset; 15 elderly + 23 young adults | Fall/ADL activities | Verify | See paper | Fall detection |
| **UR Fall Detection (URFD)** | 71 sequences: 31 falls, 40 ADL | Fall vs ADL | Roboflow mirror says CC BY 4.0 (third-party re-upload; original licence not confirmed) | Roboflow mirror / University of Rzeszów | Fall detection during unsupervised home sessions |

Sources:
- KINECAL licence, size, movements, labels, groups — [PhysioNet](https://physionet.org/content/kinecal/); paper — [PMC10507078](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10507078/); [AWS registry](https://registry.opendata.aws/kinecal/)
- TOAGA content and clinical scores (BBS mean 45.0, TUG mean 12.2 s) — [PMC9272879](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9272879/); [Sci Data](https://www.nature.com/articles/s41597-022-01495-z)
- GAVD licence (MIT), columns, no raw video — [GitHub](https://github.com/Rahmyyy/GAVD); 1,874 sequences — [arXiv 2407.04190](https://arxiv.org/abs/2407.04190)
- Monash sit-to-walk dataset, 65 adults, 1.03 GB — [Monash figshare](https://bridges.monash.edu/articles/dataset/_b_Human_Sitting_to_Walking_Transitions_A_Motion_Capture_Dataset_b_/24515092)
- Gait dataset with 3,120 videos + goniometer — [Sci Data](https://www.nature.com/articles/s41597-023-02161-8)
- Mendeley gait/fall-risk older adults — [ScienceDirect](https://sciencedirect.com/science/article/pii/S2352340920314323)
- UP-Fall elderly/young split; public fall datasets mostly use young people — [ProQuest](https://www.proquest.com/docview/2301610862); [Multi Visual Modality Fall Detection](https://arxiv.org/pdf/2206.12740)
- URFD mirror licence and counts — [Roboflow URFD](https://universe.roboflow.com/test-gna4b/urfd-ye4ma)
- Video TUG subtask segmentation study (17 older adults, GoPro + pose; no public release seen) — [PMC12762308](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12762308/)
- Smartphone shoulder-abduction vs goniometer study (10 healthy volunteers; data release not stated) — [PMC10416158](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10416158/)

### Inferences
- KINECAL's thresholds (STS-5 >16.7 s, TUG >14 s) can be used directly as the scoring rule for an in-app "30-second check-up" and its recordings as test data for the timer. It is Kinect skeleton, not RGB, so 2D projection to MediaPipe-like joints is needed.
- KINECAL is 86 GB zipped; downloading only TUG/STS-5 folders file-by-file from PhysioNet is advisable.
- ROM ground truth will likely have to be self-collected (goniometer + phone video) since no public set was found.

### Gaps
- TOAGA, Monash and the Sci Data gait dataset licences not confirmed on their pages (nature.com redirected to login).
- PD4T (Parkinson's video) and other Parkinson's gait video sets were not found in results.
- No public shoulder/knee ROM video dataset with goniometer ground truth found.
- UR Fall original licence not checked on the University of Rzeszów page.

## 3. Roboflow Universe pose/keypoint/exercise datasets

### Takeaway
Roboflow Universe has several small (hundreds of images) community keypoint and classification sets for squat, plank, lunge and single-leg squat. They are image-level, community-labelled, and licence/count data in search snippets disagree, so they suit quick prototypes or a pose-model fine-tune, not clinical quality labels. Dataset pages returned 403 to automated fetching, so licences must be checked by hand.

### Cited Findings

| Project | Type | Size (per listing) | Classes | Licence (per listing) | Link |
|---|---|---|---|---|---|
| Exercise-Pose (HighLight) | Keypoint detection | 602-606 images | Exercise poses | Not confirmed | https://universe.roboflow.com/highlight-84ih7/exercise-pose |
| Pose Counting Repetition (lftnnisa) | Keypoint + YOLOv11n-pose model | 458 or 1,085 images (listings conflict) | Squat, plank | CC BY 4.0 (snippet) | https://universe.roboflow.com/lftnnisa/pose-counting-repetition |
| Squat (project-pswjo) | Keypoint | Not confirmed | Squat | Not confirmed | https://universe.roboflow.com/project-pswjo/squat-wv3cn |
| Exercise (Image) | Classification (not keypoints) | 688 images | Includes squat | "Open source" (exact licence not confirmed) | https://universe.roboflow.com/image-d2zzb/exercise-xj6eg |
| PHYSIOTHERAPY "aloo4" / poseAction | Keypoint | 200 / 678 images | Single-leg squat; lunge, back bridge | Not confirmed | Found via search listing only |
| URFD (Elderly Fall Detection) | Object detection | 71 sequences source | Fall | CC BY 4.0 (mirror) | https://universe.roboflow.com/test-gna4b/urfd-ye4ma |
| UR Fall Detection (Fall older) | Object detection | n/a | Fall | Not confirmed | https://universe.roboflow.com/fall-older/ur-fall-detection-dataset-mbbxe |

Sources:
- Listings for Exercise-Pose, Pose Counting Repetition, PHYSIOTHERAPY/poseAction, Exercise (Image) — [Roboflow search](https://universe.roboflow.com/search?p=2&q=class%3Asquat); [Exercise-Pose](https://universe.roboflow.com/highlight-84ih7/exercise-pose); [Pose Counting Repetition](https://universe.roboflow.com/lftnnisa/pose-counting-repetition); [Exercise Classification](https://universe.roboflow.com/image-d2zzb/exercise-xj6eg)
- A 2026 MDPI paper trained a YOLOv8n-pose model (25 keypoints) for physiotherapy joint angles using Exercise-Pose and the project-pswjo Squat set — [MDPI J. Imaging](https://www.mdpi.com/2313-433X/12/4/157)
- Fall mirrors — [URFD](https://universe.roboflow.com/test-gna4b/urfd-ye4ma); [UR Fall](https://universe.roboflow.com/fall-older/ur-fall-detection-dataset-mbbxe)

### Inferences
- Since the app uses MediaPipe's fixed 33-landmark model, these keypoint sets add little unless the team switches to a fine-tunable pose model (e.g., YOLO-pose). They could serve as a small check of landmark accuracy on hard poses (floor exercises, side views).
- Roboflow fall mirrors are re-uploads; licence claims should be traced to the original source.

### Gaps
- Roboflow pages returned HTTP 403 to WebFetch; licences, current image counts and keypoint schemas need manual checking in a browser.
- No Roboflow dataset with clinician quality labels was found.

## 4. Kaggle: exercise form, gait, falls; Arabic medical text; Arabic/Egyptian speech

### Takeaway
Kaggle exercise sets are mostly exercise-class labels (not form quality) and often non-commercial. For Arabic medical text, AHQAD/AHD (808k Altibbi Q&A pairs, 90 categories, Mendeley, Data in Brief 2024) is by far the largest new source. For voice coaching, Common Voice Arabic (CC0, 158 h) is the only clearly permissive speech set found; Egyptian-dialect speech corpora are non-commercial or paid.

### Cited Findings

Exercise / falls (Kaggle):

| Dataset | Contents | Labels | Licence | Feature |
|---|---|---|---|---|
| Workout/Exercises Video (hasyimabdillah) | 652 YouTube clips, 22 exercises, ~5 s each | Exercise class only | CC BY-NC-SA 4.0 | Exercise recognition (non-commercial) |
| Exercise Detection dataset (mrigaankjaswal) | Push-ups, jumping jacks, pull-ups, squats, Russian twists; MediaPipe landmarks and joint angles | Description claims support for correct vs incorrect form; verify files | Verify | MediaPipe-native form features |
| Gym Exercises Dataset (rishitmurarka) | Gym exercises | Verify | Verify | Recognition |
| Elderly Fall Detection IoT (ziya07) | IoT sensor data | Fall | Verify | Not camera-based |

Arabic medical / health text:

| Dataset | Contents / size | Licence | Access | Feature |
|---|---|---|---|---|
| **AHQAD / AHD** (Arabic Healthcare Dataset) | 808k+ Q&A pairs, 90 categories, from Altibbi; newer version adds English translation | Verify on Mendeley page | Mendeley DOI 10.17632/mgj29ndgrk (direct download); HF mirror Hezam/AHD appeared empty | Large Arabic patient-question corpus: test/augment the pain red-flag check, retrieval FAQ |
| MAQA (Medical Arabic Q&A) | Arabic medical Q&A | Verify | See record | Same as above |
| MedQA-MA (Moroccan Arabic healthcare QA) | Dialect QA | Verify | Mendeley | Dialect robustness test |
| MedAraBench (ICLR 2026) | Large Arabic medical QA benchmark | Verify | See paper | Evaluating any Arabic LLM component |
| AraHealthQA 2025 shared task / MedArabiQ | Arabic medical QA tasks incl. patient-doctor QA | Verify | See paper | Benchmark |
| ArSyra Medical (HF) | Arabic medical dialect data | CC BY-NC-SA 4.0 | HF | Dialect text (non-commercial) |
| ArabPV (HF) | Arabic medical fine-tuning incl. QA | "other" | HF | Verify terms |
| Arabic Medical Company Info & FAQ (Kaggle) | 250+ synthetic Q&A about a fictional company | MIT | Kaggle | RAG plumbing tests only, not clinical |

Arabic / Egyptian speech:

| Dataset | Contents | Licence | Access | Feature |
|---|---|---|---|---|
| **Common Voice Scripted Speech 23.0 Arabic** | 135,805 clips, 158 h (92 h validated), 1,654 speakers | **CC0** | Mozilla Data Collective | ASR fine-tune/eval for spoken pain reports and voice commands |
| Masri 100h (ehabnegm, HF) | ~100 h single-speaker Egyptian | CC BY-NC 4.0 | HF | Egyptian TTS voice for coaching prompts (non-commercial) |
| ASR-EgArbCSC (MagicHub) | 5.5 h Egyptian conversational speech | CC BY-NC-ND 4.0 | Sign-in | Egyptian ASR evaluation |
| 400K Egyptian Arabic Lines (Kaggle) | 400k text lines + audio clipped from online videos/podcasts | GPL 3 listed; underlying audio rights unclear | Kaggle | Risky for anything beyond experiments |
| CALLHOME Egyptian Arabic (LDC97S45) | Telephone speech, 8 kHz | LDC user agreement (paid for non-members) | LDC | Legacy benchmark |
| SpeechDataAI Egyptian conversational | 2,000 h | Commercial licence, samples on request | Vendor | If budget allows |
| Aswat (ArabicNLP 2023) | 732 h MSA + dialect | Not stated in snippet | Paper | Verify |

Sources:
- Kaggle workout video set, CC BY-NC-SA 4.0, 652 clips — [Kaggle](https://www.kaggle.com/datasets/hasyimabdillah/workoutfitness-video); [arXiv 2411.11548](https://arxiv.org/html/2411.11548v1)
- Exercise Detection dataset — [Kaggle](https://www.kaggle.com/datasets/mrigaankjaswal/exercise-detection-dataset)
- Gym Exercises Dataset — [Kaggle](https://www.kaggle.com/datasets/rishitmurarka/gym-exercises-dataset)
- Elderly Fall Detection IoT — [Kaggle](https://www.kaggle.com/datasets/ziya07/elderly-fall-detection-iot-dataset)
- AHQAD/AHD 808k pairs, 90 categories, renamed AHD, translated version — [Mendeley v2](https://data.mendeley.com/datasets/mgj29ndgrk/2); [Mendeley latest](https://data.mendeley.com/datasets/mgj29ndgrk); [Data in Brief via DOAJ](https://doaj.org/article/32bb88ea1e4d403ebb0fcd95f727cd50); Altibbi source and empty mirror — [HF Hezam/AHD](https://huggingface.co/datasets/Hezam/AHD)
- MAQA — [record](https://krishi.icar.gov.in/ohs-2.3.1/index.php/record/view/915703); MedQA-MA — [Mendeley](https://data.mendeley.com/datasets/v6gs7nsy9z); MedAraBench — [ICLR 2026](https://iclr.cc/virtual/2026/poster/10011856); AraHealthQA 2025 — [arXiv 2508.20047](https://arxiv.org/html/2508.20047v1)
- ArSyra, ArabPV, Kaggle FAQ — [ArSyra](https://huggingface.co/datasets/ArSyra/arsyra-medical); [ArabPV](https://huggingface.co/datasets/ahmed7111nn/arabpv-dataset); [Kaggle FAQ](https://www.kaggle.com/datasets/moazeldsokyx/arabic-medical-company-info-and-faq-dataset-ai-gen)
- Common Voice Arabic 23.0, CC0, 158 h — [Mozilla Data Collective](https://datacollective.mozillafoundation.org/datasets/cmflnuzw47jng4x81tavetpul)
- Masri — [HF](https://huggingface.co/datasets/ehabnegm/100-hour-Egyptian-dataset-single-speaker); EgArbCSC — [MagicHub](https://magichub.com/datasets/egyptian-arabic-conversational-speech-corpus/); 400K lines — [Kaggle](https://www.kaggle.com/datasets/fadisarwat/egyptian-arabic-lines); CALLHOME — [LDC](https://catalog.ldc.upenn.edu/LDC97S45); SpeechDataAI — [HF](https://huggingface.co/datasets/SpeechDataAI/egyptian-arabic-conversational-speech); Aswat — [ACL Anthology](https://aclanthology.org/2023.arabicnlp-1.10.pdf)

### Inferences
- AHD is a natural next test set for the Arabic pain red-flag check: it is real patient phrasing from the same platform family as many Arabic consultation sets (Altibbi), but overlap with Shifaa should be checked before using it as a "blind" set.
- For a voice-coaching prototype, Common Voice Arabic is the only legally clean training/eval audio; Egyptian dialect coverage within it is not known.

### Gaps
- AHD licence not confirmed (Mendeley page not fetched).
- No Kaggle gait dataset with clinical labels was found.
- MASC (Arabic speech corpus) and MGB-3 Egyptian licences were not found in results.
- Dialect breakdown of Common Voice Arabic not checked.

## 5. Guideline / exercise-prescription corpora usable for RAG

### Takeaway
WHO's Package of Interventions for Rehabilitation (PIR) is the best open corpus, but it is CC BY-NC-SA 3.0 IGO (non-commercial, share-alike). NICE explicitly forbids AI use without a signed licence (fee outside the UK). Physiopedia's terms prohibit scraping and data mining for AI, despite CC reuse of individual pages.

### Cited Findings
- WHO PIR modules (e.g., musculoskeletal, cardiopulmonary, sensory, mental health, cancer) are licensed CC BY-NC-SA 3.0 IGO; adaptations must carry the same or equivalent licence — [WHO IRIS Module 5](https://iris.who.int/server/api/core/bitstreams/e2101cd7-a3ef-4c87-a482-a9f1960179ca/content); [Module 8](https://iris.who.int/server/api/core/bitstreams/7f323d01-6ebd-4a60-a6cb-e1f5783ac522/content); [Spanish Module 1](https://iris.who.int/server/api/core/bitstreams/39f5136b-73b1-413b-b799-ff67b792888d/content)
- NICE: "NICE content cannot be used for AI purposes without written permission from NICE supported by a signed licence agreement"; AI requests need approval and, internationally, a fee; the UK Open Content Licence does not cover AI — [NICE AI use](https://www.nice.org.uk/reusing-our-content/use-of-our-content-for-ai-purposes); [NICE UK open licence](https://www.nice.org.uk/reusing-our-content/nice-uk-open-content-licence); [International use](https://www.nice.org.uk/reusing-our-content/use-of-our-content-internationally)
- Physiopedia: FAQ says content is free to reuse under a Creative Commons licence, but its open letter says the terms forbid web scraping, data mining and bulk extraction, particularly for AI training; images without licence details need author permission — [FAQ](https://www.physio-pedia.com/Help:Frequently_Asked_Questions); [AI licensing open letter](https://physio-pedia.com/Physiopedia:AI_Training_Model_Licensing_Policy_An_Open_Letter); [Terms of Service](https://www.physio-pedia.com/Physiopedia:Terms_of_Service)
- World Physiotherapy has its own copyright/terms pages — [world.physio copyright](https://world.physio/copyright)
- PEDro has a fair-use page — [PEDro](https://pedro.org.au/fair-use/)

### Inferences
- For a student/non-commercial project, WHO PIR is usable for RAG with attribution; any derived Arabic summaries would need the same CC BY-NC-SA licence. For a commercial product, written permission from WHO would be needed.
- NICE and Physiopedia should not be ingested into a RAG index without permission.

### Gaps
- Physiopedia's exact CC licence version (copyright page returned 403) not confirmed.
- MedlinePlus (US public domain portions, some Arabic leaflets) and NHS exercise sheets (Open Government Licence?) were not covered by results.
- No open patient-reported-outcome or exercise-prescription dataset was found in this pass.
- Whether WHO PIR has Arabic translations was not checked.

## 6. Arabic or Middle East rehabilitation datasets

### Takeaway
No public Arabic-language or Middle East physiotherapy motion dataset was found. The nearest items are Saudi projects that reuse IRDS and Arabic medical text corpora (AHD, MedQA-MA, AraHealthQA).

### Cited Findings
- A Saudi hackathon app (MOVE) uses IRDS as its clinical benchmark with Arabic voice guidance; it is a code repo, not a dataset, and its claims are unverified — [GitHub](https://github.com/AmmarsGeeks/KSDCR-Hackathon-Move-Project)
- Search results for Saudi/Arabic physiotherapy motion data returned only general datasets (IRDS, UL-RED, REHAB24-6) — [IRDS Zenodo](https://zenodo.org/records/4610859); [UL-RED](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12062305/)
- Regional Arabic medical text: AHD (Yemeni authors, Altibbi source), MedQA-MA (Moroccan Arabic) — [Data in Brief via DOAJ](https://doaj.org/article/32bb88ea1e4d403ebb0fcd95f727cd50); [MedQA-MA](https://data.mendeley.com/datasets/v6gs7nsy9z)

### Inferences
- A small self-collected Arabic set (Egyptian patients, phone video, physio scores, Arabic pain notes) would be novel and a credible thesis contribution, since nothing comparable exists publicly.

### Gaps
- Saudi, Egyptian and Gulf university repositories and health-ministry portals were not searched directly.
